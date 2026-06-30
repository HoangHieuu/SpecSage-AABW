from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence, TypeVar

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from pc_build_copilot.catalog_models import (
    CatalogQueryResponse,
    CatalogSku,
    CatalogSnapshot,
    CatalogValidationReport,
    ComponentCategory,
)
from pc_build_copilot.catalog_repository import (
    CatalogRepository,
    default_catalog_snapshot_path,
)
from pc_build_copilot.catalog_validation import validate_catalog
from pc_build_copilot.persistence import resolve_postgres_url


ModelT = TypeVar("ModelT", bound=BaseModel)


POSTGRES_CATALOG_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS catalog_versions (
        snapshot_version TEXT PRIMARY KEY,
        generated_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        sku_count INTEGER NOT NULL CHECK (sku_count >= 0),
        validation_json JSONB NOT NULL,
        payload_json JSONB NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        activated_at TIMESTAMPTZ,
        is_active BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_catalog_versions_single_active
        ON catalog_versions(is_active)
        WHERE is_active = TRUE
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_versions_generated_at
        ON catalog_versions(generated_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS catalog_skus (
        snapshot_version TEXT NOT NULL REFERENCES catalog_versions(snapshot_version)
            ON DELETE CASCADE,
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        brand TEXT,
        price_vnd BIGINT NOT NULL CHECK (price_vnd >= 0),
        list_price_vnd BIGINT CHECK (list_price_vnd IS NULL OR list_price_vnd >= 0),
        discount_amount_vnd BIGINT CHECK (
            discount_amount_vnd IS NULL OR discount_amount_vnd >= 0
        ),
        stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
        stock_status TEXT NOT NULL,
        url TEXT NOT NULL,
        image_url TEXT,
        specs_confidence TEXT NOT NULL,
        catalog_snapshot_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        raw_category TEXT,
        highlights_json JSONB NOT NULL,
        specs_json JSONB NOT NULL,
        payload_json JSONB NOT NULL,
        PRIMARY KEY (snapshot_version, sku)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_skus_snapshot_category_price
        ON catalog_skus(snapshot_version, category, price_vnd)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_skus_snapshot_brand
        ON catalog_skus(snapshot_version, lower(brand))
        WHERE brand IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_skus_snapshot_in_stock
        ON catalog_skus(snapshot_version, category, price_vnd)
        WHERE stock_quantity > 0
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_skus_specs_gin
        ON catalog_skus USING GIN (specs_json)
    """,
    """
    CREATE TABLE IF NOT EXISTS catalog_publish_runs (
        run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        snapshot_version TEXT NOT NULL,
        snapshot_generated_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN ('started', 'loaded', 'blocked', 'failed')
        ),
        sku_count INTEGER NOT NULL CHECK (sku_count >= 0),
        issue_count INTEGER NOT NULL CHECK (issue_count >= 0),
        blocking_issue_count INTEGER NOT NULL CHECK (blocking_issue_count >= 0),
        validation_json JSONB NOT NULL,
        load_options_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        finished_at TIMESTAMPTZ,
        activated_at TIMESTAMPTZ,
        error_text TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_publish_runs_snapshot_started
        ON catalog_publish_runs(snapshot_version, started_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_catalog_publish_runs_status_started
        ON catalog_publish_runs(status, started_at DESC)
    """,
)


@dataclass(frozen=True)
class CatalogPublishBlockedError(Exception):
    validation: CatalogValidationReport

    def __str__(self) -> str:
        return (
            "Catalog snapshot has "
            f"{self.validation.blocking_issue_count} blocking validation issue(s)."
        )


class PostgresCatalogRepository:
    def __init__(
        self,
        database_url: str,
        *,
        fallback: CatalogRepository | None = None,
    ) -> None:
        self.database_url = database_url
        self.fallback = fallback or CatalogRepository()
        ensure_catalog_schema(database_url)

    def snapshot(self) -> CatalogSnapshot:
        with _connect(self.database_url) as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM catalog_versions
                WHERE is_active = TRUE
                ORDER BY activated_at DESC NULLS LAST, generated_at DESC
                LIMIT 1
                """,
            ).fetchone()
        if row is None:
            return self.fallback.snapshot()
        return _model_from_payload(CatalogSnapshot, row["payload_json"])

    def validation_report(self) -> CatalogValidationReport:
        snapshot = self.snapshot()
        if snapshot.items:
            return validate_catalog(
                snapshot.items,
                snapshot_version=snapshot.snapshot_version,
                generated_at=snapshot.generated_at,
            )
        if snapshot.validation is not None:
            return snapshot.validation
        return self.fallback.validation_report()

    def query(
        self,
        *,
        category: ComponentCategory | None = None,
        brand: str | None = None,
        min_price_vnd: int | None = None,
        max_price_vnd: int | None = None,
        in_stock: bool | None = None,
        socket: str | None = None,
        memory_type: str | None = None,
        min_wattage_w: int | None = None,
        min_capacity_gb: int | None = None,
        min_vram_gb: int | None = None,
    ) -> CatalogQueryResponse:
        active = self._active_version()
        if active is None:
            return self.fallback.query(
                category=category,
                brand=brand,
                min_price_vnd=min_price_vnd,
                max_price_vnd=max_price_vnd,
                in_stock=in_stock,
                socket=socket,
                memory_type=memory_type,
                min_wattage_w=min_wattage_w,
                min_capacity_gb=min_capacity_gb,
                min_vram_gb=min_vram_gb,
            )

        conditions = ["snapshot_version = %s"]
        params: list[Any] = [active["snapshot_version"]]

        if category is not None:
            conditions.append("category = %s")
            params.append(category.value)
        if brand:
            conditions.append("brand IS NOT NULL AND lower(brand) LIKE %s")
            params.append(f"%{brand.casefold()}%")
        if min_price_vnd is not None:
            conditions.append("price_vnd >= %s")
            params.append(min_price_vnd)
        if max_price_vnd is not None:
            conditions.append("price_vnd <= %s")
            params.append(max_price_vnd)
        if in_stock is not None:
            conditions.append("stock_quantity > 0" if in_stock else "stock_quantity = 0")
        if socket:
            socket_normalized = socket.casefold()
            conditions.append(
                """
                (
                    lower(coalesce(specs_json->>'socket', '')) = %s
                    OR EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(
                            CASE
                                WHEN jsonb_typeof(specs_json->'socket_support') = 'array'
                                THEN specs_json->'socket_support'
                                ELSE '[]'::jsonb
                            END
                        ) AS socket_value(value)
                        WHERE lower(socket_value.value) LIKE %s
                    )
                )
                """
            )
            params.extend([socket_normalized, f"%{socket_normalized}%"])
        if memory_type:
            conditions.append("lower(coalesce(specs_json->>'memory_type', '')) = %s")
            params.append(memory_type.casefold())
        if min_wattage_w is not None:
            conditions.append(
                """
                jsonb_typeof(specs_json->'wattage_w') = 'number'
                AND (specs_json->>'wattage_w')::integer >= %s
                """
            )
            params.append(min_wattage_w)
        if min_capacity_gb is not None:
            conditions.append(
                """
                jsonb_typeof(specs_json->'capacity_gb') = 'number'
                AND (specs_json->>'capacity_gb')::integer >= %s
                """
            )
            params.append(min_capacity_gb)
        if min_vram_gb is not None:
            conditions.append(
                """
                jsonb_typeof(specs_json->'vram_gb') = 'number'
                AND (specs_json->>'vram_gb')::integer >= %s
                """
            )
            params.append(min_vram_gb)

        sql = f"""
            SELECT payload_json
            FROM catalog_skus
            WHERE {' AND '.join(conditions)}
            ORDER BY category ASC, price_vnd ASC, sku ASC
        """
        with _connect(self.database_url) as conn:
            rows = conn.execute(sql, params).fetchall()

        items = [_model_from_payload(CatalogSku, row["payload_json"]) for row in rows]
        return CatalogQueryResponse(
            snapshot_version=active["snapshot_version"],
            catalog_snapshot_at=active["generated_at"],
            sku_count=len(items),
            items=items,
        )

    def _active_version(self) -> dict[str, Any] | None:
        with _connect(self.database_url) as conn:
            return conn.execute(
                """
                SELECT snapshot_version, generated_at
                FROM catalog_versions
                WHERE is_active = TRUE
                ORDER BY activated_at DESC NULLS LAST, generated_at DESC
                LIMIT 1
                """,
            ).fetchone()


def load_catalog_snapshot(
    database_url: str,
    snapshot: CatalogSnapshot,
    *,
    allow_blocking: bool = False,
) -> CatalogSnapshot:
    ensure_catalog_schema(database_url)
    validation = validate_catalog(
        snapshot.items,
        snapshot_version=snapshot.snapshot_version,
        generated_at=snapshot.generated_at,
    )
    snapshot = snapshot.model_copy(update={"validation": validation})
    run_id = _record_catalog_publish_started(
        database_url,
        snapshot,
        validation,
        allow_blocking=allow_blocking,
    )

    if validation.blocking_issue_count and not allow_blocking:
        message = (
            "Catalog snapshot has "
            f"{validation.blocking_issue_count} blocking validation issue(s); "
            "fix the snapshot or pass --allow-blocking."
        )
        _finish_catalog_publish_run(
            database_url,
            run_id,
            status="blocked",
            error_text=message,
        )
        raise CatalogPublishBlockedError(validation)

    try:
        with _connect(database_url) as conn:
            conn.execute(
                """
                INSERT INTO catalog_versions (
                    snapshot_version,
                    generated_at,
                    source,
                    sku_count,
                    validation_json,
                    payload_json,
                    ingested_at,
                    activated_at,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, now(), NULL, FALSE)
                ON CONFLICT(snapshot_version) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    source = excluded.source,
                    sku_count = excluded.sku_count,
                    validation_json = excluded.validation_json,
                    payload_json = excluded.payload_json,
                    ingested_at = now(),
                    activated_at = NULL,
                    is_active = FALSE
                """,
                (
                    snapshot.snapshot_version,
                    snapshot.generated_at,
                    snapshot.source,
                    len(snapshot.items),
                    _model_jsonb(validation),
                    _model_jsonb(snapshot),
                ),
            )
            conn.execute(
                "DELETE FROM catalog_skus WHERE snapshot_version = %s",
                (snapshot.snapshot_version,),
            )
            _executemany(
                conn,
                """
                INSERT INTO catalog_skus (
                    snapshot_version,
                    sku,
                    name,
                    category,
                    brand,
                    price_vnd,
                    list_price_vnd,
                    discount_amount_vnd,
                    stock_quantity,
                    stock_status,
                    url,
                    image_url,
                    specs_confidence,
                    catalog_snapshot_at,
                    source,
                    raw_category,
                    highlights_json,
                    specs_json,
                    payload_json
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                [
                    _sku_params(snapshot.snapshot_version, item)
                    for item in snapshot.items
                ],
            )
            conn.execute(
                "UPDATE catalog_versions SET is_active = FALSE WHERE snapshot_version <> %s",
                (snapshot.snapshot_version,),
            )
            conn.execute(
                """
                UPDATE catalog_versions
                SET is_active = TRUE, activated_at = now()
                WHERE snapshot_version = %s
                """,
                (snapshot.snapshot_version,),
            )
            _finish_catalog_publish_run_in_transaction(conn, run_id)
    except Exception as exc:
        _try_mark_catalog_publish_failed(database_url, run_id, exc)
        raise
    return snapshot


def ensure_catalog_schema(database_url: str) -> None:
    with _connect(database_url) as conn:
        for statement in POSTGRES_CATALOG_SCHEMA_STATEMENTS:
            conn.execute(statement)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load a validated catalog snapshot into Postgres."
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=default_catalog_snapshot_path(),
        help="Path to catalog_snapshot.json.",
    )
    parser.add_argument("--database-url", help="Postgres URL. Defaults to env.")
    parser.add_argument(
        "--allow-blocking",
        action="store_true",
        help="Load even when catalog validation has blocking issues.",
    )
    args = parser.parse_args(argv)

    database_url = args.database_url or resolve_postgres_url()
    if not database_url:
        parser.error("DATABASE_URL, POSTGRES_URL, or --database-url is required.")

    snapshot = CatalogSnapshot.model_validate_json(
        args.snapshot.read_text(encoding="utf-8")
    )
    try:
        loaded = load_catalog_snapshot(
            database_url,
            snapshot,
            allow_blocking=args.allow_blocking,
        )
    except CatalogPublishBlockedError as exc:
        print(f"{exc} Fix the snapshot or pass --allow-blocking.")
        return 1

    print(
        f"Loaded catalog snapshot {loaded.snapshot_version} "
        f"with {len(loaded.items)} SKUs into Postgres."
    )
    return 0


def _connect(database_url: str) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(database_url, row_factory=dict_row)


def _executemany(
    conn: psycopg.Connection[dict[str, Any]],
    sql: str,
    params: list[tuple[Any, ...]],
) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(sql, params)


def _record_catalog_publish_started(
    database_url: str,
    snapshot: CatalogSnapshot,
    validation: CatalogValidationReport,
    *,
    allow_blocking: bool,
) -> int:
    with _connect(database_url) as conn:
        row = conn.execute(
            """
            INSERT INTO catalog_publish_runs (
                snapshot_version,
                snapshot_generated_at,
                source,
                status,
                sku_count,
                issue_count,
                blocking_issue_count,
                validation_json,
                load_options_json
            )
            VALUES (%s, %s, %s, 'started', %s, %s, %s, %s, %s)
            RETURNING run_id
            """,
            (
                snapshot.snapshot_version,
                snapshot.generated_at,
                snapshot.source,
                len(snapshot.items),
                validation.issue_count,
                validation.blocking_issue_count,
                _model_jsonb(validation),
                Jsonb({"allow_blocking": allow_blocking}),
            ),
        ).fetchone()
    return int(row["run_id"])


def _finish_catalog_publish_run(
    database_url: str,
    run_id: int,
    *,
    status: str,
    error_text: str | None = None,
) -> None:
    with _connect(database_url) as conn:
        conn.execute(
            """
            UPDATE catalog_publish_runs
            SET status = %s,
                finished_at = now(),
                error_text = %s
            WHERE run_id = %s
            """,
            (status, error_text, run_id),
        )


def _finish_catalog_publish_run_in_transaction(
    conn: psycopg.Connection[dict[str, Any]],
    run_id: int,
) -> None:
    conn.execute(
        """
        UPDATE catalog_publish_runs
        SET status = 'loaded',
            finished_at = now(),
            activated_at = now(),
            error_text = NULL
        WHERE run_id = %s
        """,
        (run_id,),
    )


def _try_mark_catalog_publish_failed(
    database_url: str,
    run_id: int,
    exc: Exception,
) -> None:
    try:
        _finish_catalog_publish_run(
            database_url,
            run_id,
            status="failed",
            error_text=str(exc),
        )
    except Exception:
        pass


def _sku_params(snapshot_version: str, item: CatalogSku) -> tuple[Any, ...]:
    return (
        snapshot_version,
        item.sku,
        item.name,
        item.category.value,
        item.brand,
        item.price_vnd,
        item.list_price_vnd,
        item.discount_amount_vnd,
        item.stock_quantity,
        item.stock_status.value,
        item.url,
        item.image_url,
        item.specs_confidence.value,
        item.catalog_snapshot_at,
        item.source,
        item.raw_category,
        Jsonb(item.highlights),
        Jsonb(item.specs),
        _model_jsonb(item),
    )


def _model_jsonb(model: BaseModel) -> Jsonb:
    return Jsonb(model.model_dump(mode="json"))


def _model_from_payload(model_class: type[ModelT], payload: Any) -> ModelT:
    if isinstance(payload, str):
        return model_class.model_validate_json(payload)
    return model_class.model_validate(payload)


if __name__ == "__main__":
    raise SystemExit(main())

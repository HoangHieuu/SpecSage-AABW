from __future__ import annotations

import os
from hmac import compare_digest
from pathlib import Path

from pc_build_copilot.catalog_models import CatalogRefreshResponse, CatalogSnapshot
from pc_build_copilot.catalog_repository import default_catalog_snapshot_path
from pc_build_copilot.catalog_validation import validate_catalog
from pc_build_copilot.persistence import resolve_postgres_url
from pc_build_copilot.postgres_catalog import load_catalog_snapshot


CRON_SECRET_ENV = "CRON_SECRET"
CATALOG_REFRESH_TRIGGER = "vercel_cron"


class CatalogRefreshUnauthorizedError(Exception):
    pass


class CatalogRefreshConfigurationError(Exception):
    pass


def validate_catalog_refresh_authorization(
    authorization: str | None,
    *,
    secret: str | None = None,
) -> None:
    expected_secret = secret if secret is not None else os.environ.get(CRON_SECRET_ENV)
    if not expected_secret:
        raise CatalogRefreshConfigurationError("CRON_SECRET is not configured.")
    if not compare_digest(authorization or "", f"Bearer {expected_secret}"):
        raise CatalogRefreshUnauthorizedError("Invalid catalog refresh token.")


def refresh_postgres_catalog_from_snapshot(
    *,
    database_url: str | None = None,
    snapshot_path: Path | None = None,
    trigger: str = CATALOG_REFRESH_TRIGGER,
) -> CatalogRefreshResponse:
    resolved_database_url = database_url or resolve_postgres_url()
    if not resolved_database_url:
        raise CatalogRefreshConfigurationError(
            "DATABASE_URL, POSTGRES_URL, or POSTGRES_URL_NON_POOLING is required."
        )

    resolved_snapshot_path = snapshot_path or default_catalog_snapshot_path()
    snapshot = CatalogSnapshot.model_validate_json(
        resolved_snapshot_path.read_text(encoding="utf-8")
    )
    loaded = load_catalog_snapshot(
        resolved_database_url,
        snapshot,
        allow_blocking=False,
        load_options={
            "trigger": trigger,
            "snapshot_path": str(resolved_snapshot_path),
        },
    )
    validation = loaded.validation or validate_catalog(
        loaded.items,
        snapshot_version=loaded.snapshot_version,
        generated_at=loaded.generated_at,
    )
    return CatalogRefreshResponse(
        status="loaded",
        trigger=trigger,
        snapshot_version=loaded.snapshot_version,
        snapshot_generated_at=loaded.generated_at,
        source=loaded.source,
        sku_count=len(loaded.items),
        issue_count=validation.issue_count,
        blocking_issue_count=validation.blocking_issue_count,
    )

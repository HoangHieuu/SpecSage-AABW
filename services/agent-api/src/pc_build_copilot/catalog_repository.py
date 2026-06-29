from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pc_build_copilot.catalog_models import (
    CatalogIssue,
    CatalogQueryResponse,
    CatalogSnapshot,
    CatalogValidationReport,
    ComponentCategory,
)
from pc_build_copilot.catalog_validation import validate_catalog


class CatalogRepository:
    def __init__(
        self,
        snapshot_path: Path | None = None,
        snapshot: CatalogSnapshot | None = None,
    ) -> None:
        self._snapshot_path = snapshot_path or default_catalog_snapshot_path()
        self._snapshot = snapshot

    def snapshot(self) -> CatalogSnapshot:
        if self._snapshot is not None:
            return self._snapshot
        if not self._snapshot_path.exists():
            generated_at = datetime.now(UTC)
            return CatalogSnapshot(
                snapshot_version="catalog_missing",
                generated_at=generated_at,
                source=str(self._snapshot_path),
                items=[],
                validation=CatalogValidationReport(
                    snapshot_version="catalog_missing",
                    generated_at=generated_at,
                    sku_count=0,
                    issue_count=1,
                    blocking_issue_count=1,
                    issues=[
                        CatalogIssue(
                            severity="block",
                            code="CATALOG_SNAPSHOT_MISSING",
                            field="catalog_snapshot.json",
                            message="Local catalog snapshot file is missing.",
                        )
                    ],
                ),
            )
        self._snapshot = CatalogSnapshot.model_validate_json(
            self._snapshot_path.read_text(encoding="utf-8")
        )
        return self._snapshot

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
        return CatalogValidationReport(
            snapshot_version=snapshot.snapshot_version,
            generated_at=snapshot.generated_at,
            sku_count=len(snapshot.items),
            issue_count=0,
            blocking_issue_count=0,
            issues=[],
        )

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
        snapshot = self.snapshot()
        items = list(snapshot.items)

        if category is not None:
            items = [item for item in items if item.category == category]
        if brand:
            brand_normalized = brand.casefold()
            items = [
                item
                for item in items
                if item.brand and brand_normalized in item.brand.casefold()
            ]
        if min_price_vnd is not None:
            items = [item for item in items if item.price_vnd >= min_price_vnd]
        if max_price_vnd is not None:
            items = [item for item in items if item.price_vnd <= max_price_vnd]
        if in_stock is not None:
            items = [
                item
                for item in items
                if (item.stock_quantity > 0) == in_stock
            ]
        if socket:
            socket_normalized = socket.casefold()
            items = [
                item
                for item in items
                if str(item.specs.get("socket", "")).casefold() == socket_normalized
                or socket_normalized
                in " ".join(map(str, item.specs.get("socket_support", []))).casefold()
            ]
        if memory_type:
            memory_type_normalized = memory_type.casefold()
            items = [
                item
                for item in items
                if str(item.specs.get("memory_type", "")).casefold()
                == memory_type_normalized
            ]
        if min_wattage_w is not None:
            items = [
                item
                for item in items
                if int(item.specs.get("wattage_w", 0)) >= min_wattage_w
            ]
        if min_capacity_gb is not None:
            items = [
                item
                for item in items
                if int(item.specs.get("capacity_gb", 0)) >= min_capacity_gb
            ]
        if min_vram_gb is not None:
            items = [
                item
                for item in items
                if int(item.specs.get("vram_gb", 0)) >= min_vram_gb
            ]

        return CatalogQueryResponse(
            snapshot_version=snapshot.snapshot_version,
            catalog_snapshot_at=snapshot.generated_at,
            sku_count=len(items),
            items=items,
        )


def default_catalog_snapshot_path() -> Path:
    return Path(__file__).resolve().parents[2] / "catalog" / "catalog_snapshot.json"

from datetime import UTC, datetime

from pc_build_copilot.catalog_models import (
    CatalogIssue,
    CatalogSku,
    CatalogValidationReport,
    ComponentCategory,
)


REQUIRED_SPECS: dict[ComponentCategory, list[str]] = {
    ComponentCategory.CPU: ["socket", "tdp_w", "cores", "threads"],
    ComponentCategory.MAINBOARD: ["socket", "chipset", "memory_type", "form_factor"],
    ComponentCategory.RAM: ["memory_type", "capacity_gb", "module_count", "speed_mhz"],
    ComponentCategory.VGA: ["chipset", "vram_gb", "tdp_w", "length_mm", "power_connectors"],
    ComponentCategory.STORAGE: ["capacity_gb", "interface"],
    ComponentCategory.PSU: ["wattage_w", "efficiency_rating", "pcie_8pin_connectors"],
    ComponentCategory.CASE: ["motherboard_support", "gpu_clearance_mm", "psu_support"],
    ComponentCategory.COOLER: ["socket_support", "tdp_rating_w", "height_mm"],
    ComponentCategory.MONITOR: ["resolution", "refresh_rate_hz"],
}


def validate_catalog(
    items: list[CatalogSku],
    *,
    snapshot_version: str,
    generated_at: datetime | None = None,
) -> CatalogValidationReport:
    issues: list[CatalogIssue] = []
    seen: set[str] = set()

    for item in items:
        if item.sku in seen:
            issues.append(
                CatalogIssue(
                    severity="block",
                    code="CATALOG_DUPLICATE_SKU",
                    sku=item.sku,
                    field="sku",
                    message=f"Duplicate SKU {item.sku} in catalog snapshot.",
                )
            )
        seen.add(item.sku)

        if item.category == ComponentCategory.UNKNOWN:
            issues.append(
                CatalogIssue(
                    severity="block",
                    code="CATALOG_UNKNOWN_CATEGORY",
                    sku=item.sku,
                    field="category",
                    message="SKU category could not be mapped to a component slot.",
                )
            )

        if item.price_vnd <= 0:
            issues.append(
                CatalogIssue(
                    severity="block",
                    code="CATALOG_MISSING_PRICE",
                    sku=item.sku,
                    field="price_vnd",
                    message="SKU is missing a positive VND price.",
                )
            )

        if not item.url.startswith("https://phongvu.vn/"):
            issues.append(
                CatalogIssue(
                    severity="warn",
                    code="CATALOG_NON_PHONGVU_URL",
                    sku=item.sku,
                    field="url",
                    message="SKU URL does not point at phongvu.vn.",
                )
            )

        for field in REQUIRED_SPECS.get(item.category, []):
            if field not in item.specs or item.specs[field] in (None, "", []):
                issues.append(
                    CatalogIssue(
                        severity="block",
                        code="CATALOG_MISSING_REQUIRED_SPEC",
                        sku=item.sku,
                        field=f"specs.{field}",
                        message=f"Missing compatibility-critical spec {field}.",
                    )
                )

    blocking_count = sum(1 for issue in issues if issue.severity == "block")
    return CatalogValidationReport(
        snapshot_version=snapshot_version,
        generated_at=generated_at or datetime.now(UTC),
        sku_count=len(items),
        issue_count=len(issues),
        blocking_issue_count=blocking_count,
        issues=issues,
    )

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

DEMO_REQUIRED_CATEGORIES: tuple[ComponentCategory, ...] = (
    ComponentCategory.CPU,
    ComponentCategory.MAINBOARD,
    ComponentCategory.RAM,
    ComponentCategory.STORAGE,
    ComponentCategory.VGA,
    ComponentCategory.PSU,
    ComponentCategory.CASE,
)


def validate_catalog(
    items: list[CatalogSku],
    *,
    snapshot_version: str,
    generated_at: datetime | None = None,
) -> CatalogValidationReport:
    issues: list[CatalogIssue] = []
    seen: set[str] = set()
    category_counts: dict[ComponentCategory, int] = {
        category: 0 for category in ComponentCategory if category != ComponentCategory.UNKNOWN
    }

    for item in items:
        if item.category != ComponentCategory.UNKNOWN:
            category_counts[item.category] = category_counts.get(item.category, 0) + 1

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

    missing_required_categories = [
        category for category in DEMO_REQUIRED_CATEGORIES if category_counts.get(category, 0) == 0
    ]
    for category in missing_required_categories:
        issues.append(
            CatalogIssue(
                severity="block",
                code="CATALOG_MISSING_DEMO_CATEGORY",
                field=f"category_counts.{category.value}",
                message=f"Catalog snapshot is missing required demo category {category.value}.",
            )
        )

    blocking_count = sum(1 for issue in issues if issue.severity == "block")
    return CatalogValidationReport(
        snapshot_version=snapshot_version,
        generated_at=generated_at or datetime.now(UTC),
        sku_count=len(items),
        issue_count=len(issues),
        blocking_issue_count=blocking_count,
        category_counts=category_counts,
        required_demo_categories=list(DEMO_REQUIRED_CATEGORIES),
        missing_required_demo_categories=missing_required_categories,
        demo_ready=blocking_count == 0 and not missing_required_categories,
        issues=issues,
    )

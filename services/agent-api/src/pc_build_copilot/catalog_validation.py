from datetime import UTC, datetime, timedelta

from pc_build_copilot.catalog_models import (
    CatalogIssue,
    CatalogSku,
    CatalogValidationReport,
    ComponentCategory,
    SpecsConfidence,
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

DEMO_RECOMMENDED_CATEGORY_COUNTS: dict[ComponentCategory, int] = {
    category: 2 for category in DEMO_REQUIRED_CATEGORIES
}

PILOT_RECOMMENDED_CATEGORY_COUNTS: dict[ComponentCategory, int] = {
    category: 3 for category in DEMO_REQUIRED_CATEGORIES
}

PRODUCTION_TARGET_CATEGORY_COUNTS: dict[ComponentCategory, int] = {
    ComponentCategory.CPU: 15,
    ComponentCategory.MAINBOARD: 15,
    ComponentCategory.RAM: 10,
    ComponentCategory.STORAGE: 10,
    ComponentCategory.VGA: 20,
    ComponentCategory.PSU: 10,
    ComponentCategory.CASE: 10,
    ComponentCategory.COOLER: 8,
    ComponentCategory.MONITOR: 10,
}

DEFAULT_STALE_AFTER_DAYS = 7


def validate_catalog(
    items: list[CatalogSku],
    *,
    snapshot_version: str,
    generated_at: datetime | None = None,
    freshness_checked_at: datetime | None = None,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
) -> CatalogValidationReport:
    generated_at = _ensure_aware(generated_at or datetime.now(UTC))
    freshness_checked_at = _ensure_aware(freshness_checked_at or datetime.now(UTC))
    snapshot_fresh_until = generated_at + timedelta(days=stale_after_days)
    snapshot_age_days = max(0, (freshness_checked_at - generated_at).days)
    freshness_status = (
        "fresh" if freshness_checked_at <= snapshot_fresh_until else "stale"
    )

    issues: list[CatalogIssue] = []
    seen: set[str] = set()
    category_counts: dict[ComponentCategory, int] = {
        category: 0 for category in ComponentCategory if category != ComponentCategory.UNKNOWN
    }
    specs_confidence_counts: dict[SpecsConfidence, int] = {
        confidence: 0 for confidence in SpecsConfidence
    }

    for item in items:
        if item.category != ComponentCategory.UNKNOWN:
            category_counts[item.category] = category_counts.get(item.category, 0) + 1
        specs_confidence_counts[item.specs_confidence] = (
            specs_confidence_counts.get(item.specs_confidence, 0) + 1
        )

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

    thin_demo_categories = [
        category
        for category, recommended_count in DEMO_RECOMMENDED_CATEGORY_COUNTS.items()
        if 0 < category_counts.get(category, 0) < recommended_count
    ]
    for category in thin_demo_categories:
        issues.append(
            CatalogIssue(
                severity="warn",
                code="CATALOG_THIN_DEMO_CATEGORY",
                field=f"category_counts.{category.value}",
                message=(
                    f"Catalog snapshot has {category_counts.get(category, 0)} "
                    f"{category.value} SKU(s); recommended demo coverage is "
                    f"{DEMO_RECOMMENDED_CATEGORY_COUNTS[category]}."
                ),
            )
        )

    thin_pilot_categories = [
        category
        for category, recommended_count in PILOT_RECOMMENDED_CATEGORY_COUNTS.items()
        if 0 < category_counts.get(category, 0) < recommended_count
    ]
    for category in thin_pilot_categories:
        issues.append(
            CatalogIssue(
                severity="warn",
                code="CATALOG_THIN_PILOT_CATEGORY",
                field=f"category_counts.{category.value}",
                message=(
                    f"Catalog snapshot has {category_counts.get(category, 0)} "
                    f"{category.value} SKU(s); pilot coverage target is "
                    f"{PILOT_RECOMMENDED_CATEGORY_COUNTS[category]}."
                ),
            )
        )

    production_gap_categories = [
        category
        for category, target_count in PRODUCTION_TARGET_CATEGORY_COUNTS.items()
        if category_counts.get(category, 0) < target_count
    ]
    if production_gap_categories:
        issues.append(
            CatalogIssue(
                severity="warn",
                code="CATALOG_PRODUCTION_TARGET_GAP",
                field="category_counts",
                message=(
                    "Catalog snapshot is below the production coverage target for: "
                    + ", ".join(category.value for category in production_gap_categories)
                    + "."
                ),
            )
        )

    if freshness_status == "stale":
        issues.append(
            CatalogIssue(
                severity="warn",
                code="CATALOG_SNAPSHOT_STALE",
                field="generated_at",
                message=(
                    f"Catalog snapshot is {snapshot_age_days} day(s) old; "
                    f"refresh target is every {stale_after_days} day(s)."
                ),
            )
        )

    blocking_count = sum(1 for issue in issues if issue.severity == "block")
    demo_ready = blocking_count == 0 and not missing_required_categories
    pilot_ready = (
        demo_ready
        and freshness_status == "fresh"
        and not thin_pilot_categories
    )
    production_ready = (
        blocking_count == 0
        and freshness_status == "fresh"
        and not production_gap_categories
    )
    return CatalogValidationReport(
        snapshot_version=snapshot_version,
        generated_at=generated_at,
        sku_count=len(items),
        issue_count=len(issues),
        blocking_issue_count=blocking_count,
        stale_after_days=stale_after_days,
        freshness_checked_at=freshness_checked_at,
        snapshot_fresh_until=snapshot_fresh_until,
        snapshot_age_days=snapshot_age_days,
        freshness_status=freshness_status,
        specs_confidence_counts=specs_confidence_counts,
        category_counts=category_counts,
        recommended_demo_category_counts=DEMO_RECOMMENDED_CATEGORY_COUNTS,
        pilot_recommended_category_counts=PILOT_RECOMMENDED_CATEGORY_COUNTS,
        production_target_category_counts=PRODUCTION_TARGET_CATEGORY_COUNTS,
        required_demo_categories=list(DEMO_REQUIRED_CATEGORIES),
        missing_required_demo_categories=missing_required_categories,
        thin_demo_categories=thin_demo_categories,
        thin_pilot_categories=thin_pilot_categories,
        production_gap_categories=production_gap_categories,
        demo_ready=demo_ready,
        pilot_ready=pilot_ready,
        production_ready=production_ready,
        issues=issues,
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value

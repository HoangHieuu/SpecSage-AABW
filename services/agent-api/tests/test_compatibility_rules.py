from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from pc_build_copilot.catalog_models import (
    CatalogSku,
    CatalogSnapshot,
    ComponentCategory,
    SpecsConfidence,
    StockStatus,
)
from pc_build_copilot.compatibility_models import (
    BuildSlot,
    CompatibilitySeverity,
    CompatibilityStatus,
    RULES_VERSION,
)
from pc_build_copilot.compatibility_rules import validate_build_compatibility

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)
RULE_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "rules"
    / "compatibility_rules_v2026_06_27.json"
)
VALID_SELECTED = {
    BuildSlot.CPU: "211208130",
    BuildSlot.MAINBOARD: "230203929",
    BuildSlot.RAM: "210602265",
    BuildSlot.STORAGE: "221000008",
    BuildSlot.VGA: "260508255",
    BuildSlot.PSU: "210800662",
    BuildSlot.CASE: "220101742",
}


def _snapshot(items: list[CatalogSku] | None = None) -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_compat",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=items or _items(),
    )


def _replace(items: list[CatalogSku], replacement: CatalogSku) -> list[CatalogSku]:
    return [replacement if item.sku == replacement.sku else item for item in items]


def _item(items: list[CatalogSku], sku: str) -> CatalogSku:
    return next(item for item in items if item.sku == sku)


def _with_specs(item: CatalogSku, **specs: Any) -> CatalogSku:
    merged = dict(item.specs)
    merged.update(specs)
    return item.model_copy(update={"specs": merged})


def _cooler(*, height_mm: int, tdp_rating_w: int = 150) -> CatalogSku:
    return CatalogSku(
        sku="cooler-test-001",
        name="Cooler test LGA1700",
        category=ComponentCategory.COOLER,
        price_vnd=590_000,
        stock_quantity=5,
        stock_status=StockStatus.IN_STOCK,
        url="https://phongvu.vn/cooler-test--scooler-test-001",
        brand="Test",
        specs={
            "socket_support": ["LGA1700"],
            "tdp_rating_w": tdp_rating_w,
            "height_mm": height_mm,
        },
        specs_confidence=SpecsConfidence.VERIFIED,
        catalog_snapshot_at=SNAPSHOT_AT,
    )


def _rule_ids(report) -> set[str]:
    return {result.rule_id for result in report.results}


def test_rule_manifest_matches_runtime_version_and_required_rule_ids() -> None:
    manifest = json.loads(RULE_MANIFEST.read_text(encoding="utf-8"))
    manifest_rule_ids = {rule["id"] for rule in manifest["rules"]}

    assert manifest["version"] == RULES_VERSION
    assert {
        "COMPAT_SOCKET_MISMATCH",
        "COMPAT_RAM_TYPE_MISMATCH",
        "COMPAT_PSU_WATTAGE_TOO_LOW",
        "COMPAT_GPU_POWER_CONNECTOR_MISSING",
        "COMPAT_GPU_CASE_CLEARANCE_BLOCK",
        "COMPAT_COOLER_CASE_CLEARANCE_BLOCK",
    }.issubset(manifest_rule_ids)


def test_valid_fixture_build_can_be_approved() -> None:
    report = validate_build_compatibility(
        build_id="build_valid",
        selected_skus=VALID_SELECTED,
        catalog=_snapshot(),
    )

    assert report.status == CompatibilityStatus.APPROVED
    assert report.max_severity == CompatibilitySeverity.PASS
    assert report.can_approve is True
    assert "COMPAT_SOCKET_MATCH" in _rule_ids(report)
    assert "COMPAT_PSU_WATTAGE_OK" in _rule_ids(report)


def test_cpu_mainboard_socket_mismatch_blocks_build() -> None:
    items = _items()
    mainboard = _with_specs(_item(items, "230203929"), socket="AM5")
    report = validate_build_compatibility(
        build_id="build_socket_bad",
        selected_skus=VALID_SELECTED,
        catalog=_snapshot(_replace(items, mainboard)),
    )

    assert report.status == CompatibilityStatus.BLOCKED
    assert report.can_approve is False
    assert "COMPAT_SOCKET_MISMATCH" in _rule_ids(report)


def test_ram_type_mismatch_blocks_build() -> None:
    items = _items()
    ram = _with_specs(_item(items, "210602265"), memory_type="DDR5")
    report = validate_build_compatibility(
        build_id="build_ram_bad",
        selected_skus=VALID_SELECTED,
        catalog=_snapshot(_replace(items, ram)),
    )

    assert report.status == CompatibilityStatus.BLOCKED
    assert "COMPAT_RAM_TYPE_MISMATCH" in _rule_ids(report)


def test_psu_wattage_and_gpu_connectors_block_build() -> None:
    items = _items()
    psu = _with_specs(
        _item(items, "210800662"),
        wattage_w=300,
        pcie_8pin_connectors=0,
    )
    report = validate_build_compatibility(
        build_id="build_psu_bad",
        selected_skus=VALID_SELECTED,
        catalog=_snapshot(_replace(items, psu)),
    )

    assert report.status == CompatibilityStatus.BLOCKED
    assert "COMPAT_PSU_WATTAGE_TOO_LOW" in _rule_ids(report)
    assert "COMPAT_GPU_POWER_CONNECTOR_MISSING" in _rule_ids(report)


def test_gpu_case_clearance_blocks_when_card_is_too_long() -> None:
    items = _items()
    case = _with_specs(_item(items, "220101742"), gpu_clearance_mm=240)
    report = validate_build_compatibility(
        build_id="build_gpu_clearance_bad",
        selected_skus=VALID_SELECTED,
        catalog=_snapshot(_replace(items, case)),
    )

    assert report.status == CompatibilityStatus.BLOCKED
    assert "COMPAT_GPU_CASE_CLEARANCE_BLOCK" in _rule_ids(report)


def test_gpu_case_clearance_warns_when_margin_is_tight() -> None:
    items = _items()
    case = _with_specs(_item(items, "220101742"), gpu_clearance_mm=260)
    report = validate_build_compatibility(
        build_id="build_gpu_clearance_tight",
        selected_skus=VALID_SELECTED,
        catalog=_snapshot(_replace(items, case)),
    )

    assert report.status == CompatibilityStatus.WARNING
    assert report.can_approve is True
    assert "COMPAT_GPU_CASE_CLEARANCE_TIGHT" in _rule_ids(report)


def test_cooler_case_clearance_blocks_or_warns_by_margin() -> None:
    blocking_report = validate_build_compatibility(
        build_id="build_cooler_block",
        selected_skus={**VALID_SELECTED, BuildSlot.COOLER: "cooler-test-001"},
        catalog=_snapshot([*_items(), _cooler(height_mm=170)]),
    )
    warning_report = validate_build_compatibility(
        build_id="build_cooler_warn",
        selected_skus={**VALID_SELECTED, BuildSlot.COOLER: "cooler-test-001"},
        catalog=_snapshot([*_items(), _cooler(height_mm=155)]),
    )

    assert blocking_report.status == CompatibilityStatus.BLOCKED
    assert "COMPAT_COOLER_CASE_CLEARANCE_BLOCK" in _rule_ids(blocking_report)
    assert warning_report.status == CompatibilityStatus.WARNING
    assert "COMPAT_COOLER_CASE_CLEARANCE_TIGHT" in _rule_ids(warning_report)


def test_missing_catalog_sku_blocks_build_approval() -> None:
    report = validate_build_compatibility(
        build_id="build_missing_sku",
        selected_skus={**VALID_SELECTED, BuildSlot.CPU: "missing-sku"},
        catalog=_snapshot(),
    )

    assert report.status == CompatibilityStatus.BLOCKED
    assert report.can_approve is False
    assert "CATALOG_SKU_NOT_FOUND" in _rule_ids(report)

from datetime import UTC, datetime
from pathlib import Path

from pc_build_copilot.catalog_cli import main
from pc_build_copilot.catalog_models import CatalogSnapshot, ComponentCategory
from pc_build_copilot.catalog_parser import (
    apply_overrides,
    load_overrides,
    normalize_products,
    parse_next_data_products,
)
from pc_build_copilot.catalog_validation import validate_catalog


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "phongvu-category-components.html"
OVERRIDES = ROOT / "catalog" / "sku_specs_overrides.json"
SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _items():
    raw_products = parse_next_data_products(FIXTURE.read_text(encoding="utf-8"))
    normalized = normalize_products(raw_products, snapshot_at=SNAPSHOT_AT)
    return apply_overrides(normalized, load_overrides(OVERRIDES))


def test_next_data_fixture_normalizes_sku_price_stock_and_url() -> None:
    items = _items()

    gpu = next(item for item in items if item.sku == "260508255")

    assert gpu.name == "VGA ASUS Dual Radeon RX 7600 8GB GDDR6"
    assert gpu.category == ComponentCategory.VGA
    assert gpu.price_vnd == 6_990_000
    assert gpu.stock_quantity == 12
    assert gpu.url == "https://phongvu.vn/vga-asus-dual-radeon-rx-7600-8gb-gddr6--s260508255"
    assert "8GB GDDR6" in gpu.highlights


def test_overrides_complete_required_compatibility_specs() -> None:
    items = _items()

    report = validate_catalog(
        items,
        snapshot_version="catalog_test",
        generated_at=SNAPSHOT_AT,
    )

    assert report.sku_count == 11
    assert report.blocking_issue_count == 0
    assert report.demo_ready is True
    assert report.category_counts[ComponentCategory.CPU] == 1
    assert report.category_counts[ComponentCategory.VGA] == 2
    assert report.recommended_demo_category_counts[ComponentCategory.CPU] == 2
    assert report.missing_required_demo_categories == []
    assert report.thin_demo_categories == [
        ComponentCategory.CPU,
        ComponentCategory.MAINBOARD,
        ComponentCategory.CASE,
    ]
    assert any(
        issue.severity == "warn"
        and issue.code == "CATALOG_THIN_DEMO_CATEGORY"
        and issue.field == "category_counts.cpu"
        for issue in report.issues
    )
    assert all(item.specs_confidence == "verified" for item in items)


def test_validation_blocks_skus_missing_critical_specs() -> None:
    cpu = next(item for item in _items() if item.category == ComponentCategory.CPU)
    incomplete = cpu.model_copy(update={"specs": {"socket": "LGA1700"}})

    report = validate_catalog(
        [incomplete],
        snapshot_version="catalog_test_missing_specs",
        generated_at=SNAPSHOT_AT,
    )

    assert report.blocking_issue_count > 0
    assert any(
        issue.code == "CATALOG_MISSING_REQUIRED_SPEC" and issue.field == "specs.tdp_w"
        for issue in report.issues
    )


def test_validation_blocks_snapshots_missing_required_demo_categories() -> None:
    items = [
        item
        for item in _items()
        if item.category
        not in {
            ComponentCategory.VGA,
            ComponentCategory.PSU,
        }
    ]

    report = validate_catalog(
        items,
        snapshot_version="catalog_test_missing_demo_category",
        generated_at=SNAPSHOT_AT,
    )

    assert report.demo_ready is False
    assert ComponentCategory.VGA in report.missing_required_demo_categories
    assert ComponentCategory.PSU in report.missing_required_demo_categories
    assert ComponentCategory.VGA not in report.thin_demo_categories
    assert ComponentCategory.PSU not in report.thin_demo_categories
    assert any(
        issue.code == "CATALOG_MISSING_DEMO_CATEGORY"
        and issue.field == "category_counts.vga"
        for issue in report.issues
    )


def test_catalog_cli_writes_snapshot_with_embedded_validation(tmp_path: Path) -> None:
    output = tmp_path / "catalog_snapshot.json"

    exit_code = main(
        [
            "--input",
            str(FIXTURE),
            "--overrides",
            str(OVERRIDES),
            "--output",
            str(output),
            "--snapshot-at",
            "2026-06-27T00:00:00Z",
            "--snapshot-version",
            "catalog_test_cli",
        ]
    )

    snapshot = CatalogSnapshot.model_validate_json(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert snapshot.snapshot_version == "catalog_test_cli"
    assert len(snapshot.items) == 11
    assert snapshot.validation is not None
    assert snapshot.validation.blocking_issue_count == 0
    assert snapshot.validation.demo_ready is True
    assert snapshot.validation.category_counts[ComponentCategory.CASE] == 1
    assert snapshot.validation.recommended_demo_category_counts[ComponentCategory.CASE] == 2
    assert ComponentCategory.CASE in snapshot.validation.thin_demo_categories

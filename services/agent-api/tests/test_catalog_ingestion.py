import json
from datetime import UTC, datetime
from pathlib import Path

from pc_build_copilot.catalog_capture_cli import (
    main as capture_main,
    sanitize_next_data_html,
)
from pc_build_copilot.catalog_cli import (
    load_source_manifest,
    main as catalog_sync_main,
)
from pc_build_copilot.catalog_models import CatalogSnapshot, ComponentCategory
from pc_build_copilot.catalog_parser import (
    apply_overrides,
    extract_next_data_json,
    load_overrides,
    normalize_products,
    parse_next_data_products,
)
from pc_build_copilot.catalog_source_report_cli import (
    build_source_report,
    source_report_to_dict,
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


def test_live_teko_listing_shape_normalizes_nested_price_and_link() -> None:
    items = normalize_products(
        [
            {
                "sku": "260501434",
                "name": "Bộ vi xử lý/ CPU Intel Core i7-14700F LGA-1700",
                "price": {
                    "latestPrice": 10_790_000,
                    "supplierRetailPrice": 10_790_000,
                    "discountAmount": 0,
                },
                "stockQuantity": 1000,
                "brand": {"name": "Intel", "code": "intel"},
                "highlight": "<span>Socket 1700</span><span>20 nhân / 28 luồng</span>",
                "link": {
                    "as": {
                        "pathname": "/cpu-intel-core-i7-14700f-tray--s260501434"
                    }
                },
            }
        ],
        snapshot_at=SNAPSHOT_AT,
        category_hint=ComponentCategory.CPU,
        source_url="https://phongvu.vn/c/cpu",
    )

    assert len(items) == 1
    assert items[0].price_vnd == 10_790_000
    assert items[0].list_price_vnd == 10_790_000
    assert items[0].brand == "Intel"
    assert items[0].url == "https://phongvu.vn/cpu-intel-core-i7-14700f-tray--s260501434"
    assert items[0].specs["socket"] == "LGA1700"


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

    exit_code = catalog_sync_main(
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


def test_catalog_cli_merges_manifest_sources_with_dedupe_and_overrides(
    tmp_path: Path,
) -> None:
    extra_source = tmp_path / "extra-cpu.html"
    extra_source.write_text(
        """
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "serverProducts": [
                {
                  "sku": "cpu-extra-1",
                  "name": "CPU Intel Core i5-13400F LGA1700 10C 16T",
                  "latestPrice": 4090000,
                  "stockQuantity": 7,
                  "slug": "cpu-intel-core-i5-13400f",
                  "category": "cpu",
                  "highlight": ["LGA1700", "10C 16T"]
                }
              ]
            }
          }
        }
        </script>
        """,
        encoding="utf-8",
    )
    manifest = tmp_path / "catalog_sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"input": str(FIXTURE), "source": "test_existing_fixture"},
                    {
                        "input": "extra-cpu.html",
                        "source": "test_extra_cpu_fixture",
                        "category_hint": "cpu",
                    },
                    {"input": str(FIXTURE), "source": "test_duplicate_fixture"},
                ]
            }
        ),
        encoding="utf-8",
    )
    overrides = load_overrides(OVERRIDES)
    overrides["cpu-extra-1"] = {
        "specs_confidence": "verified",
        "specs": {
            "socket": "LGA1700",
            "tdp_w": 65,
            "cores": 10,
            "threads": 16,
        },
    }
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(json.dumps(overrides), encoding="utf-8")
    output = tmp_path / "catalog_snapshot.json"

    exit_code = catalog_sync_main(
        [
            "--source-manifest",
            str(manifest),
            "--overrides",
            str(overrides_path),
            "--output",
            str(output),
            "--snapshot-at",
            "2026-06-27T00:00:00Z",
            "--snapshot-version",
            "catalog_test_manifest",
        ]
    )

    snapshot = CatalogSnapshot.model_validate_json(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert snapshot.snapshot_version == "catalog_test_manifest"
    assert snapshot.source == str(manifest)
    assert len(snapshot.items) == 12
    assert sum(1 for item in snapshot.items if item.sku == "260508255") == 1
    assert snapshot.validation is not None
    assert snapshot.validation.blocking_issue_count == 0
    assert snapshot.validation.category_counts[ComponentCategory.CPU] == 2
    assert ComponentCategory.CPU not in snapshot.validation.thin_demo_categories


def test_catalog_cli_skips_disabled_manifest_sources(tmp_path: Path) -> None:
    staged_source = tmp_path / "staged-cpu.html"
    staged_source.write_text(
        """
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "serverProducts": [
                {
                  "sku": "cpu-staged-1",
                  "name": "CPU Intel Core i5-14400F LGA1700 10C 16T",
                  "latestPrice": 4590000,
                  "stockQuantity": 5,
                  "slug": "cpu-intel-core-i5-14400f",
                  "category": "cpu",
                  "highlight": ["LGA1700", "10C 16T"]
                }
              ]
            }
          }
        }
        </script>
        """,
        encoding="utf-8",
    )
    manifest = tmp_path / "catalog_sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"input": str(FIXTURE), "source": "test_existing_fixture"},
                    {
                        "input": "staged-cpu.html",
                        "source": "test_staged_cpu_fixture",
                        "category_hint": "cpu",
                        "enabled": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "catalog_snapshot.json"

    enabled_sources = load_source_manifest(manifest)
    all_sources = load_source_manifest(manifest, include_disabled=True)
    exit_code = catalog_sync_main(
        [
            "--source-manifest",
            str(manifest),
            "--overrides",
            str(OVERRIDES),
            "--output",
            str(output),
            "--snapshot-at",
            "2026-06-27T00:00:00Z",
            "--snapshot-version",
            "catalog_test_staged",
        ]
    )

    snapshot = CatalogSnapshot.model_validate_json(output.read_text(encoding="utf-8"))
    assert len(enabled_sources) == 1
    assert len(all_sources) == 2
    assert all_sources[1].enabled is False
    assert exit_code == 0
    assert len(snapshot.items) == 11
    assert "cpu-staged-1" not in {item.sku for item in snapshot.items}


def test_catalog_capture_cli_sanitizes_payload_and_upserts_manifest(
    tmp_path: Path,
) -> None:
    output = tmp_path / "captures" / "vga.html"
    manifest = tmp_path / "catalog" / "catalog_sources.json"

    exit_code = capture_main(
        [
            "--input",
            str(FIXTURE),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--source",
            "test_capture_fixture",
            "--source-url",
            "https://phongvu.vn/c/vga-card-man-hinh",
            "--category-hint",
            "vga",
        ]
    )
    second_exit_code = capture_main(
        [
            "--input",
            str(FIXTURE),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--source",
            "test_capture_fixture",
            "--source-url",
            "https://phongvu.vn/c/vga-card-man-hinh",
            "--category-hint",
            "vga",
        ]
    )

    loaded_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert second_exit_code == 0
    captured = output.read_text(encoding="utf-8")
    assert parse_next_data_products(captured)
    assert "window.env" not in captured
    assert "FIREBASE_API_KEY" not in captured
    assert loaded_manifest == {
        "sources": [
            {
                "input": "../captures/vga.html",
                "source": "test_capture_fixture",
                "source_url": "https://phongvu.vn/c/vga-card-man-hinh",
                "category_hint": "vga",
            }
        ]
    }


def test_catalog_capture_cli_can_stage_manifest_entries(tmp_path: Path) -> None:
    output = tmp_path / "captures" / "cpu.html"
    manifest = tmp_path / "catalog" / "catalog_sources.json"

    exit_code = capture_main(
        [
            "--input",
            str(FIXTURE),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--source",
            "test_staged_capture_fixture",
            "--source-url",
            "https://phongvu.vn/c/cpu",
            "--category-hint",
            "cpu",
            "--staged",
        ]
    )

    loaded_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert loaded_manifest["sources"][0]["enabled"] is False


def test_catalog_source_report_counts_enabled_and_staged_candidates(
    tmp_path: Path,
) -> None:
    staged_source = tmp_path / "staged-cpu.html"
    staged_source.write_text(
        """
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "serverProducts": [
                {
                  "sku": "cpu-staged-1",
                  "name": "CPU Intel Core i5-14400F LGA1700 10C 16T",
                  "latestPrice": 4590000,
                  "stockQuantity": 5,
                  "slug": "cpu-intel-core-i5-14400f",
                  "category": "cpu",
                  "highlight": ["LGA1700", "10C 16T"]
                }
              ]
            }
          }
        }
        </script>
        """,
        encoding="utf-8",
    )
    manifest = tmp_path / "catalog_sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"input": str(FIXTURE), "source": "test_existing_fixture"},
                    {
                        "input": "staged-cpu.html",
                        "source": "test_staged_cpu_fixture",
                        "category_hint": "cpu",
                        "enabled": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_source_report(
        manifest_path=manifest,
        snapshot_at=SNAPSHOT_AT,
    )
    rendered = source_report_to_dict(report)

    assert report.source_count == 2
    assert report.enabled_source_count == 1
    assert report.staged_source_count == 1
    assert report.candidate_count == 12
    assert report.invalid_candidate_count == 0
    assert report.unique_candidate_count == 12
    assert report.enabled_candidate_count == 11
    assert report.staged_candidate_count == 1
    assert rendered["staged_category_counts"]["cpu"] == 1


def test_catalog_source_report_counts_invalid_staged_candidates(
    tmp_path: Path,
) -> None:
    staged_source = tmp_path / "staged-invalid.html"
    staged_source.write_text(
        """
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "serverProducts": [
                {
                  "sku": "missing-price-1",
                  "name": "CPU missing price",
                  "stockQuantity": 5,
                  "slug": "cpu-missing-price",
                  "category": "cpu"
                },
                {
                  "sku": "cpu-staged-1",
                  "name": "CPU Intel Core i5-14400F LGA1700 10C 16T",
                  "latestPrice": 4590000,
                  "stockQuantity": 5,
                  "slug": "cpu-intel-core-i5-14400f",
                  "category": "cpu",
                  "highlight": ["LGA1700", "10C 16T"]
                }
              ]
            }
          }
        }
        </script>
        """,
        encoding="utf-8",
    )
    manifest = tmp_path / "catalog_sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "input": "staged-invalid.html",
                        "source": "test_staged_invalid_fixture",
                        "category_hint": "cpu",
                        "enabled": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_source_report(
        manifest_path=manifest,
        snapshot_at=SNAPSHOT_AT,
    )

    assert report.source_count == 1
    assert report.candidate_count == 1
    assert report.invalid_candidate_count == 1
    assert report.sources[0].invalid_product_count == 1


def test_catalog_capture_cli_rejects_payload_without_next_data_products(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "empty.html"
    input_path.write_text("<html><body>No product payload.</body></html>", encoding="utf-8")
    output = tmp_path / "captures" / "empty.html"

    exit_code = capture_main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    assert not output.exists()


def test_catalog_capture_sanitizes_page_env_before_writing() -> None:
    raw = """
    <script>window.env = {"FIREBASE_API_KEY":"SHOULD_NOT_SURVIVE"};</script>
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "serverProducts": [
            {
              "sku": "cpu-safe-1",
              "name": "CPU Safe Fixture",
              "latestPrice": 1000000,
              "stockQuantity": 1,
              "slug": "cpu-safe-fixture",
              "category": "cpu"
            }
          ]
        }
      }
    }
    </script>
    """

    sanitized = sanitize_next_data_html(raw)

    assert "SHOULD_NOT_SURVIVE" not in sanitized
    assert "window.env" not in sanitized
    assert extract_next_data_json(sanitized)["props"]["pageProps"]["serverProducts"][0][
        "sku"
    ] == "cpu-safe-1"

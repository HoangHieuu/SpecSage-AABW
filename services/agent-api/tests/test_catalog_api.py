from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.catalog_validation import validate_catalog
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _client() -> TestClient:
    items = _items()
    validation = validate_catalog(
        items,
        snapshot_version="catalog_test_api",
        generated_at=SNAPSHOT_AT,
    )
    snapshot = CatalogSnapshot(
        snapshot_version="catalog_test_api",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=items,
        validation=validation,
    )
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=snapshot)))


def test_catalog_health_exposes_snapshot_validation_state() -> None:
    response = _client().get("/catalog/health")

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_version"] == "catalog_test_api"
    assert body["sku_count"] == 11
    assert body["blocking_issue_count"] == 0
    assert body["demo_ready"] is True
    assert body["pilot_ready"] is False
    assert body["production_ready"] is False
    assert body["stale_after_days"] == 7
    assert body["freshness_status"] == "fresh"
    assert body["snapshot_fresh_until"] == "2026-07-04T00:00:00Z"
    assert body["category_counts"]["cpu"] == 1
    assert body["category_counts"]["vga"] == 2
    assert body["recommended_demo_category_counts"]["cpu"] == 2
    assert body["pilot_recommended_category_counts"]["cpu"] == 3
    assert body["production_target_category_counts"]["vga"] == 20
    assert body["specs_confidence_counts"]["verified"] == 11
    assert body["missing_required_demo_categories"] == []
    assert body["thin_demo_categories"] == ["cpu", "mainboard", "case"]
    assert body["thin_pilot_categories"] == [
        "cpu",
        "mainboard",
        "ram",
        "storage",
        "vga",
        "psu",
        "case",
    ]
    assert "monitor" in body["production_gap_categories"]
    assert any(
        issue["code"] == "CATALOG_THIN_DEMO_CATEGORY"
        and issue["field"] == "category_counts.mainboard"
        for issue in body["issues"]
    )
    assert any(
        issue["code"] == "CATALOG_PRODUCTION_TARGET_GAP"
        and issue["field"] == "category_counts"
        for issue in body["issues"]
    )


def test_catalog_query_filters_by_category_price_stock_and_vram() -> None:
    response = _client().get(
        "/catalog/skus",
        params={
            "category": "vga",
            "max_price_vnd": 8_000_000,
            "in_stock": True,
            "min_vram_gb": 8,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_version"] == "catalog_test_api"
    assert body["sku_count"] == 1
    assert body["items"][0]["sku"] == "260508255"
    assert body["items"][0]["specs_confidence"] == "verified"


def test_catalog_query_filters_by_socket() -> None:
    response = _client().get(
        "/catalog/skus",
        params={
            "category": "cpu",
            "socket": "LGA1700",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sku_count"] == 1
    assert body["items"][0]["sku"] == "211208130"

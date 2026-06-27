from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)
VALID_SELECTED = {
    "cpu": "211208130",
    "mainboard": "230203929",
    "ram": "210602265",
    "storage": "221000008",
    "vga": "260508255",
    "psu": "210800662",
    "case": "220101742",
}


def _client() -> TestClient:
    snapshot = CatalogSnapshot(
        snapshot_version="catalog_test_compat_api",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=snapshot)))


def test_validate_build_endpoint_approves_compatible_snapshot_build() -> None:
    response = _client().post(
        "/builds/build_valid/validate",
        json={"selected_skus": VALID_SELECTED},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["build_id"] == "build_valid"
    assert body["catalog_version"] == "catalog_test_compat_api"
    assert body["status"] == "approved"
    assert body["can_approve"] is True


def test_validate_build_endpoint_returns_blocked_report_for_bad_sku() -> None:
    response = _client().post(
        "/builds/build_bad_sku/validate",
        json={"selected_skus": {**VALID_SELECTED, "cpu": "not-in-catalog"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["can_approve"] is False
    assert any(result["rule_id"] == "CATALOG_SKU_NOT_FOUND" for result in body["results"])


def test_validate_build_endpoint_blocks_wrong_slot_category() -> None:
    response = _client().post(
        "/builds/build_wrong_slot/validate",
        json={"selected_skus": {**VALID_SELECTED, "cpu": "260508255"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert any(
        result["rule_id"] == "COMPAT_SLOT_CATEGORY_MISMATCH"
        for result in body["results"]
    )

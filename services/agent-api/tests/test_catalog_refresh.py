from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot import catalog_refresh
from pc_build_copilot.api import create_app
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.catalog_validation import validate_catalog
from pc_build_copilot.postgres_catalog import CatalogPublishBlockedError
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_refresh",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def _client() -> TestClient:
    return TestClient(
        create_app(
            store=SessionStore(),
            catalog_repository=CatalogRepository(snapshot=_snapshot()),
        )
    )


def _clear_database_env(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL_NON_POOLING", raising=False)


def test_catalog_refresh_requires_cron_secret(monkeypatch) -> None:
    monkeypatch.delenv("CRON_SECRET", raising=False)

    response = _client().get("/catalog/refresh")

    assert response.status_code == 503
    assert response.json()["detail"] == "CRON_SECRET is not configured."


def test_catalog_refresh_rejects_wrong_authorization(monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "expected-secret")

    response = _client().get(
        "/catalog/refresh",
        headers={"Authorization": "Bearer wrong-secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_catalog_refresh_requires_database_url(monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "expected-secret")
    _clear_database_env(monkeypatch)

    response = _client().get(
        "/catalog/refresh",
        headers={"Authorization": "Bearer expected-secret"},
    )

    assert response.status_code == 503
    assert "DATABASE_URL" in response.json()["detail"]


def test_catalog_refresh_loads_snapshot_through_postgres_loader(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CRON_SECRET", "expected-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/catalog")
    snapshot_path = tmp_path / "catalog_snapshot.json"
    snapshot_path.write_text(_snapshot().model_dump_json(), encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_default_catalog_snapshot_path():
        return snapshot_path

    def fake_load_catalog_snapshot(
        database_url: str,
        snapshot: CatalogSnapshot,
        *,
        allow_blocking: bool,
        load_options=None,
    ) -> CatalogSnapshot:
        assert database_url == "postgresql://example/catalog"
        assert snapshot.snapshot_version == "catalog_test_refresh"
        assert allow_blocking is False
        assert load_options == {
            "trigger": "vercel_cron",
            "snapshot_path": str(snapshot_path),
        }
        captured["loaded"] = True
        validation = validate_catalog(
            snapshot.items,
            snapshot_version=snapshot.snapshot_version,
            generated_at=snapshot.generated_at,
        )
        return snapshot.model_copy(update={"validation": validation})

    monkeypatch.setattr(
        catalog_refresh,
        "default_catalog_snapshot_path",
        fake_default_catalog_snapshot_path,
    )
    monkeypatch.setattr(
        catalog_refresh,
        "load_catalog_snapshot",
        fake_load_catalog_snapshot,
    )

    response = _client().get(
        "/catalog/refresh",
        headers={"Authorization": "Bearer expected-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert captured["loaded"] is True
    assert body["status"] == "loaded"
    assert body["trigger"] == "vercel_cron"
    assert body["snapshot_version"] == "catalog_test_refresh"
    assert body["sku_count"] == len(_items())
    assert body["blocking_issue_count"] == 0


def test_catalog_refresh_reports_blocked_validation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CRON_SECRET", "expected-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/catalog")
    broken_item = _items()[0].model_copy(update={"specs": {}})
    snapshot = CatalogSnapshot(
        snapshot_version="catalog_test_refresh_blocked",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=[broken_item],
    )
    snapshot_path = tmp_path / "catalog_snapshot.json"
    snapshot_path.write_text(snapshot.model_dump_json(), encoding="utf-8")

    def fake_default_catalog_snapshot_path():
        return snapshot_path

    def fake_load_catalog_snapshot(
        database_url: str,
        loaded_snapshot: CatalogSnapshot,
        *,
        allow_blocking: bool,
        load_options=None,
    ) -> CatalogSnapshot:
        validation = validate_catalog(
            loaded_snapshot.items,
            snapshot_version=loaded_snapshot.snapshot_version,
            generated_at=loaded_snapshot.generated_at,
        )
        raise CatalogPublishBlockedError(validation)

    monkeypatch.setattr(
        catalog_refresh,
        "default_catalog_snapshot_path",
        fake_default_catalog_snapshot_path,
    )
    monkeypatch.setattr(
        catalog_refresh,
        "load_catalog_snapshot",
        fake_load_catalog_snapshot,
    )

    response = _client().get(
        "/catalog/refresh",
        headers={"Authorization": "Bearer expected-secret"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["status"] == "blocked"
    assert detail["snapshot_version"] == "catalog_test_refresh_blocked"
    assert detail["blocking_issue_count"] > 0

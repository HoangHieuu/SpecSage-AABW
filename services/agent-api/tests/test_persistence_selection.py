from pathlib import Path

from fastapi.testclient import TestClient

from pc_build_copilot import api, persistence
from pc_build_copilot.build_store import BuildStore
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.postgres_store import POSTGRES_SCHEMA_STATEMENTS
from pc_build_copilot.sqlite_store import SqliteBuildStore, SqliteSessionStore
from pc_build_copilot.store import SessionStore


def test_resolve_postgres_url_prefers_database_url(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgresql://postgres-url")
    monkeypatch.setenv("DATABASE_URL", "postgresql://database-url")

    assert persistence.resolve_postgres_url() == "postgresql://database-url"


def test_create_persistent_stores_uses_sqlite_without_postgres_url(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "fallback.sqlite3"
    monkeypatch.setenv("PC_BUILD_COPILOT_DB_PATH", str(db_path))

    session_store, build_store = persistence.create_persistent_stores()

    assert isinstance(session_store, SqliteSessionStore)
    assert isinstance(build_store, SqliteBuildStore)
    assert db_path.exists()


def test_create_persistent_stores_uses_postgres_when_configured(
    monkeypatch,
) -> None:
    expected = (SessionStore(), BuildStore())
    captured_urls: list[str] = []

    def fake_create_postgres_stores(database_url: str) -> tuple[SessionStore, BuildStore]:
        captured_urls.append(database_url)
        return expected

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example/db")
    monkeypatch.setattr(
        persistence,
        "create_postgres_stores",
        fake_create_postgres_stores,
    )

    stores = persistence.create_persistent_stores()

    assert stores == expected
    assert captured_urls == ["postgresql://user:pass@example/db"]


def test_default_app_uses_persistent_store_factory(monkeypatch) -> None:
    calls: list[str] = []

    def fake_create_persistent_stores() -> tuple[SessionStore, BuildStore]:
        calls.append("called")
        return SessionStore(), BuildStore()

    monkeypatch.setattr(api, "create_persistent_stores", fake_create_persistent_stores)

    app = api.create_app(catalog_repository=CatalogRepository())
    client = TestClient(app)
    response = client.post("/sessions", json={})

    assert response.status_code == 200
    assert app.title == "PC Build Copilot Agent API"
    assert calls == ["called"]


def test_postgres_schema_matches_production_state_contract() -> None:
    schema = "\n".join(POSTGRES_SCHEMA_STATEMENTS)

    assert "build_sessions" in schema
    assert "intent_revisions" in schema
    assert "build_artifacts" in schema
    assert "cart_handoffs" in schema
    assert "build_feedback" in schema
    assert "payload_json JSONB NOT NULL" in schema
    assert "TIMESTAMPTZ NOT NULL" in schema
    assert "idx_pg_build_feedback_review_queued" in schema
    assert "WHERE review_queue_status = 'queued'" in schema

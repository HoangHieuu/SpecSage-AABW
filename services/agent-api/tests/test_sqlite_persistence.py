from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.sqlite_store import SqliteBuildStore, SqliteSessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_sqlite",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def _client(db_path: Path) -> TestClient:
    return TestClient(
        create_app(
            store=SqliteSessionStore(db_path),
            catalog_repository=CatalogRepository(snapshot=_snapshot()),
            build_store=SqliteBuildStore(db_path),
        )
    )


def test_sqlite_session_store_survives_app_reinstantiation(tmp_path: Path) -> None:
    db_path = tmp_path / "pc-build-copilot.sqlite3"
    client = _client(db_path)
    session = client.post("/sessions", json={}).json()

    intent = client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    ).json()

    restarted = _client(db_path)
    stored_session = restarted.get(f"/sessions/{session['build_session_id']}").json()
    revisions = restarted.get(
        f"/sessions/{session['build_session_id']}/intent-revisions"
    ).json()

    assert stored_session["build_session_id"] == session["build_session_id"]
    assert stored_session["state"] == "intent_confirmed"
    assert len(revisions) == 1
    assert revisions[0]["revision_id"] == intent["revision"]["revision_id"]
    assert revisions[0]["intent"]["budget_max"] == 25_000_000
    assert revisions[0]["confirmed"] is True


def test_sqlite_build_flow_survives_app_reinstantiation(tmp_path: Path) -> None:
    db_path = tmp_path / "pc-build-copilot.sqlite3"
    client = _client(db_path)
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    base_build = client.post(f"/sessions/{session['build_session_id']}/generate").json()
    alternatives = client.get(f"/builds/{base_build['build_id']}/alternatives").json()
    ram_upgrade = next(
        item for item in alternatives["alternatives"] if item["kind"] == "ram_upgrade"
    )
    applied_build = client.post(
        f"/builds/{base_build['build_id']}/alternatives/{ram_upgrade['variant_id']}/apply"
    ).json()
    handoff = client.post(f"/builds/{applied_build['build_id']}/approve").json()

    restarted = _client(db_path)
    stored_session = restarted.get(f"/sessions/{session['build_session_id']}").json()
    stored_base = restarted.get(f"/builds/{base_build['build_id']}").json()
    stored_applied = restarted.get(f"/builds/{applied_build['build_id']}").json()
    reloaded_alternatives = restarted.get(
        f"/builds/{applied_build['build_id']}/alternatives"
    ).json()
    repeated_handoff = restarted.post(f"/builds/{applied_build['build_id']}/approve").json()

    assert stored_session["state"] == "cart_ready"
    assert stored_base["build_version"] == 1
    assert [step["agent"] for step in stored_base["orchestration_trace"]] == [
        "intent",
        "catalog",
        "optimizer",
        "compatibility",
        "performance",
        "explainer",
        "commerce",
        "validator",
    ]
    assert any(item["slot"] == "ram" and item["sku"] == "210602265" for item in stored_base["items"])
    assert stored_applied["build_version"] == 2
    assert stored_applied["total_price_vnd"] == 17_890_000
    assert any(
        item["slot"] == "ram" and item["sku"] == "240601032"
        for item in stored_applied["items"]
    )
    assert len(reloaded_alternatives["alternatives"]) == 3
    assert repeated_handoff["handoff_id"] == handoff["handoff_id"]
    assert repeated_handoff["approval"]["approval_id"] == handoff["approval"]["approval_id"]


def test_default_app_uses_sqlite_path_from_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "default-app.sqlite3"
    monkeypatch.setenv("PC_BUILD_COPILOT_DB_PATH", str(db_path))

    client = TestClient(create_app(catalog_repository=CatalogRepository(snapshot=_snapshot())))
    session = client.post("/sessions", json={}).json()

    restarted = TestClient(create_app(catalog_repository=CatalogRepository(snapshot=_snapshot())))
    stored = restarted.get(f"/sessions/{session['build_session_id']}").json()

    assert db_path.exists()
    assert stored["build_session_id"] == session["build_session_id"]
    assert stored["state"] == "created"

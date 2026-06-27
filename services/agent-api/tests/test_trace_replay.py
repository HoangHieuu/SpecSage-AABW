from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.build_models import BuildArtifact, OrchestrationAgent
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.sqlite_store import SqliteBuildStore, SqliteSessionStore
from pc_build_copilot.store import SessionStore
from pc_build_copilot.trace_replay import build_trace_replay

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_trace",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def _client() -> TestClient:
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=_snapshot())))


def _confirmed_session(client: TestClient) -> str:
    session = client.post("/sessions", json={}).json()
    build_session_id = session["build_session_id"]
    client.post(
        f"/sessions/{build_session_id}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    return build_session_id


def test_build_trace_endpoint_returns_replay_fields() -> None:
    client = _client()
    build_session_id = _confirmed_session(client)
    build = client.post(f"/sessions/{build_session_id}/generate").json()

    response = client.get(f"/builds/{build['build_id']}/trace")

    assert response.status_code == 200
    body = response.json()
    assert body["build_session_id"] == build_session_id
    assert body["build_id"] == build["build_id"]
    assert body["build_version"] == 1
    assert body["replay_status"] == "complete"
    assert [event["agent"] for event in body["events"]] == [
        "catalog",
        "optimizer",
        "compatibility",
        "performance",
        "explainer",
        "validator",
    ]
    first = body["events"][0]
    assert first["sequence"] == 1
    assert first["tool_calls"] == ["catalog_snapshot.read", "catalog_stock.filter"]
    assert first["model_version"] == "catalog-snapshot:catalog_test_trace"
    assert isinstance(first["latency_ms"], int)


def test_session_trace_endpoint_links_build_versions_and_export_text() -> None:
    client = _client()
    build_session_id = _confirmed_session(client)
    base_build = client.post(f"/sessions/{build_session_id}/generate").json()
    alternatives = client.get(f"/builds/{base_build['build_id']}/alternatives").json()
    ram_upgrade = next(
        item for item in alternatives["alternatives"] if item["kind"] == "ram_upgrade"
    )
    applied_build = client.post(
        f"/builds/{base_build['build_id']}/alternatives/{ram_upgrade['variant_id']}/apply"
    ).json()

    response = client.get(f"/sessions/{build_session_id}/trace")

    assert response.status_code == 200
    body = response.json()
    assert body["build_session_id"] == build_session_id
    assert body["generated_build_count"] == 2
    assert "free-text intent" in body["redaction_policy_vi"]
    assert f"Session: {build_session_id}" in body["support_export_text"]
    assert "Build v1" in body["support_export_text"]
    assert "Build v2" in body["support_export_text"]
    assert [build["build_version"] for build in body["builds"]] == [1, 2]
    assert body["builds"][0]["build_id"] == base_build["build_id"]
    assert body["builds"][0]["replay_status"] == "complete"
    assert body["builds"][1]["build_id"] == applied_build["build_id"]
    assert body["builds"][1]["replay_status"] == "empty"
    assert body["builds"][1]["events"] == []


def test_trace_replay_redacts_sensitive_step_payload() -> None:
    client = _client()
    build_session_id = _confirmed_session(client)
    build = client.post(f"/sessions/{build_session_id}/generate").json()
    artifact = client.get(f"/builds/{build['build_id']}").json()
    artifact["orchestration_trace"][0]["inputs"] = {
        "raw_text": "Nguyen Van A 0901234567 email a@example.com"
    }

    replay = build_trace_replay(BuildArtifact.model_validate(artifact))

    assert replay.events[0].agent == OrchestrationAgent.CATALOG
    assert replay.events[0].inputs_redacted["raw_text"] == "[redacted]"


def test_sqlite_session_trace_survives_app_reinstantiation(tmp_path: Path) -> None:
    db_path = tmp_path / "trace.sqlite3"
    client = TestClient(
        create_app(
            store=SqliteSessionStore(db_path),
            catalog_repository=CatalogRepository(snapshot=_snapshot()),
            build_store=SqliteBuildStore(db_path),
        )
    )
    build_session_id = _confirmed_session(client)
    build = client.post(f"/sessions/{build_session_id}/generate").json()

    restarted = TestClient(
        create_app(
            store=SqliteSessionStore(db_path),
            catalog_repository=CatalogRepository(snapshot=_snapshot()),
            build_store=SqliteBuildStore(db_path),
        )
    )
    trace = restarted.get(f"/sessions/{build_session_id}/trace").json()

    assert trace["build_session_id"] == build_session_id
    assert trace["generated_build_count"] == 1
    assert trace["builds"][0]["build_id"] == build["build_id"]
    assert trace["builds"][0]["events"][-1]["agent"] == "validator"

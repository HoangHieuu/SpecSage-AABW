from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.models import SessionState
from pc_build_copilot.store import SessionStore


def test_create_session_defaults_to_vietnamese_web_channel() -> None:
    client = TestClient(create_app(SessionStore()))

    response = client.post("/sessions", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["build_session_id"].startswith("bs_")
    assert body["locale"] == "vi-VN"
    assert body["channel"] == "web"
    assert body["state"] == SessionState.CREATED
    assert body["ttl_expires_at"]


def test_submit_intent_stores_revision_and_confirms_when_complete() -> None:
    client = TestClient(create_app(SessionStore()))
    session = client.post("/sessions", json={}).json()

    response = client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant 144Hz",
            "confirm": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["state"] == SessionState.INTENT_CONFIRMED
    assert body["revision"]["confirmed"] is True
    assert body["revision"]["intent"]["budget_max"] == 25_000_000
    assert body["revision"]["clarification"]["field"] is None


def test_submit_intent_with_missing_budget_remains_draft() -> None:
    client = TestClient(create_app(SessionStore()))
    session = client.post("/sessions", json={}).json()

    response = client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={"message": "PC gaming chơi Valorant", "confirm": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["state"] == SessionState.INTENT_DRAFT
    assert body["revision"]["confirmed"] is False
    assert body["revision"]["clarification"]["field"] == "budget"

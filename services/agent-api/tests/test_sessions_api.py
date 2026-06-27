from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.models import AgentAnalysisStatus, IntentAgentAnalysis, SessionState
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


def test_submit_intent_can_include_openrouter_agent_analysis() -> None:
    class FakeAdvisor:
        def __init__(self) -> None:
            self.calls = 0

        def analyze(self, message: object, intent: object, clarification: object) -> IntentAgentAnalysis:
            self.calls += 1
            return IntentAgentAnalysis(
                model="deepseek/deepseek-v4-flash",
                status=AgentAnalysisStatus.AVAILABLE,
                summary_vi="Khách muốn PC gaming trong ngân sách 25 triệu.",
                confidence_notes_vi=["Parser đã nhận ngân sách."],
                safety_notes_vi=["LLM không quyết định SKU."],
            )

    advisor = FakeAdvisor()
    client = TestClient(create_app(store=SessionStore(), intent_advisor=advisor))
    session = client.post("/sessions", json={}).json()

    response = client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant 144Hz",
            "use_llm": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_analysis"]["provider"] == "openrouter"
    assert body["agent_analysis"]["model"] == "deepseek/deepseek-v4-flash"
    assert body["agent_analysis"]["status"] == AgentAnalysisStatus.AVAILABLE
    assert body["revision"]["intent"]["budget_max"] == 25_000_000
    assert advisor.calls == 1


def test_submit_intent_does_not_call_agent_on_confirm_or_opt_out() -> None:
    class FakeAdvisor:
        def __init__(self) -> None:
            self.calls = 0

        def analyze(self, message: object, intent: object, clarification: object) -> IntentAgentAnalysis:
            self.calls += 1
            return IntentAgentAnalysis(
                model="deepseek/deepseek-v4-flash",
                status=AgentAnalysisStatus.AVAILABLE,
            )

    advisor = FakeAdvisor()
    client = TestClient(create_app(store=SessionStore(), intent_advisor=advisor))
    session = client.post("/sessions", json={}).json()

    opted_out = client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant 144Hz",
            "use_llm": False,
        },
    )
    confirm = client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant 144Hz",
            "confirm": True,
            "use_llm": True,
        },
    )

    assert opted_out.status_code == 200
    assert opted_out.json()["agent_analysis"] is None
    assert confirm.status_code == 200
    assert confirm.json()["agent_analysis"] is None
    assert advisor.calls == 0

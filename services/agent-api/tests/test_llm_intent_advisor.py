from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
import json

from pytest import MonkeyPatch

from pc_build_copilot.intent_parser import parse_intent
from pc_build_copilot.llm_config import (
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterSettings,
    load_env_file,
    openrouter_settings,
)
from pc_build_copilot.llm_intent_advisor import BOUNDARY_NOTE, LlmIntentAdvisor
from pc_build_copilot.models import AgentAnalysisStatus
from pc_build_copilot.openrouter_client import OpenRouterClient, OpenRouterError


def test_openrouter_settings_loads_local_env_file_without_exposing_key(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    for key in [
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_TIMEOUT_SECONDS",
        "OPENROUTER_MAX_TOKENS",
        "LLM_AGENT_ENABLED",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY='sk-test-value'",
                "OPENROUTER_MODEL=deepseek/deepseek-v4-flash",
                "OPENROUTER_TIMEOUT_SECONDS=3.5",
                "OPENROUTER_MAX_TOKENS=180",
            ]
        ),
        encoding="utf-8",
    )

    values = load_env_file(env_file)
    settings = openrouter_settings(env_file=env_file, env={})

    assert values["OPENROUTER_API_KEY"] == "sk-test-value"
    assert settings.api_key == "sk-test-value"
    assert settings.enabled is True
    assert settings.model == DEFAULT_OPENROUTER_MODEL
    assert settings.timeout_seconds == 3.5
    assert settings.max_tokens == 180


def test_openrouter_client_sends_chat_completion_json_request() -> None:
    captured: dict[str, object] = {}

    def fake_transport(request: Request, timeout: float) -> bytes:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = json.loads((request.data or b"{}").decode("utf-8"))
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary_vi": "Khách cần PC gaming.",
                                    "confidence_notes_vi": ["Đã nhận ngân sách."],
                                    "safety_notes_vi": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }
        ).encode("utf-8")

    client = OpenRouterClient(
        OpenRouterSettings(
            api_key="sk-test",
            enabled=True,
            model="deepseek/deepseek-v4-flash",
            base_url="https://openrouter.test/api/v1",
            site_url="http://localhost:3000",
            app_name="PC Build Copilot Test",
            timeout_seconds=2,
            max_tokens=123,
        ),
        transport=fake_transport,
    )

    payload = client.chat_json([{"role": "user", "content": "hello"}])

    assert payload["summary_vi"] == "Khách cần PC gaming."
    assert captured["url"] == "https://openrouter.test/api/v1/chat/completions"
    assert captured["timeout"] == 2
    assert captured["headers"]["authorization"] == "Bearer sk-test"
    assert captured["headers"]["http-referer"] == "http://localhost:3000"
    assert captured["headers"]["x-openrouter-title"] == "PC Build Copilot Test"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "deepseek/deepseek-v4-flash"
    assert body["response_format"] == {"type": "json_object"}
    assert body["provider"] == {"require_parameters": True}
    assert body["max_tokens"] == 123


def test_openrouter_client_falls_back_when_json_mode_is_rejected() -> None:
    request_bodies: list[dict[str, object]] = []

    def fake_transport(request: Request, timeout: float) -> bytes:
        body = json.loads((request.data or b"{}").decode("utf-8"))
        request_bodies.append(body)
        if len(request_bodies) == 1:
            raise HTTPError(request.full_url, 400, "Bad Request", hdrs=None, fp=None)
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"summary_vi": "Fallback vẫn trả JSON hợp lệ."},
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }
        ).encode("utf-8")

    client = OpenRouterClient(
        OpenRouterSettings(api_key="sk-test", enabled=True, model="deepseek/deepseek-v4-flash"),
        transport=fake_transport,
    )

    payload = client.chat_json([{"role": "user", "content": "hello"}])

    assert payload["summary_vi"] == "Fallback vẫn trả JSON hợp lệ."
    assert request_bodies[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in request_bodies[1]
    assert "provider" not in request_bodies[1]


def test_llm_intent_advisor_returns_analysis_without_mutating_intent() -> None:
    intent, clarification = parse_intent("PC gaming 25 triệu chơi Valorant 144Hz")
    original_intent = intent.model_dump()

    class FakeClient:
        def chat_json(self, messages: object) -> dict[str, object]:
            return {
                "summary_vi": "Khách muốn PC gaming trong ngân sách 25 triệu cho Valorant 144Hz.",
                "clarification_vi": None,
                "confidence_notes_vi": ["Đã nhận use case gaming và ngân sách."],
                "safety_notes_vi": ["Chưa chọn SKU trong bước này."],
            }

    advisor = LlmIntentAdvisor(
        OpenRouterSettings(api_key="sk-test", enabled=True, model="deepseek/deepseek-v4-flash"),
        client=FakeClient(),  # type: ignore[arg-type]
    )

    analysis = advisor.analyze("PC gaming 25 triệu chơi Valorant 144Hz", intent, clarification)

    assert analysis.status == AgentAnalysisStatus.AVAILABLE
    assert analysis.model == "deepseek/deepseek-v4-flash"
    assert analysis.summary_vi
    assert BOUNDARY_NOTE in analysis.safety_notes_vi
    assert intent.model_dump() == original_intent


def test_llm_intent_advisor_degrades_when_provider_response_is_invalid() -> None:
    intent, clarification = parse_intent("PC gaming 25 triệu chơi Valorant 144Hz")

    class BrokenClient:
        def chat_json(self, messages: object) -> dict[str, object]:
            raise OpenRouterError("provider unavailable")

    advisor = LlmIntentAdvisor(
        OpenRouterSettings(api_key="sk-test", enabled=True, model="deepseek/deepseek-v4-flash"),
        client=BrokenClient(),  # type: ignore[arg-type]
    )

    analysis = advisor.analyze("PC gaming 25 triệu chơi Valorant 144Hz", intent, clarification)

    assert analysis.status == AgentAnalysisStatus.DEGRADED
    assert analysis.raw_json_valid is False
    assert analysis.error_vi
    assert analysis.safety_notes_vi == [BOUNDARY_NOTE]

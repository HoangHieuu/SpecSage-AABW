from pathlib import Path
from typing import Any
import json

from pydantic import BaseModel, Field, ValidationError

from pc_build_copilot.llm_config import OpenRouterSettings, openrouter_settings
from pc_build_copilot.models import (
    AgentAnalysisStatus,
    BuildIntent,
    Clarification,
    IntentAgentAnalysis,
)
from pc_build_copilot.openrouter_client import OpenRouterClient, OpenRouterError


BOUNDARY_NOTE = (
    "LLM chỉ giải thích intent; SKU, giá, ngân sách và tương thích vẫn do catalog "
    "và rule engine quyết định."
)


class IntentAdvisorPayload(BaseModel):
    summary_vi: str | None = None
    clarification_vi: str | None = None
    confidence_notes_vi: list[str] = Field(default_factory=list)
    safety_notes_vi: list[str] = Field(default_factory=list)


class LlmIntentAdvisor:
    def __init__(
        self,
        settings: OpenRouterSettings,
        client: OpenRouterClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or OpenRouterClient(settings)

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "LlmIntentAdvisor":
        settings = openrouter_settings(env_file=env_file)
        return cls(settings=settings)

    def analyze(
        self,
        message: str,
        intent: BuildIntent,
        clarification: Clarification,
    ) -> IntentAgentAnalysis:
        if not self._settings.enabled or not self._settings.api_key:
            return IntentAgentAnalysis(
                model=self._settings.model,
                status=AgentAnalysisStatus.DISABLED,
                raw_json_valid=False,
                error_vi="LLM Agent chưa được bật vì thiếu OPENROUTER_API_KEY.",
            )

        try:
            raw_payload = self._client.chat_json(
                [
                    {"role": "system", "content": _system_prompt()},
                    {
                        "role": "user",
                        "content": _user_prompt(message, intent, clarification),
                    },
                ]
            )
            payload = IntentAdvisorPayload.model_validate(raw_payload)
        except (OpenRouterError, ValidationError) as exc:
            return IntentAgentAnalysis(
                model=self._settings.model,
                status=AgentAnalysisStatus.DEGRADED,
                raw_json_valid=False,
                error_vi=(
                    "LLM Agent tạm thời chưa khả dụng; hệ thống vẫn dùng parser "
                    "và rule engine deterministic."
                ),
                safety_notes_vi=[BOUNDARY_NOTE],
            )

        return IntentAgentAnalysis(
            model=self._settings.model,
            status=AgentAnalysisStatus.AVAILABLE,
            summary_vi=_trim_text(payload.summary_vi, 700),
            clarification_vi=_trim_text(payload.clarification_vi, 360),
            confidence_notes_vi=_trim_notes(payload.confidence_notes_vi, limit=4),
            safety_notes_vi=_append_boundary_note(
                _trim_notes(payload.safety_notes_vi, limit=4)
            ),
            raw_json_valid=True,
        )


def _system_prompt() -> str:
    return (
        "Bạn là LLM Agent phụ trợ cho PC Build Copilot tại Việt Nam. "
        "Chỉ trả về một JSON object hợp lệ, không markdown. "
        "Dữ liệu deterministic trong prompt là nguồn sự thật. "
        "Không tự chọn SKU, không tự bịa giá, FPS, tồn kho, benchmark hoặc tương thích. "
        "Viết tiếng Việt ngắn gọn cho khách mua PC."
    )


def _user_prompt(
    message: str,
    intent: BuildIntent,
    clarification: Clarification,
) -> str:
    facts: dict[str, Any] = {
        "customer_message": message,
        "deterministic_intent": intent.model_dump(mode="json"),
        "deterministic_clarification": clarification.model_dump(mode="json"),
    }
    return (
        "Hãy đọc facts và trả về đúng JSON shape sau:\n"
        "{\n"
        '  "summary_vi": "1-2 câu tóm tắt nhu cầu khách hàng",\n'
        '  "clarification_vi": "câu hỏi gợi ý nếu còn thiếu thông tin, hoặc null",\n'
        '  "confidence_notes_vi": ["tối đa 2 ghi chú ngắn về phần đã hiểu chắc"],\n'
        '  "safety_notes_vi": ["tối đa 2 ghi chú ngắn về giới hạn: không quyết định SKU/giá/rule"]\n'
        "}\n\n"
        "Facts:\n"
        f"{json.dumps(facts, ensure_ascii=False)}"
    )


def _trim_text(value: str | None, max_chars: int) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 1].rstrip()}..."


def _trim_notes(values: list[str], limit: int) -> list[str]:
    notes = []
    for value in values:
        note = _trim_text(value, 220)
        if note:
            notes.append(note)
        if len(notes) >= limit:
            break
    return notes


def _append_boundary_note(notes: list[str]) -> list[str]:
    if BOUNDARY_NOTE not in notes:
        notes.append(BOUNDARY_NOTE)
    return notes

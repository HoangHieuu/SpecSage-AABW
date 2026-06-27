from __future__ import annotations

import re

from pc_build_copilot.build_models import (
    BuildArtifact,
    BuildTraceReplay,
    SessionTraceReplay,
    TraceReplayEvent,
)


REDACTION_POLICY_VI = (
    "Trace replay chỉ xuất dữ liệu cấu trúc cần debug; free-text intent, email, "
    "số điện thoại và trường định danh cá nhân được ẩn trước khi export."
)

_SENSITIVE_KEY_PARTS = ("raw", "message", "email", "phone", "name", "address")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?:\+?84|0)(?:[\s.-]?\d){8,10}")


def build_trace_replay(artifact: BuildArtifact) -> BuildTraceReplay:
    events = [
        TraceReplayEvent(
            event_id=f"{artifact.build_id}:{index}:{step.agent.value}",
            sequence=index,
            build_session_id=artifact.build_session_id,
            build_id=artifact.build_id,
            build_version=artifact.build_version,
            generated_at=artifact.generated_at,
            agent=step.agent,
            status=step.status,
            summary_vi=step.summary_vi,
            inputs_redacted=_redact_payload(step.inputs),
            tool_calls=step.tool_calls,
            outputs_redacted=_redact_payload(step.outputs),
            latency_ms=step.latency_ms,
            model_version=step.model_version,
        )
        for index, step in enumerate(artifact.orchestration_trace, start=1)
    ]
    return BuildTraceReplay(
        build_session_id=artifact.build_session_id,
        build_id=artifact.build_id,
        build_version=artifact.build_version,
        generated_at=artifact.generated_at,
        replay_status="complete" if events else "empty",
        events=events,
    )


def session_trace_replay(
    *,
    build_session_id: str,
    artifacts: list[BuildArtifact],
) -> SessionTraceReplay:
    builds = [build_trace_replay(artifact) for artifact in artifacts]
    return SessionTraceReplay(
        build_session_id=build_session_id,
        generated_build_count=len(builds),
        redaction_policy_vi=REDACTION_POLICY_VI,
        support_export_text=_support_export_text(build_session_id, builds),
        builds=builds,
    )


def _support_export_text(
    build_session_id: str,
    builds: list[BuildTraceReplay],
) -> str:
    lines = [
        "PC Build Copilot trace export",
        f"Session: {build_session_id}",
        f"Build versions: {len(builds)}",
        f"Redaction: {REDACTION_POLICY_VI}",
    ]
    for build in builds:
        lines.append("")
        lines.append(
            f"Build v{build.build_version}: {build.build_id} "
            f"({build.replay_status}, {len(build.events)} events)"
        )
        for event in build.events:
            tool_text = ", ".join(event.tool_calls) if event.tool_calls else "none"
            lines.append(
                f"{event.sequence}. {event.agent.value} [{event.status.value}] "
                f"model={event.model_version} latency_ms={event.latency_ms} tools={tool_text}"
            )
            lines.append(f"   summary={event.summary_vi}")
            lines.append(f"   inputs={event.inputs_redacted}")
            lines.append(f"   outputs={event.outputs_redacted}")
    return "\n".join(lines)


def _redact_payload(
    payload: dict[str, str | int | bool | None],
) -> dict[str, str | int | bool | None]:
    redacted: dict[str, str | int | bool | None] = {}
    for key, value in payload.items():
        if _is_sensitive_key(key):
            redacted[key] = "[redacted]"
        elif isinstance(value, str):
            redacted[key] = _redact_text(value)
        else:
            redacted[key] = value
    return redacted


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold()
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    value = _EMAIL_RE.sub("[redacted-email]", value)
    return _PHONE_RE.sub("[redacted-phone]", value)

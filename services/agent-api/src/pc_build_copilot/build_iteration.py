from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from time import perf_counter

from fastapi import HTTPException

from pc_build_copilot.build_alternatives import (
    apply_build_alternative,
    generate_build_alternatives,
)
from pc_build_copilot.build_models import (
    BudgetStatus,
    BuildAlternative,
    BuildAlternativeKind,
    BuildArtifact,
    BuildIterationRequest,
    BuildIterationResponse,
    BuildOrchestrationStep,
    OptimizerIterationDecision,
    OptimizerTrace,
    OrchestrationAgent,
    ParsedBuildIterationCommand,
)
from pc_build_copilot.catalog_models import CatalogSnapshot


COMMAND_KIND_ORDER: dict[str, tuple[BuildAlternativeKind, ...]] = {
    "cheaper": (BuildAlternativeKind.BUDGET_SAVER,),
    "quieter": (BuildAlternativeKind.PSU_HEADROOM,),
    "more_performance": (BuildAlternativeKind.NVIDIA_GPU,),
    "nvidia_gpu": (BuildAlternativeKind.NVIDIA_GPU,),
    "more_storage": (BuildAlternativeKind.STORAGE_UPGRADE,),
    "more_memory": (BuildAlternativeKind.RAM_UPGRADE,),
}


def iterate_build_from_command(
    *,
    base_artifact: BuildArtifact,
    payload: BuildIterationRequest,
    catalog: CatalogSnapshot,
) -> BuildIterationResponse:
    started_at = datetime.now(UTC)
    start = perf_counter()
    command = parse_iteration_command(payload.command_vi)
    if command.command_type == "unknown":
        raise HTTPException(
            status_code=422,
            detail="iteration command is not supported by the deterministic parser",
        )

    response = generate_build_alternatives(
        base_artifact=base_artifact,
        catalog=catalog,
        include_budget_savers=command.command_type == "cheaper",
    )
    selected, rejected = _select_iteration_alternative(
        command=command,
        base_artifact=base_artifact,
        alternatives=response.alternatives,
    )
    if selected is None:
        raise HTTPException(
            status_code=409,
            detail="no compatible in-budget variant matched this iteration command",
        )

    applied = apply_build_alternative(
        base_artifact=base_artifact,
        variant_id=selected.variant_id,
        catalog=catalog,
        include_budget_savers=command.command_type == "cheaper",
    )
    if applied is None:
        raise HTTPException(status_code=404, detail="variant_id not found")

    iteration_number = _next_iteration_number(base_artifact.optimizer_trace)
    accepted = _decision_for_alternative(
        iteration=iteration_number,
        alternative=selected,
        decision="accepted",
        reason_vi=(
            f"Chọn từ yêu cầu điều chỉnh '{command.command_vi}' vì khớp "
            f"{command.priority_label_vi} và vẫn đạt budget/compatibility gates."
        ),
    )
    rejected = [
        item.model_copy(update={"iteration": iteration_number})
        for item in rejected
    ]
    applied = applied.model_copy(
        update={
            "optimizer_trace": _append_iteration_decisions(
                base_artifact.optimizer_trace,
                [*rejected, accepted],
                iteration_number,
            ),
            "explanations_vi": [
                (
                    f"Đã xử lý yêu cầu điều chỉnh '{command.command_vi}' bằng biến thể "
                    f"{selected.label_vi}."
                ),
                *applied.explanations_vi,
            ],
            "orchestration_trace": [
                _iteration_step(
                    command=command,
                    selected=selected,
                    applied=applied,
                    started_at=started_at,
                    latency_ms=_elapsed_ms(start),
                )
            ],
        }
    )

    return BuildIterationResponse(
        source_build_id=base_artifact.build_id,
        source_build_version=base_artifact.build_version,
        command=command,
        selected_alternative=selected,
        applied_build=applied,
        rejected_candidates=rejected,
    )


def parse_iteration_command(command_vi: str) -> ParsedBuildIterationCommand:
    normalized = _normalize(command_vi)
    budget_cap = _parse_budget_cap(normalized)

    if _has_any(normalized, ("nvidia", "rtx")):
        command_type = "nvidia_gpu"
        label = "ưu tiên NVIDIA/GPU"
    elif _has_any(normalized, ("fps", "hieu nang", "manh hon", "gaming hon", "vga", "gpu")):
        command_type = "more_performance"
        label = "ưu tiên hiệu năng/GPU"
    elif _has_any(normalized, ("ssd", "o cung", "luu tru", "dung luong")):
        command_type = "more_storage"
        label = "ưu tiên SSD/lưu trữ"
    elif _has_any(normalized, ("ram", "bo nho")):
        command_type = "more_memory"
        label = "ưu tiên RAM"
    elif _has_any(normalized, ("em hon", "im lang", "it on", "quiet", "silent")):
        command_type = "quieter"
        label = "ưu tiên vận hành êm"
    elif budget_cap is not None or _has_any(
        normalized,
        ("re hon", "giam gia", "giam chi phi", "tiet kiem", "duoi", "under"),
    ):
        command_type = "cheaper"
        label = "ưu tiên giảm chi phí"
    else:
        command_type = "unknown"
        label = "chưa nhận diện"

    summary = f"Yêu cầu điều chỉnh: {label}."
    if budget_cap is not None:
        summary = f"{summary} Giữ tổng giá tối đa {_format_vnd(budget_cap)}."

    return ParsedBuildIterationCommand(
        command_vi=command_vi.strip(),
        command_type=command_type,
        target_budget_max_vnd=budget_cap,
        priority_label_vi=label,
        summary_vi=summary,
    )


def _select_iteration_alternative(
    *,
    command: ParsedBuildIterationCommand,
    base_artifact: BuildArtifact,
    alternatives: list[BuildAlternative],
) -> tuple[BuildAlternative | None, list[OptimizerIterationDecision]]:
    desired_kinds = COMMAND_KIND_ORDER.get(command.command_type, ())
    rejected: list[OptimizerIterationDecision] = []
    for alternative in alternatives:
        rejection_reason = _rejection_reason(command, base_artifact, alternative, desired_kinds)
        if rejection_reason is not None:
            rejected.append(
                _decision_for_alternative(
                    iteration=0,
                    alternative=alternative,
                    decision="rejected",
                    reason_vi=rejection_reason,
                )
            )
            continue
        return alternative, rejected
    return None, rejected


def _rejection_reason(
    command: ParsedBuildIterationCommand,
    base_artifact: BuildArtifact,
    alternative: BuildAlternative,
    desired_kinds: tuple[BuildAlternativeKind, ...],
) -> str | None:
    if alternative.kind not in desired_kinds:
        return "Biến thể không khớp loại điều chỉnh người dùng vừa yêu cầu."
    if not alternative.can_approve or alternative.budget_status != BudgetStatus.WITHIN_BUDGET:
        return "Biến thể bị loại vì chưa qua budget hoặc compatibility gate."
    if command.command_type == "cheaper" and alternative.price_delta_vnd >= 0:
        return "Biến thể bị loại vì không giảm tổng giá."
    if command.target_budget_max_vnd is not None:
        if alternative.total_price_vnd > command.target_budget_max_vnd:
            return "Biến thể bị loại vì vượt giới hạn ngân sách trong câu lệnh."
    elif command.command_type == "cheaper" and alternative.total_price_vnd >= base_artifact.total_price_vnd:
        return "Biến thể bị loại vì không làm build hiện tại rẻ hơn."
    return None


def _append_iteration_decisions(
    optimizer_trace: OptimizerTrace | None,
    decisions: list[OptimizerIterationDecision],
    iteration_number: int,
) -> OptimizerTrace | None:
    if optimizer_trace is None:
        return None
    iterations = [*optimizer_trace.iterations, *decisions]
    return optimizer_trace.model_copy(
        update={
            "max_iterations": max(optimizer_trace.max_iterations, iteration_number),
            "iterations": iterations,
            "applied_iteration_count": sum(
                1 for item in iterations if item.decision == "accepted"
            ),
            "rejected_iteration_count": sum(
                1 for item in iterations if item.decision == "rejected"
            ),
        }
    )


def _next_iteration_number(optimizer_trace: OptimizerTrace | None) -> int:
    if optimizer_trace is None or not optimizer_trace.iterations:
        return 1
    return max(item.iteration for item in optimizer_trace.iterations) + 1


def _decision_for_alternative(
    *,
    iteration: int,
    alternative: BuildAlternative,
    decision: str,
    reason_vi: str,
) -> OptimizerIterationDecision:
    return OptimizerIterationDecision(
        iteration=iteration,
        candidate_kind=alternative.kind.value,
        candidate_label_vi=alternative.label_vi,
        decision=decision,
        score=alternative.ranking.score,
        priority=alternative.ranking.priority,
        price_delta_vnd=alternative.price_delta_vnd,
        total_price_vnd=alternative.total_price_vnd,
        changed_slots=[slot.slot.value for slot in alternative.changed_slots],
        reason_vi=reason_vi,
    )


def _iteration_step(
    *,
    command: ParsedBuildIterationCommand,
    selected: BuildAlternative,
    applied: BuildArtifact,
    started_at: datetime,
    latency_ms: int,
) -> BuildOrchestrationStep:
    return BuildOrchestrationStep(
        agent=OrchestrationAgent.OPTIMIZER,
        summary_vi="Optimizer Agent xử lý yêu cầu điều chỉnh tự nhiên bằng biến thể deterministic.",
        inputs={
            "command_type": command.command_type,
            "target_budget_max_vnd": command.target_budget_max_vnd,
        },
        outputs={
            "build_id": applied.build_id,
            "build_version": applied.build_version,
            "selected_variant_kind": selected.kind.value,
            "price_delta_vnd": selected.price_delta_vnd,
            "total_price_vnd": applied.total_price_vnd,
        },
        tool_calls=[
            "build_iteration.parse_iteration_command",
            "build_alternatives.generate_build_alternatives",
            "build_alternatives.apply_build_alternative",
        ],
        model_version="deterministic-iteration-command-v1",
        started_at=started_at,
        latency_ms=latency_ms,
    )


def _elapsed_ms(start: float) -> int:
    return max(0, round((perf_counter() - start) * 1000))


def _parse_budget_cap(normalized: str) -> int | None:
    match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(trieu|tr|m)\b", normalized)
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    return int(amount * 1_000_000)


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value).lower()
    ascii_text = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", ascii_text).strip()


def _format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " VND"

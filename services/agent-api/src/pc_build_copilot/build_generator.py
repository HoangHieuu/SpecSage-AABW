from __future__ import annotations

from collections.abc import Iterable
from uuid import uuid4

from pc_build_copilot.build_models import (
    BudgetStatus,
    BuildAlternative,
    BuildAlternativeKind,
    BuildArtifact,
    BuildItem,
    BuildStatus,
    MockCartPayload,
    OptimizerIterationDecision,
    OptimizerTrace,
)
from pc_build_copilot.catalog_models import CatalogSku, CatalogSnapshot, ComponentCategory
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.compatibility_rules import validate_build_compatibility
from pc_build_copilot.models import BuildIntent, UseCase
from pc_build_copilot.optimizer_policy import (
    build_budget_allocation,
    priority_labels_vi,
    priority_overrides_for_intent,
)
from pc_build_copilot.performance_profile import generate_performance_profile


REQUIRED_BASE_SLOTS = (
    BuildSlot.CPU,
    BuildSlot.MAINBOARD,
    BuildSlot.RAM,
    BuildSlot.STORAGE,
    BuildSlot.PSU,
    BuildSlot.CASE,
)
OPTIMIZER_MAX_SWAPS = 2
OPTIMIZER_USE_CASES = {UseCase.CREATOR, UseCase.AI, UseCase.STREAMING, UseCase.GAMING}
GAMING_OPTIMIZER_MIN_SCORE = 70


def generate_build_artifact(
    *,
    build_session_id: str,
    intent: BuildIntent,
    catalog: CatalogSnapshot,
    optimize: bool = True,
) -> BuildArtifact:
    selected = _select_skus(intent, catalog.items)
    build_id = f"build_{uuid4().hex}"
    optimizer_trace = _new_optimizer_trace(
        intent=intent,
        max_iterations=OPTIMIZER_MAX_SWAPS if optimize else 0,
    )
    artifact = _build_artifact_from_selected(
        build_id=build_id,
        build_session_id=build_session_id,
        intent=intent,
        catalog=catalog,
        selected=selected,
        optimizer_notes=[],
        optimizer_trace=optimizer_trace,
    )
    if not optimize:
        return artifact

    optimized_selected, optimizer_notes, optimizer_trace = _budget_aware_improvement_pass(
        artifact=artifact,
        catalog=catalog,
    )
    if not optimizer_notes:
        return artifact.model_copy(update={"optimizer_trace": optimizer_trace})
    return _build_artifact_from_selected(
        build_id=build_id,
        build_session_id=build_session_id,
        intent=intent,
        catalog=catalog,
        selected=optimized_selected,
        optimizer_notes=optimizer_notes,
        optimizer_trace=optimizer_trace,
    )


def _build_artifact_from_selected(
    *,
    build_id: str,
    build_session_id: str,
    intent: BuildIntent,
    catalog: CatalogSnapshot,
    selected: dict[BuildSlot, CatalogSku],
    optimizer_notes: list[str],
    optimizer_trace: OptimizerTrace,
) -> BuildArtifact:
    compatibility_report = validate_build_compatibility(
        build_id=build_id,
        selected_skus={slot: sku.sku for slot, sku in selected.items()},
        catalog=catalog,
    )
    total_price = sum(item.price_vnd for item in selected.values())
    budget_status, budget_gap = _budget_status(total_price, intent.budget_max)
    can_approve = compatibility_report.can_approve and budget_status != BudgetStatus.OVER_BUDGET
    status = _build_status(compatibility_report.can_approve, budget_status)
    performance_profile = generate_performance_profile(intent=intent, selected_skus=selected)

    items = [
        BuildItem(
            slot=slot,
            sku=item.sku,
            name=item.name,
            category=item.category,
            price_vnd=item.price_vnd,
            url=item.url,
            brand=item.brand,
            specs_confidence=item.specs_confidence,
            explanation_vi=_item_explanation(slot, item, intent),
        )
        for slot, item in selected.items()
    ]

    warnings = [
        *_budget_warnings(total_price, intent.budget_max, budget_gap),
        *performance_profile.warnings_vi,
    ]
    if not compatibility_report.can_approve:
        warnings.append("Cấu hình có lỗi tương thích mức block nên chưa thể duyệt.")

    return BuildArtifact(
        build_id=build_id,
        build_session_id=build_session_id,
        intent_snapshot=intent,
        catalog_version=catalog.snapshot_version,
        rules_version=compatibility_report.rules_version,
        total_price_vnd=total_price,
        budget_max_vnd=intent.budget_max,
        budget_gap_vnd=budget_gap,
        budget_status=budget_status,
        status=status,
        can_approve=can_approve,
        items=items,
        compatibility_report=compatibility_report,
        performance_profile=performance_profile,
        optimizer_trace=optimizer_trace,
        explanations_vi=_build_explanations(
            intent,
            total_price,
            budget_status,
            catalog,
            optimizer_notes,
        ),
        warnings_vi=warnings,
        mock_cart_payload=MockCartPayload(
            items=[{"sku": item.sku, "url": item.url} for item in selected.values()]
        ),
    )


def _budget_aware_improvement_pass(
    *,
    artifact: BuildArtifact,
    catalog: CatalogSnapshot,
) -> tuple[dict[BuildSlot, CatalogSku], list[str], OptimizerTrace]:
    optimizer_trace = artifact.optimizer_trace or _new_optimizer_trace(
        intent=artifact.intent_snapshot,
        max_iterations=OPTIMIZER_MAX_SWAPS,
    )
    if artifact.intent_snapshot.use_case not in OPTIMIZER_USE_CASES:
        optimizer_trace = _append_optimizer_decision(
            optimizer_trace,
            _skipped_decision(
                "Use case này chưa thuộc phạm vi optimizer tự động của Phase 5.",
            ),
        )
        return _selected_from_artifact(artifact, catalog), [], optimizer_trace
    if artifact.budget_status != BudgetStatus.WITHIN_BUDGET or not artifact.can_approve:
        optimizer_trace = _append_optimizer_decision(
            optimizer_trace,
            _skipped_decision(
                "Optimizer không chạy vì build cơ sở chưa qua budget hoặc approval gate.",
            ),
        )
        return _selected_from_artifact(artifact, catalog), [], optimizer_trace
    if artifact.budget_max_vnd is None:
        optimizer_trace = _append_optimizer_decision(
            optimizer_trace,
            _skipped_decision("Optimizer cần budget_max để chứng minh phương án nằm trong ngân sách."),
        )
        return _selected_from_artifact(artifact, catalog), [], optimizer_trace

    from pc_build_copilot.build_alternatives import generate_build_alternatives

    current_artifact = artifact
    optimizer_notes: list[str] = []
    applied_kinds: set[BuildAlternativeKind] = set()
    priority_overrides = priority_overrides_for_intent(artifact.intent_snapshot)

    for iteration in range(1, OPTIMIZER_MAX_SWAPS + 1):
        response = generate_build_alternatives(base_artifact=current_artifact, catalog=catalog)
        selected_alternative, decisions = _select_optimizer_alternative(
            artifact=current_artifact,
            alternatives=response.alternatives,
            applied_kinds=applied_kinds,
            priority_overrides=priority_overrides,
            iteration=iteration,
        )
        optimizer_trace = _append_optimizer_decisions(optimizer_trace, decisions)
        if selected_alternative is None:
            if not decisions:
                optimizer_trace = _append_optimizer_decision(
                    optimizer_trace,
                    _skipped_decision(
                        "Không còn biến thể hợp lệ để optimizer xem xét.",
                        iteration=iteration,
                    ),
                )
            break

        applied_kinds.add(selected_alternative.kind)
        optimizer_notes.extend(_optimizer_notes_for_alternative(selected_alternative))
        current_artifact = _build_artifact_from_selected(
            build_id=artifact.build_id,
            build_session_id=artifact.build_session_id,
            intent=artifact.intent_snapshot,
            catalog=catalog,
            selected=_selected_from_build_items(selected_alternative.items, catalog),
            optimizer_notes=optimizer_notes,
            optimizer_trace=optimizer_trace,
        )

    if not optimizer_notes:
        return _selected_from_artifact(artifact, catalog), [], optimizer_trace
    return _selected_from_artifact(current_artifact, catalog), optimizer_notes, optimizer_trace


def _select_optimizer_alternative(
    *,
    artifact: BuildArtifact,
    alternatives: list[BuildAlternative],
    applied_kinds: set[BuildAlternativeKind],
    priority_overrides: list[str],
    iteration: int,
) -> tuple[BuildAlternative | None, list[OptimizerIterationDecision]]:
    decisions: list[OptimizerIterationDecision] = []
    for alternative in alternatives:
        if alternative.kind in applied_kinds:
            decisions.append(
                _optimizer_decision(
                    iteration=iteration,
                    alternative=alternative,
                    decision="rejected",
                    reason_vi="Đã áp dụng loại biến thể này trong vòng trước nên bỏ qua để tránh lặp.",
                )
            )
            continue
        if not _is_basic_optimizer_candidate(alternative):
            decisions.append(
                _optimizer_decision(
                    iteration=iteration,
                    alternative=alternative,
                    decision="rejected",
                    reason_vi="Biến thể bị loại vì không đạt budget hoặc approval gate.",
                )
            )
            continue
        if artifact.intent_snapshot.use_case == UseCase.GAMING:
            if _needs_gaming_optimizer(artifact) and _is_benchmark_preserving_gaming_candidate(alternative):
                decisions.append(
                    _optimizer_decision(
                        iteration=iteration,
                        alternative=alternative,
                        decision="accepted",
                        reason_vi="Chọn vì gaming build đang dưới target và biến thể giữ được benchmark evidence.",
                    )
                )
                return alternative, decisions
            decisions.append(
                _optimizer_decision(
                    iteration=iteration,
                    alternative=alternative,
                    decision="rejected",
                    reason_vi="Gaming auto-swap bị chặn vì chưa có PERF_BELOW_TARGET hoặc chưa đủ benchmark evidence.",
                )
            )
            continue
        if alternative.ranking.priority == "recommended":
            decisions.append(
                _optimizer_decision(
                    iteration=iteration,
                    alternative=alternative,
                    decision="accepted",
                    reason_vi="Chọn biến thể recommended trong budget cho use case hiện tại.",
                )
            )
            return alternative, decisions
        if _matches_priority_override(alternative, priority_overrides):
            decisions.append(
                _optimizer_decision(
                    iteration=iteration,
                    alternative=alternative,
                    decision="accepted",
                    reason_vi="Chọn vì khớp priority override từ intent và vẫn đạt các gate deterministic.",
                )
            )
            return alternative, decisions
        decisions.append(
            _optimizer_decision(
                iteration=iteration,
                alternative=alternative,
                decision="rejected",
                reason_vi="Biến thể hợp lệ nhưng chưa đủ ưu tiên để auto-apply.",
            )
        )
    return None, decisions


def _is_basic_optimizer_candidate(alternative: BuildAlternative) -> bool:
    return (
        alternative.can_approve
        and alternative.budget_status == BudgetStatus.WITHIN_BUDGET
    )


def _is_benchmark_preserving_gaming_candidate(alternative: BuildAlternative) -> bool:
    return (
        alternative.kind == BuildAlternativeKind.NVIDIA_GPU
        and alternative.ranking.priority in {"recommended", "good_fit"}
        and alternative.ranking.score >= GAMING_OPTIMIZER_MIN_SCORE
        and _has_benchmark_evidence(alternative)
    )


def _has_benchmark_evidence(alternative: BuildAlternative) -> bool:
    return any(
        evidence.source == "benchmark"
        for evidence in alternative.performance_profile.evidence
    )


def _needs_gaming_optimizer(artifact: BuildArtifact) -> bool:
    return any(
        "PERF_BELOW_TARGET" in warning
        for warning in artifact.performance_profile.warnings_vi
    )


def _optimizer_notes_for_alternative(selected_alternative: BuildAlternative) -> list[str]:
    return [
        (
            f"Optimizer đã thử các biến thể trong ngân sách và chọn {selected_alternative.label_vi} "
            f"vì đạt ưu tiên {selected_alternative.ranking.score}/100."
        ),
        *selected_alternative.ranking.reasons_vi[:2],
    ]


def _matches_priority_override(
    alternative: BuildAlternative,
    priority_overrides: list[str],
) -> bool:
    if alternative.ranking.priority not in {"recommended", "good_fit"}:
        return False
    if "gpu" in priority_overrides and alternative.kind == BuildAlternativeKind.NVIDIA_GPU:
        return True
    if "quiet" in priority_overrides and alternative.kind == BuildAlternativeKind.PSU_HEADROOM:
        return True
    return False


def _new_optimizer_trace(
    *,
    intent: BuildIntent,
    max_iterations: int,
) -> OptimizerTrace:
    overrides = priority_overrides_for_intent(intent)
    return OptimizerTrace(
        max_iterations=max_iterations,
        priority_overrides=priority_labels_vi(overrides),
        budget_allocation=build_budget_allocation(intent),
    )


def _append_optimizer_decisions(
    optimizer_trace: OptimizerTrace,
    decisions: list[OptimizerIterationDecision],
) -> OptimizerTrace:
    updated = optimizer_trace
    for decision in decisions:
        updated = _append_optimizer_decision(updated, decision)
    return updated


def _append_optimizer_decision(
    optimizer_trace: OptimizerTrace,
    decision: OptimizerIterationDecision,
) -> OptimizerTrace:
    iterations = [*optimizer_trace.iterations, decision]
    return optimizer_trace.model_copy(
        update={
            "iterations": iterations,
            "applied_iteration_count": sum(1 for item in iterations if item.decision == "accepted"),
            "rejected_iteration_count": sum(1 for item in iterations if item.decision == "rejected"),
        }
    )


def _optimizer_decision(
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


def _skipped_decision(reason_vi: str, iteration: int = 0) -> OptimizerIterationDecision:
    return OptimizerIterationDecision(
        iteration=iteration,
        decision="skipped",
        reason_vi=reason_vi,
    )


def _selected_from_artifact(
    artifact: BuildArtifact,
    catalog: CatalogSnapshot,
) -> dict[BuildSlot, CatalogSku]:
    return _selected_from_build_items(artifact.items, catalog)


def _selected_from_build_items(
    build_items: Iterable[BuildItem],
    catalog: CatalogSnapshot,
) -> dict[BuildSlot, CatalogSku]:
    catalog_by_sku = {item.sku: item for item in catalog.items}
    selected = {}
    for item in build_items:
        catalog_item = catalog_by_sku.get(item.sku)
        if catalog_item is not None:
            selected[item.slot] = catalog_item
    return selected


def _select_skus(
    intent: BuildIntent, catalog_items: Iterable[CatalogSku]
) -> dict[BuildSlot, CatalogSku]:
    by_category: dict[ComponentCategory, list[CatalogSku]] = {}
    for item in catalog_items:
        if item.stock_quantity <= 0:
            continue
        by_category.setdefault(item.category, []).append(item)

    selected: dict[BuildSlot, CatalogSku] = {}
    for slot in REQUIRED_BASE_SLOTS:
        selected[slot] = _cheapest(by_category.get(_category_for_slot(slot), []), slot)

    if _requires_discrete_gpu(intent, selected.get(BuildSlot.CPU)):
        selected[BuildSlot.VGA] = _cheapest(by_category.get(ComponentCategory.VGA, []), BuildSlot.VGA)

    return selected


def _cheapest(items: list[CatalogSku], slot: BuildSlot) -> CatalogSku:
    if not items:
        raise ValueError(f"Catalog snapshot has no in-stock candidate for {slot.value}.")
    return min(items, key=lambda item: (item.price_vnd, item.sku))


def _category_for_slot(slot: BuildSlot) -> ComponentCategory:
    return ComponentCategory(slot.value)


def _requires_discrete_gpu(intent: BuildIntent, cpu: CatalogSku | None) -> bool:
    if intent.use_case in {UseCase.GAMING, UseCase.CREATOR, UseCase.AI, UseCase.STREAMING}:
        return True
    if cpu and cpu.specs.get("integrated_graphics") is False:
        return True
    return False


def _budget_status(total_price: int, budget_max: int | None) -> tuple[BudgetStatus, int]:
    if budget_max is None:
        return BudgetStatus.UNKNOWN_BUDGET, 0
    if total_price > budget_max:
        return BudgetStatus.OVER_BUDGET, total_price - budget_max
    return BudgetStatus.WITHIN_BUDGET, 0


def _build_status(compat_can_approve: bool, budget_status: BudgetStatus) -> BuildStatus:
    if not compat_can_approve:
        return BuildStatus.BLOCKED
    if budget_status == BudgetStatus.OVER_BUDGET:
        return BuildStatus.OVER_BUDGET
    return BuildStatus.GENERATED


def _build_explanations(
    intent: BuildIntent,
    total_price: int,
    budget_status: BudgetStatus,
    catalog: CatalogSnapshot,
    optimizer_notes: list[str],
) -> list[str]:
    use_case = _use_case_label(intent.use_case)
    explanation = [
        (
            f"Cấu hình được tạo từ catalog snapshot {catalog.snapshot_version} "
            f"cho nhu cầu {use_case}."
        ),
        (
            "Các linh kiện đều là SKU trong catalog cục bộ, có link sản phẩm và "
            "giá snapshot để kiểm tra lại."
        ),
        (
            "Tương thích được kiểm tra bằng rule engine trước khi cho phép duyệt build."
        ),
    ]
    if budget_status == BudgetStatus.WITHIN_BUDGET:
        explanation.append(f"Tổng giá snapshot là {_format_vnd(total_price)}, nằm trong ngân sách.")
        explanation.extend(optimizer_notes)
    if budget_status == BudgetStatus.OVER_BUDGET:
        explanation.append(
            "Snapshot hiện tại không có phương án rẻ hơn đủ slot, nên hệ thống trả về "
            "khoảng vượt ngân sách thay vì bịa linh kiện ngoài catalog."
        )
    return explanation


def _budget_warnings(
    total_price: int, budget_max: int | None, budget_gap: int
) -> list[str]:
    if budget_max is None:
        return ["Chưa có budget_max nên build chưa thể chứng minh nằm trong ngân sách."]
    if budget_gap > 0:
        return [
            (
                f"Build vượt ngân sách {_format_vnd(budget_max)} "
                f"{_format_vnd(budget_gap)} theo giá snapshot."
            ),
            "Giá có thể thay đổi; kiểm tra lại link Phong Vu trước khi mua.",
        ]
    return ["Giá có thể thay đổi; kiểm tra lại link Phong Vu trước khi mua."]


def _item_explanation(slot: BuildSlot, item: CatalogSku, intent: BuildIntent) -> str:
    if slot == BuildSlot.VGA:
        if intent.use_case in {UseCase.OFFICE, UseCase.STUDENT}:
            return "GPU được chọn để xuất hình vì CPU trong snapshot không có iGPU; không phải cam kết tăng FPS."
        return "GPU được chọn để ưu tiên workload gaming/creator; FPS chỉ hiển thị khi có benchmark matrix khớp."
    if slot == BuildSlot.PSU:
        return "PSU được chọn vì rule engine cần công suất và đầu cấp nguồn đủ cho cấu hình."
    if slot == BuildSlot.CASE:
        return "Case được chọn vì có dữ liệu clearance để kiểm tra chiều dài GPU."
    if slot == BuildSlot.RAM:
        return "RAM được chọn theo chuẩn bộ nhớ trong snapshot và kiểm tra với mainboard."
    if slot == BuildSlot.STORAGE:
        return "SSD NVMe được chọn làm ổ boot tối thiểu cho trải nghiệm mượt hơn."
    if slot == BuildSlot.CPU:
        return f"CPU được chọn làm nền tảng cho nhu cầu {_use_case_label(intent.use_case)}."
    if slot == BuildSlot.MAINBOARD:
        return "Mainboard được chọn để khớp socket CPU và chuẩn RAM."
    return "Linh kiện được chọn từ catalog snapshot hiện tại."


def _use_case_label(use_case: UseCase) -> str:
    labels = {
        UseCase.GAMING: "gaming",
        UseCase.CREATOR: "đồ họa",
        UseCase.OFFICE: "văn phòng",
        UseCase.STUDENT: "học tập",
        UseCase.AI: "AI/local LLM",
        UseCase.STREAMING: "streaming",
        UseCase.COMPACT: "compact",
        UseCase.UNKNOWN: "chưa rõ",
    }
    return labels[use_case]


def _format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " VND"

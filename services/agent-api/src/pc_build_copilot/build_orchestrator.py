from __future__ import annotations

import operator
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from pc_build_copilot.build_generator import generate_build_artifact
from pc_build_copilot.build_models import (
    BuildArtifact,
    BuildOrchestrationStep,
    OrchestrationAgent,
    OrchestrationStepStatus,
)
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.models import BuildIntent


class BuildOrchestrationState(TypedDict):
    build_session_id: str
    intent: BuildIntent
    catalog: CatalogSnapshot
    candidate_sku_count: NotRequired[int]
    in_stock_sku_count: NotRequired[int]
    artifact: NotRequired[BuildArtifact]
    steps: Annotated[list[BuildOrchestrationStep], operator.add]


def generate_build_with_orchestration(
    *,
    build_session_id: str,
    intent: BuildIntent,
    catalog: CatalogSnapshot,
) -> BuildArtifact:
    state = _GRAPH.invoke(
        {
            "build_session_id": build_session_id,
            "intent": intent,
            "catalog": catalog,
            "steps": [],
        }
    )
    artifact = state["artifact"]
    return artifact.model_copy(update={"orchestration_trace": state["steps"]})


def _intent_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    intent = state["intent"]
    return {
        "steps": [
            _step(
                OrchestrationAgent.INTENT,
                "Intent Agent nhận nhu cầu đã xác nhận và chuẩn hóa thành schema trước khi gọi catalog.",
                inputs={
                    "build_session_id": state["build_session_id"],
                    "raw_text": intent.raw_text,
                },
                outputs={
                    "use_case": intent.use_case.value,
                    "budget_max_vnd": intent.budget_max,
                    "target_game_count": len(intent.target_games),
                    "target_app_count": len(intent.target_apps),
                    "performance_target_count": len(intent.performance_targets),
                    "mentioned_component_count": len(intent.mentioned_components),
                },
                tool_calls=["intent_parser.parse_intent", "intent_schema.validate"],
                model_version="intent-schema-confirmed-v1",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _catalog_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    in_stock = sum(1 for item in state["catalog"].items if item.stock_quantity > 0)
    return {
        "candidate_sku_count": len(state["catalog"].items),
        "in_stock_sku_count": in_stock,
        "steps": [
            _step(
                OrchestrationAgent.CATALOG,
                "Catalog Agent dùng snapshot cục bộ và chỉ cho phép SKU Phong Vu có trong dữ liệu.",
                outputs={
                    "catalog_version": state["catalog"].snapshot_version,
                    "candidate_sku_count": len(state["catalog"].items),
                    "in_stock_sku_count": in_stock,
                },
                tool_calls=["catalog_snapshot.read", "catalog_stock.filter"],
                model_version=f"catalog-snapshot:{state['catalog'].snapshot_version}",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _optimizer_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    artifact = generate_build_artifact(
        build_session_id=state["build_session_id"],
        intent=state["intent"],
        catalog=state["catalog"],
    )
    optimizer_trace = artifact.optimizer_trace
    return {
        "artifact": artifact,
        "steps": [
            _step(
                OrchestrationAgent.OPTIMIZER,
                (
                    "Optimizer Agent dùng chiến lược ngân sách theo use case, đọc priority override "
                    "và ghi lại các quyết định vòng lặp."
                ),
                inputs={
                    "budget_max_vnd": state["intent"].budget_max,
                    "candidate_sku_count": state.get("candidate_sku_count"),
                    "in_stock_sku_count": state.get("in_stock_sku_count"),
                },
                outputs={
                    "build_id": artifact.build_id,
                    "selected_sku_count": len(artifact.items),
                    "total_price_vnd": artifact.total_price_vnd,
                    "budget_status": artifact.budget_status.value,
                    "optimizer_note_count": sum(
                        1 for explanation in artifact.explanations_vi if "Optimizer" in explanation
                    ),
                    "max_iterations": optimizer_trace.max_iterations if optimizer_trace else 0,
                    "accepted_iterations": (
                        optimizer_trace.applied_iteration_count if optimizer_trace else 0
                    ),
                    "rejected_candidates": (
                        optimizer_trace.rejected_iteration_count if optimizer_trace else 0
                    ),
                    "priority_override_count": (
                        len(optimizer_trace.priority_overrides) if optimizer_trace else 0
                    ),
                },
                tool_calls=[
                    "optimizer_policy.build_budget_allocation",
                    "build_generator.generate_build_artifact",
                    "build_alternatives.generate_build_alternatives",
                ],
                model_version="config-driven-optimizer-loop-v1",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _compatibility_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    artifact = _artifact(state)
    report = artifact.compatibility_report
    status = (
        OrchestrationStepStatus.COMPLETED
        if report.can_approve
        else OrchestrationStepStatus.BLOCKED
    )
    return {
        "steps": [
            _step(
                OrchestrationAgent.COMPATIBILITY,
                "Compatibility Agent dùng rule engine deterministic để kiểm tra socket, RAM, PSU và clearance.",
                status=status,
                inputs={
                    "build_id": artifact.build_id,
                    "selected_sku_count": len(artifact.items),
                },
                outputs={
                    "rules_version": report.rules_version,
                    "compatibility_status": report.status.value,
                    "max_severity": report.max_severity.value,
                    "can_approve": report.can_approve,
                },
                tool_calls=["compatibility_rules.validate_build_compatibility"],
                model_version=f"rules:{report.rules_version}",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _performance_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    artifact = _artifact(state)
    profile = artifact.performance_profile
    return {
        "steps": [
            _step(
                OrchestrationAgent.PERFORMANCE,
                "Performance Agent tạo workload fit từ catalog facts và benchmark matrix khi khớp, không bịa FPS.",
                inputs={
                    "use_case": profile.use_case,
                    "selected_sku_count": len(artifact.items),
                },
                outputs={
                    "fit_level": profile.fit_level.value,
                    "confidence": profile.confidence.value,
                    "evidence_count": len(profile.evidence),
                    "balance_score": profile.balance.score if profile.balance else None,
                },
                tool_calls=["performance_profile.generate_performance_profile"],
                model_version="benchmark-aware-performance-fit-v1",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _explainer_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    artifact = _artifact(state)
    return {
        "steps": [
            _step(
                OrchestrationAgent.EXPLAINER,
                "Explainer Agent chỉ diễn giải từ build artifact, catalog, budget và rule report đã có.",
                inputs={
                    "build_id": artifact.build_id,
                    "warning_count": len(artifact.warnings_vi),
                },
                outputs={
                    "explanation_count": len(artifact.explanations_vi),
                    "item_explanation_count": len(artifact.items),
                },
                tool_calls=["artifact_explanation.render_vi"],
                model_version="deterministic-explainer-v1",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _commerce_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    artifact = _artifact(state)
    return {
        "steps": [
            _step(
                OrchestrationAgent.COMMERCE,
                "Commerce Agent chuẩn bị trạng thái mua hàng mock bằng link SKU Phong Vu, không tự checkout.",
                inputs={
                    "build_id": artifact.build_id,
                    "can_approve": artifact.can_approve,
                    "selected_sku_count": len(artifact.items),
                    "recommended_addon_count": len(artifact.recommended_addons),
                },
                outputs={
                    "provider": artifact.mock_cart_payload.provider,
                    "mock_cart_link_count": len(artifact.mock_cart_payload.items),
                    "total_price_vnd": artifact.total_price_vnd,
                    "ready_for_approval": artifact.can_approve,
                    "real_checkout_enabled": False,
                },
                tool_calls=["commerce.mock_cart_link_list.prepare"],
                model_version="mock-commerce-agent-v1",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _validator_agent(state: BuildOrchestrationState) -> dict[str, object]:
    started_at = datetime.now(UTC)
    start = perf_counter()
    artifact = _artifact(state)
    status = (
        OrchestrationStepStatus.COMPLETED
        if artifact.can_approve
        else OrchestrationStepStatus.BLOCKED
    )
    return {
        "steps": [
            _step(
                OrchestrationAgent.VALIDATOR,
                "Validator Agent là gate cuối cho trạng thái build và quyền duyệt.",
                status=status,
                inputs={
                    "build_id": artifact.build_id,
                    "compatibility_can_approve": artifact.compatibility_report.can_approve,
                    "budget_status": artifact.budget_status.value,
                },
                outputs={
                    "build_status": artifact.status.value,
                    "can_approve": artifact.can_approve,
                },
                tool_calls=["approval_gate.evaluate"],
                model_version=f"validator:{artifact.rules_version}",
                started_at=started_at,
                latency_ms=_elapsed_ms(start),
            )
        ],
    }


def _step(
    agent: OrchestrationAgent,
    summary_vi: str,
    *,
    status: OrchestrationStepStatus = OrchestrationStepStatus.COMPLETED,
    inputs: dict[str, str | int | bool | None] | None = None,
    outputs: dict[str, str | int | bool | None] | None = None,
    tool_calls: list[str] | None = None,
    latency_ms: int = 0,
    model_version: str = "deterministic-local-v1",
    started_at: datetime | None = None,
) -> BuildOrchestrationStep:
    completed_at = datetime.now(UTC)
    return BuildOrchestrationStep(
        agent=agent,
        status=status,
        summary_vi=summary_vi,
        inputs=inputs or {},
        outputs=outputs or {},
        tool_calls=tool_calls or [],
        latency_ms=latency_ms,
        model_version=model_version,
        started_at=started_at or completed_at,
        completed_at=completed_at,
    )


def _artifact(state: BuildOrchestrationState) -> BuildArtifact:
    artifact = state.get("artifact")
    if artifact is None:
        raise RuntimeError("Build orchestration artifact is missing.")
    return artifact


def _elapsed_ms(start: float) -> int:
    return max(0, round((perf_counter() - start) * 1000))


def _build_graph():
    graph = StateGraph(BuildOrchestrationState)
    graph.add_node("intent_agent", _intent_agent)
    graph.add_node("catalog_agent", _catalog_agent)
    graph.add_node("optimizer_agent", _optimizer_agent)
    graph.add_node("compatibility_agent", _compatibility_agent)
    graph.add_node("performance_agent", _performance_agent)
    graph.add_node("explainer_agent", _explainer_agent)
    graph.add_node("commerce_agent", _commerce_agent)
    graph.add_node("validator_agent", _validator_agent)
    graph.add_edge(START, "intent_agent")
    graph.add_edge("intent_agent", "catalog_agent")
    graph.add_edge("catalog_agent", "optimizer_agent")
    graph.add_edge("optimizer_agent", "compatibility_agent")
    graph.add_edge("compatibility_agent", "performance_agent")
    graph.add_edge("performance_agent", "explainer_agent")
    graph.add_edge("explainer_agent", "commerce_agent")
    graph.add_edge("commerce_agent", "validator_agent")
    graph.add_edge("validator_agent", END)
    return graph.compile()


_GRAPH = _build_graph()

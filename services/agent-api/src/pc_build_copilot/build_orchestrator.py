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
    return {
        "artifact": artifact,
        "steps": [
            _step(
                OrchestrationAgent.OPTIMIZER,
                "Optimizer Agent chọn một cấu hình ứng viên bằng heuristic hiện tại.",
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
                },
                tool_calls=["build_generator.generate_build_artifact"],
                model_version="heuristic-build-generator-v1",
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
                "Performance Agent tạo workload fit định tính từ fact trong catalog, không bịa FPS.",
                inputs={
                    "use_case": profile.use_case,
                    "selected_sku_count": len(artifact.items),
                },
                outputs={
                    "fit_level": profile.fit_level.value,
                    "confidence": profile.confidence.value,
                    "evidence_count": len(profile.evidence),
                },
                tool_calls=["performance_profile.generate_performance_profile"],
                model_version="qualitative-performance-fit-v1",
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
    graph.add_node("catalog_agent", _catalog_agent)
    graph.add_node("optimizer_agent", _optimizer_agent)
    graph.add_node("compatibility_agent", _compatibility_agent)
    graph.add_node("performance_agent", _performance_agent)
    graph.add_node("explainer_agent", _explainer_agent)
    graph.add_node("validator_agent", _validator_agent)
    graph.add_edge(START, "catalog_agent")
    graph.add_edge("catalog_agent", "optimizer_agent")
    graph.add_edge("optimizer_agent", "compatibility_agent")
    graph.add_edge("compatibility_agent", "performance_agent")
    graph.add_edge("performance_agent", "explainer_agent")
    graph.add_edge("explainer_agent", "validator_agent")
    graph.add_edge("validator_agent", END)
    return graph.compile()


_GRAPH = _build_graph()

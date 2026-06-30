from datetime import UTC, datetime

from pc_build_copilot.build_orchestrator import generate_build_with_orchestration
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.models import BuildIntent, UseCase

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_orchestrator",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def test_langgraph_orchestrator_runs_agent_sequence_and_preserves_build_output() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Valorant", "LMHT"],
        performance_targets=["144Hz"],
    )

    artifact = generate_build_with_orchestration(
        build_session_id="bs_orchestrated",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.status == "generated"
    assert artifact.can_approve is True
    assert artifact.total_price_vnd == 17_190_000
    assert artifact.performance_profile.fit_level == "good"
    assert [step.agent for step in artifact.orchestration_trace] == [
        "intent",
        "catalog",
        "optimizer",
        "compatibility",
        "performance",
        "explainer",
        "commerce",
        "validator",
    ]
    assert all(step.status == "completed" for step in artifact.orchestration_trace)
    assert artifact.orchestration_trace[0].outputs["use_case"] == "gaming"
    assert artifact.orchestration_trace[1].outputs["catalog_version"] == "catalog_test_orchestrator"
    assert artifact.orchestration_trace[2].outputs["selected_sku_count"] == len(artifact.items)
    assert artifact.orchestration_trace[2].outputs["max_iterations"] == 2
    assert artifact.orchestration_trace[2].outputs["priority_override_count"] == 0
    assert artifact.orchestration_trace[-2].agent == "commerce"
    assert artifact.orchestration_trace[-2].outputs["provider"] == "mock_phongvu_link_list"
    assert artifact.orchestration_trace[-2].outputs["real_checkout_enabled"] is False
    assert artifact.orchestration_trace[-1].outputs["can_approve"] is True
    assert {item.sku for item in artifact.items}.issubset({item.sku for item in _items()})


def test_langgraph_orchestrator_exports_optimizer_loop_counts() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz, ưu tiên VGA",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1440p", "Ultra", "144Hz"],
    )

    artifact = generate_build_with_orchestration(
        build_session_id="bs_orchestrated_optimizer_loop",
        intent=intent,
        catalog=_snapshot(),
    )
    optimizer_step = artifact.orchestration_trace[2]

    assert artifact.optimizer_trace is not None
    assert artifact.optimizer_trace.applied_iteration_count == 1
    assert "ưu tiên GPU/VGA" in artifact.optimizer_trace.priority_overrides
    assert optimizer_step.agent == "optimizer"
    assert optimizer_step.outputs["accepted_iterations"] == 1
    assert optimizer_step.outputs["priority_override_count"] == 1
    assert "optimizer_policy.build_budget_allocation" in optimizer_step.tool_calls


def test_langgraph_orchestrator_exposes_intent_and_mock_commerce_agents() -> None:
    intent = BuildIntent(
        raw_text="PC creator 35 triệu dựng video, cần RAM 32GB",
        use_case=UseCase.CREATOR,
        budget_max=35_000_000,
        target_apps=["Premiere"],
        mentioned_components=["RAM 32GB"],
    )

    artifact = generate_build_with_orchestration(
        build_session_id="bs_orchestrated_complete_agent_chain",
        intent=intent,
        catalog=_snapshot(),
    )
    intent_step = artifact.orchestration_trace[0]
    commerce_step = artifact.orchestration_trace[-2]

    assert intent_step.agent == "intent"
    assert intent_step.outputs["use_case"] == "creator"
    assert intent_step.outputs["target_app_count"] == 1
    assert "intent_schema.validate" in intent_step.tool_calls
    assert commerce_step.agent == "commerce"
    assert commerce_step.outputs["mock_cart_link_count"] == len(artifact.mock_cart_payload.items)
    assert commerce_step.outputs["ready_for_approval"] == artifact.can_approve
    assert commerce_step.outputs["real_checkout_enabled"] is False


def test_langgraph_orchestrator_marks_validator_blocked_for_over_budget_build() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 8 triệu chơi Valorant",
        use_case=UseCase.GAMING,
        budget_max=8_000_000,
        target_games=["Valorant"],
    )

    artifact = generate_build_with_orchestration(
        build_session_id="bs_orchestrated_low_budget",
        intent=intent,
        catalog=_snapshot(),
    )

    commerce_step = artifact.orchestration_trace[-2]
    validator_step = artifact.orchestration_trace[-1]

    assert artifact.status == "over_budget"
    assert artifact.can_approve is False
    assert commerce_step.agent == "commerce"
    assert commerce_step.outputs["ready_for_approval"] is False
    assert validator_step.agent == "validator"
    assert validator_step.status == "blocked"
    assert validator_step.outputs["build_status"] == "over_budget"
    assert validator_step.outputs["can_approve"] is False

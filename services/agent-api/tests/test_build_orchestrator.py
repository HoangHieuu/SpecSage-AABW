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
        "catalog",
        "optimizer",
        "compatibility",
        "performance",
        "explainer",
        "validator",
    ]
    assert all(step.status == "completed" for step in artifact.orchestration_trace)
    assert artifact.orchestration_trace[0].outputs["catalog_version"] == "catalog_test_orchestrator"
    assert artifact.orchestration_trace[1].outputs["selected_sku_count"] == len(artifact.items)
    assert artifact.orchestration_trace[-1].outputs["can_approve"] is True
    assert {item.sku for item in artifact.items}.issubset({item.sku for item in _items()})


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

    validator_step = artifact.orchestration_trace[-1]

    assert artifact.status == "over_budget"
    assert artifact.can_approve is False
    assert validator_step.agent == "validator"
    assert validator_step.status == "blocked"
    assert validator_step.outputs["build_status"] == "over_budget"
    assert validator_step.outputs["can_approve"] is False

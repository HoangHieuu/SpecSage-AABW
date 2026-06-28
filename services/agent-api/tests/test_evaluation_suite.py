from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.evaluation import (
    DEFAULT_SCENARIO_PATH,
    evaluate_scenario,
    load_scenarios,
    run_evaluation_suite,
)


def test_canonical_scenarios_cover_required_count_personas_and_budgets() -> None:
    scenarios = load_scenarios(DEFAULT_SCENARIO_PATH)
    personas = {scenario.persona for scenario in scenarios}
    budget_statuses = {scenario.expected_budget_status for scenario in scenarios}

    assert len(scenarios) >= 30
    assert len({scenario.id for scenario in scenarios}) == len(scenarios)
    assert {"first_time_builder", "creator", "ai_builder", "parent", "office_buyer"} <= personas
    assert {status.value for status in budget_statuses} == {"within_budget", "over_budget"}


def test_quality_evaluation_suite_passes_against_current_catalog_snapshot() -> None:
    report = run_evaluation_suite()

    assert report.passed is True
    assert report.scenario_count == 30
    assert report.passed_count == 30
    assert report.failed_count == 0
    assert report.catalog_version == "catalog_v2026_06_27_fixture"
    assert report.rules_version == "compat_rules_v2026_06_27"
    assert all(result.rubric and result.rubric.total >= 8 for result in report.results)


def test_quality_evaluation_catches_hallucinated_sku_regression() -> None:
    scenario = load_scenarios(DEFAULT_SCENARIO_PATH)[0]
    catalog = CatalogRepository().snapshot()

    result = evaluate_scenario(
        scenario=scenario,
        catalog=catalog,
        catalog_skus=set(),
    )
    hallucination_check = next(
        check for check in result.checks if check.name == "no_hallucinated_skus"
    )

    assert result.passed is False
    assert hallucination_check.passed is False


def test_quality_evaluation_records_required_core_checks() -> None:
    scenario = load_scenarios(DEFAULT_SCENARIO_PATH)[0]
    catalog = CatalogRepository().snapshot()

    result = evaluate_scenario(
        scenario=scenario,
        catalog=catalog,
        catalog_skus={item.sku for item in catalog.items},
    )
    check_names = {check.name for check in result.checks}

    assert result.passed is True
    assert {
        "expected_budget_status",
        "compatibility_expectation",
        "required_slots",
        "no_hallucinated_skus",
        "no_numeric_fps_claims",
        "benchmark_fps_claims_source_backed",
        "explanation_rubric_minimum",
    } <= check_names

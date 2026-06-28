from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from pc_build_copilot.build_models import BuildArtifact, BudgetStatus, BuildStatus
from pc_build_copilot.build_orchestrator import generate_build_with_orchestration
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.intent_parser import parse_intent
from pc_build_copilot.models import UseCase


DEFAULT_SCENARIO_PATH = (
    Path(__file__).resolve().parents[4] / "evals" / "canonical_build_scenarios.json"
)
NUMERIC_FPS_RE = re.compile(r"\b\d{2,4}\s*fps\b", re.IGNORECASE)


class EvaluationScenario(BaseModel):
    id: str = Field(pattern=r"^T-\d{3}$")
    persona: str
    message: str
    preset: UseCase | None = None
    expected_use_case: UseCase
    expected_budget_status: BudgetStatus
    expected_status: BuildStatus
    expected_can_approve: bool
    required_slots: list[BuildSlot]
    minimum_rubric_score: int = Field(default=8, ge=0, le=9)


class EvaluationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ExplanationRubricScore(BaseModel):
    clarity: int = Field(ge=0, le=3)
    grounding: int = Field(ge=0, le=3)
    vietnamese_tone: int = Field(ge=0, le=3)
    total: int = Field(ge=0, le=9)
    notes: list[str] = Field(default_factory=list)


class ScenarioEvaluationResult(BaseModel):
    scenario_id: str
    persona: str
    passed: bool
    build_id: str | None = None
    total_price_vnd: int | None = None
    budget_status: BudgetStatus | None = None
    build_status: BuildStatus | None = None
    checks: list[EvaluationCheck] = Field(default_factory=list)
    rubric: ExplanationRubricScore | None = None


class EvaluationSuiteReport(BaseModel):
    scenario_count: int
    passed_count: int
    failed_count: int
    passed: bool
    catalog_version: str
    rules_version: str | None = None
    results: list[ScenarioEvaluationResult] = Field(default_factory=list)


def load_scenarios(path: Path = DEFAULT_SCENARIO_PATH) -> list[EvaluationScenario]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = [EvaluationScenario.model_validate(item) for item in payload]
    ids = [scenario.id for scenario in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation scenario ids must be unique.")
    if len(scenarios) < 30:
        raise ValueError("Evaluation suite must include at least 30 scenarios.")
    return scenarios


def run_evaluation_suite(
    *,
    scenarios: list[EvaluationScenario] | None = None,
    catalog: CatalogSnapshot | None = None,
) -> EvaluationSuiteReport:
    catalog = catalog or CatalogRepository().snapshot()
    scenarios = scenarios or load_scenarios()
    catalog_skus = {item.sku for item in catalog.items}
    results = [
        evaluate_scenario(
            scenario=scenario,
            catalog=catalog,
            catalog_skus=catalog_skus,
        )
        for scenario in scenarios
    ]
    passed_count = sum(1 for result in results if result.passed)
    rules_version = next(
        (
            result.checks[-1].detail
            for result in results
            if result.checks and result.checks[-1].name == "rules_version"
        ),
        None,
    )
    return EvaluationSuiteReport(
        scenario_count=len(results),
        passed_count=passed_count,
        failed_count=len(results) - passed_count,
        passed=passed_count == len(results),
        catalog_version=catalog.snapshot_version,
        rules_version=rules_version,
        results=results,
    )


def evaluate_scenario(
    *,
    scenario: EvaluationScenario,
    catalog: CatalogSnapshot,
    catalog_skus: set[str],
) -> ScenarioEvaluationResult:
    checks: list[EvaluationCheck] = []
    try:
        intent, clarification = parse_intent(scenario.message, scenario.preset)
        artifact = generate_build_with_orchestration(
            build_session_id=f"eval_{scenario.id.lower()}",
            intent=intent,
            catalog=catalog,
        )
    except Exception as exc:
        return ScenarioEvaluationResult(
            scenario_id=scenario.id,
            persona=scenario.persona,
            passed=False,
            checks=[
                EvaluationCheck(
                    name="scenario_exception",
                    passed=False,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            ],
        )

    _add_check(
        checks,
        "no_required_clarification",
        clarification.field is None,
        f"clarification_field={clarification.field}",
    )
    _add_check(
        checks,
        "expected_use_case",
        intent.use_case == scenario.expected_use_case,
        f"actual={intent.use_case.value} expected={scenario.expected_use_case.value}",
    )
    _add_check(
        checks,
        "expected_budget_status",
        artifact.budget_status == scenario.expected_budget_status,
        f"actual={artifact.budget_status.value} expected={scenario.expected_budget_status.value}",
    )
    _add_check(
        checks,
        "expected_build_status",
        artifact.status == scenario.expected_status,
        f"actual={artifact.status.value} expected={scenario.expected_status.value}",
    )
    _add_check(
        checks,
        "expected_can_approve",
        artifact.can_approve is scenario.expected_can_approve,
        f"actual={artifact.can_approve} expected={scenario.expected_can_approve}",
    )
    _add_check(
        checks,
        "budget_gate",
        _budget_gate_matches(artifact),
        _budget_gate_detail(artifact),
    )
    _add_check(
        checks,
        "compatibility_expectation",
        _compatibility_matches(scenario, artifact),
        f"can_approve={artifact.compatibility_report.can_approve}",
    )
    _add_check(
        checks,
        "required_slots",
        _required_slots_present(scenario, artifact),
        f"actual={sorted(item.slot.value for item in artifact.items)}",
    )
    _add_check(
        checks,
        "no_hallucinated_skus",
        _all_artifact_skus_are_catalog_skus(artifact, catalog_skus),
        f"catalog_sku_count={len(catalog_skus)}",
    )
    _add_check(
        checks,
        "no_numeric_fps_claims",
        not NUMERIC_FPS_RE.search(_artifact_text(artifact)),
        "checked non-benchmark artifact text for numeric FPS claims",
    )
    _add_check(
        checks,
        "benchmark_fps_claims_source_backed",
        _benchmark_fps_claims_source_backed(artifact),
        "checked benchmark FPS evidence carries source provenance",
    )

    rubric = score_explanation_rubric(artifact)
    _add_check(
        checks,
        "explanation_rubric_minimum",
        rubric.total >= scenario.minimum_rubric_score,
        f"actual={rubric.total} expected_min={scenario.minimum_rubric_score}",
    )
    _add_check(
        checks,
        "rules_version",
        True,
        artifact.rules_version,
    )

    return ScenarioEvaluationResult(
        scenario_id=scenario.id,
        persona=scenario.persona,
        passed=all(check.passed for check in checks),
        build_id=artifact.build_id,
        total_price_vnd=artifact.total_price_vnd,
        budget_status=artifact.budget_status,
        build_status=artifact.status,
        checks=checks,
        rubric=rubric,
    )


def score_explanation_rubric(artifact: BuildArtifact) -> ExplanationRubricScore:
    text = _artifact_text(artifact).casefold()
    notes: list[str] = []

    clarity = 0
    if len(artifact.explanations_vi) >= 3:
        clarity += 1
    if artifact.total_price_vnd > 0 and artifact.items:
        clarity += 1
    if artifact.status.value in text or "ngân sách" in text:
        clarity += 1
    if clarity < 3:
        notes.append("Explanation clarity could be stronger.")

    grounding = 0
    if artifact.catalog_version in text or "catalog" in text:
        grounding += 1
    if artifact.rules_version in text or "rule" in text or "tương thích" in text:
        grounding += 1
    if all(item.url.startswith("https://phongvu.vn/") for item in artifact.items):
        grounding += 1
    if grounding < 3:
        notes.append("Grounding should cite catalog/rules/SKU links more clearly.")

    vietnamese_tone = 0
    if any(marker in text for marker in ["cấu hình", "linh kiện", "ngân sách"]):
        vietnamese_tone += 1
    if any(char in text for char in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệóòỏõọốồổỗộớờởỡợúùủũụứừửữựíìỉĩịýỳỷỹỵ"):
        vietnamese_tone += 1
    if "Mock cart".casefold() not in text:
        vietnamese_tone += 1
    if vietnamese_tone < 3:
        notes.append("Vietnamese tone should be reviewed by a human.")

    return ExplanationRubricScore(
        clarity=clarity,
        grounding=grounding,
        vietnamese_tone=vietnamese_tone,
        total=clarity + grounding + vietnamese_tone,
        notes=notes,
    )


def _add_check(
    checks: list[EvaluationCheck],
    name: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(EvaluationCheck(name=name, passed=passed, detail=detail))


def _budget_gate_matches(artifact: BuildArtifact) -> bool:
    if artifact.budget_status == BudgetStatus.WITHIN_BUDGET:
        return artifact.budget_max_vnd is not None and artifact.total_price_vnd <= artifact.budget_max_vnd
    if artifact.budget_status == BudgetStatus.OVER_BUDGET:
        return artifact.budget_max_vnd is not None and artifact.budget_gap_vnd > 0
    return artifact.budget_max_vnd is None


def _budget_gate_detail(artifact: BuildArtifact) -> str:
    return (
        f"status={artifact.budget_status.value} total={artifact.total_price_vnd} "
        f"budget_max={artifact.budget_max_vnd} gap={artifact.budget_gap_vnd}"
    )


def _compatibility_matches(
    scenario: EvaluationScenario,
    artifact: BuildArtifact,
) -> bool:
    if scenario.expected_can_approve:
        return artifact.compatibility_report.can_approve
    return (
        artifact.budget_status == BudgetStatus.OVER_BUDGET
        or not artifact.compatibility_report.can_approve
    )


def _required_slots_present(
    scenario: EvaluationScenario,
    artifact: BuildArtifact,
) -> bool:
    slots = {item.slot for item in artifact.items}
    return set(scenario.required_slots).issubset(slots)


def _all_artifact_skus_are_catalog_skus(
    artifact: BuildArtifact,
    catalog_skus: set[str],
) -> bool:
    item_skus = {item.sku for item in artifact.items}
    cart_skus = {item["sku"] for item in artifact.mock_cart_payload.items}
    compatibility_skus = set(artifact.compatibility_report.selected_skus.values())
    return item_skus <= catalog_skus and cart_skus <= catalog_skus and compatibility_skus <= catalog_skus


def _artifact_text(artifact: BuildArtifact) -> str:
    return " ".join(
        [
            *artifact.explanations_vi,
            *artifact.warnings_vi,
            artifact.performance_profile.summary_vi,
            *artifact.performance_profile.fit_notes_vi,
            *artifact.performance_profile.bottleneck_notes_vi,
            *artifact.performance_profile.warnings_vi,
            *(item.explanation_vi for item in artifact.items),
        ]
    )


def _benchmark_fps_claims_source_backed(artifact: BuildArtifact) -> bool:
    fps_evidence = [
        evidence
        for evidence in artifact.performance_profile.evidence
        if NUMERIC_FPS_RE.search(evidence.value)
    ]
    return all(
        evidence.source == "benchmark" and evidence.source_label and evidence.source_url
        for evidence in fps_evidence
    )

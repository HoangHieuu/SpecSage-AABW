from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.store import SessionStore
from pc_build_copilot.upgrade_models import ExistingSystemOverrides, UpgradePlanRequest
from pc_build_copilot.upgrade_planner import create_gpu_upgrade_plan, parse_existing_system


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CATALOG = ROOT / "catalog" / "catalog_snapshot.json"
SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _active_catalog_snapshot() -> CatalogSnapshot:
    return CatalogSnapshot.model_validate_json(
        Path(ACTIVE_CATALOG).read_text(encoding="utf-8")
    )


def _client(snapshot: CatalogSnapshot | None = None) -> TestClient:
    return TestClient(
        create_app(
            SessionStore(),
            CatalogRepository(snapshot=snapshot or _active_catalog_snapshot()),
        )
    )


def test_parse_existing_system_marks_missing_fields_unknown() -> None:
    spec = parse_existing_system("PC cũ RTX 3060, RAM 16GB, muốn nâng GPU")

    assert spec.gpu_name == "RTX-3060"
    assert spec.gpu_tier_score is not None
    assert spec.ram_gb == 16
    assert "cpu" in spec.unknown_fields
    assert "psu" in spec.unknown_fields
    assert "case" in spec.unknown_fields


def test_parse_existing_system_does_not_treat_gpu_vram_as_system_ram() -> None:
    spec = parse_existing_system(
        "Máy i5-12400F, RTX 3060 12GB GDDR6, RAM 2x8GB DDR4, nguồn 650W"
    )

    assert spec.gpu_name == "RTX-3060"
    assert spec.ram_gb == 16


def test_gpu_upgrade_plan_recommends_real_catalog_gpu_and_reuses_psu_case() -> None:
    payload = UpgradePlanRequest(
        current_pc=(
            "Máy hiện tại i5-12400F, B660 DDR4, RAM 16GB, RTX 3060, "
            "nguồn 650W 2x8-pin, case hỗ trợ GPU 330mm, SSD 1TB"
        ),
        upgrade_budget_max_vnd=10_000_000,
    )

    plan = create_gpu_upgrade_plan(
        payload=payload,
        catalog=_active_catalog_snapshot(),
    )
    recommendation = plan.recommendations[0]

    assert recommendation.sku == "231101406"
    assert recommendation.name.startswith("VGA MSI GeForce RTX 4060")
    assert recommendation.price_vnd == 8_990_000
    assert recommendation.compatibility_status == "pass"
    assert {check.code for check in recommendation.checks} == {
        "UPGRADE_PSU_WATTAGE_OK",
        "UPGRADE_GPU_POWER_CONNECTOR_OK",
        "UPGRADE_GPU_CASE_CLEARANCE_OK",
    }
    assert plan.total_upgrade_cost_vnd == recommendation.price_vnd
    assert any(
        item.slot == "vga" and item.decision == "replace"
        for item in plan.reuse_decisions
    )
    assert any(
        item.slot == "psu" and item.decision == "reuse"
        for item in plan.reuse_decisions
    )
    assert any(
        item.slot == "case" and item.decision == "reuse"
        for item in plan.reuse_decisions
    )
    assert {recommendation.sku}.issubset({item.sku for item in _active_catalog_snapshot().items})


def test_gpu_upgrade_plan_blocks_when_existing_psu_is_too_small() -> None:
    payload = UpgradePlanRequest(
        current_pc=(
            "Máy hiện tại i5-12400F, B660 DDR4, RAM 16GB, RTX 3060, "
            "nguồn 300W 1x8-pin, case hỗ trợ GPU 330mm, SSD 1TB"
        ),
        upgrade_budget_max_vnd=10_000_000,
    )

    plan = create_gpu_upgrade_plan(
        payload=payload,
        catalog=_active_catalog_snapshot(),
    )
    recommendation = plan.recommendations[0]

    assert recommendation.compatibility_status == "block"
    assert any(check.code == "UPGRADE_PSU_WATTAGE_TOO_LOW" for check in recommendation.checks)
    assert any(
        item.slot == "psu" and item.decision == "replace"
        for item in plan.reuse_decisions
    )
    assert any("Xử lý các mục bị block" in item for item in plan.next_steps_vi)


def test_gpu_upgrade_plan_accepts_partial_specs_with_conservative_warnings() -> None:
    payload = UpgradePlanRequest(
        current_pc="PC cũ RTX 3060, RAM 16GB, muốn nâng GPU",
        upgrade_budget_max_vnd=10_000_000,
    )

    plan = create_gpu_upgrade_plan(
        payload=payload,
        catalog=_active_catalog_snapshot(),
    )
    recommendation = plan.recommendations[0]

    assert recommendation.sku == "231101406"
    assert recommendation.compatibility_status == "warn"
    assert any(check.code == "UPGRADE_PSU_INPUT_UNKNOWN" for check in recommendation.checks)
    assert any(check.code == "UPGRADE_CASE_CLEARANCE_UNKNOWN" for check in recommendation.checks)
    assert "psu" in plan.existing_system.unknown_fields
    assert "case" in plan.existing_system.unknown_fields
    assert any("thận trọng" in warning for warning in plan.warnings_vi)


def test_gpu_upgrade_plan_uses_confirmed_existing_system_for_checks() -> None:
    payload = UpgradePlanRequest(
        current_pc="PC cũ RTX 3060, RAM 16GB, muốn nâng GPU",
        upgrade_budget_max_vnd=10_000_000,
        confirmed_existing_system=ExistingSystemOverrides(
            cpu_name="i5-12400F",
            mainboard_name="b660",
            ram_gb=16,
            gpu_name="RTX 3060",
            psu_wattage_w=650,
            psu_pcie_8pin_connectors=2,
            case_gpu_clearance_mm=330,
            storage_summary="SSD 1TB",
        ),
    )

    plan = create_gpu_upgrade_plan(
        payload=payload,
        catalog=_active_catalog_snapshot(),
    )
    recommendation = plan.recommendations[0]

    assert plan.existing_system.raw_text == payload.current_pc
    assert plan.existing_system.cpu_name == "I5-12400F"
    assert plan.existing_system.mainboard_name == "B660"
    assert plan.existing_system.unknown_fields == []
    assert recommendation.compatibility_status == "pass"
    assert {check.code for check in recommendation.checks} == {
        "UPGRADE_PSU_WATTAGE_OK",
        "UPGRADE_GPU_POWER_CONNECTOR_OK",
        "UPGRADE_GPU_CASE_CLEARANCE_OK",
    }


def test_existing_system_parse_api_endpoint_returns_confirmation_summary() -> None:
    response = _client().post(
        "/upgrade-plans/existing-system/parse",
        json={
            "current_pc": (
                "Máy i5-12400F, RTX 3060 12GB GDDR6, RAM 2x8GB DDR4, nguồn 650W"
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["confirmation_required"] is True
    assert payload["existing_system"]["cpu_name"] == "I5-12400F"
    assert payload["existing_system"]["gpu_name"] == "RTX-3060"
    assert payload["existing_system"]["ram_gb"] == 16
    assert "case" in payload["existing_system"]["unknown_fields"]
    assert "12GB" not in payload["summary_vi"]


def test_gpu_upgrade_plan_api_endpoint() -> None:
    response = _client().post(
        "/upgrade-plans/gpu",
        json={
            "current_pc": (
                "Máy hiện tại i5-12400F, B660 DDR4, RAM 16GB, RTX 3060, "
                "nguồn 650W 2x8-pin, case hỗ trợ GPU 330mm, SSD 1TB"
            ),
            "upgrade_budget_max_vnd": 10_000_000,
            "target_use_case": "gaming",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog_version"] == _active_catalog_snapshot().snapshot_version
    assert payload["recommendations"][0]["sku"] == "231101406"
    assert payload["recommendations"][0]["compatibility_status"] == "pass"

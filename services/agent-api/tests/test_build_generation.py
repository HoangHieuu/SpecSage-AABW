from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.build_alternatives import (
    apply_build_alternative,
    generate_build_alternatives,
)
from pc_build_copilot.build_generator import generate_build_artifact
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.compatibility_models import BuildSlot
from pc_build_copilot.models import BuildIntent, UseCase
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot(items=None) -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_build",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=items or _items(),
    )


def _client() -> TestClient:
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=_snapshot())))


def test_generator_creates_compatible_grounded_build_under_budget() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 20 triệu chơi Valorant và LMHT",
        use_case=UseCase.GAMING,
        budget_max=20_000_000,
        target_games=["Valorant", "LMHT"],
        performance_targets=["144Hz"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_test",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.status == "generated"
    assert artifact.budget_status == "within_budget"
    assert artifact.can_approve is True
    assert artifact.total_price_vnd == 17_190_000
    assert artifact.compatibility_report.status == "approved"
    assert artifact.performance_profile.use_case == "gaming"
    assert artifact.performance_profile.fit_level == "good"
    assert artifact.performance_profile.confidence == "high"
    assert any("8GB VRAM" in fact.value for fact in artifact.performance_profile.evidence)
    assert any("144Hz" in fact.value for fact in artifact.performance_profile.evidence)
    assert artifact.catalog_version == "catalog_test_build"
    assert artifact.rules_version == artifact.compatibility_report.rules_version
    assert {item.sku for item in artifact.items}.issubset({item.sku for item in _items()})
    assert all(item.url.startswith("https://phongvu.vn/") for item in artifact.items)
    assert "fps" not in " ".join(artifact.explanations_vi).casefold()
    assert "fps" not in artifact.performance_profile.summary_vi.casefold()


def test_generator_returns_explicit_over_budget_gap_without_inventing_parts() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 8 triệu chơi Valorant",
        use_case=UseCase.GAMING,
        budget_max=8_000_000,
        target_games=["Valorant"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_low_budget",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.status == "over_budget"
    assert artifact.budget_status == "over_budget"
    assert artifact.budget_gap_vnd == 9_190_000
    assert artifact.can_approve is False
    assert any("vượt ngân sách" in warning for warning in artifact.warnings_vi)
    assert {item.sku for item in artifact.items}.issubset({item.sku for item in _items()})


def test_generator_blocks_artifact_when_compatibility_has_block_result() -> None:
    items = _items()
    bad_mainboard = next(item for item in items if item.sku == "230203929").model_copy(
        update={"specs": {**next(item for item in items if item.sku == "230203929").specs, "socket": "AM5"}}
    )
    mutated = [bad_mainboard if item.sku == bad_mainboard.sku else item for item in items]
    intent = BuildIntent(
        raw_text="PC gaming 20 triệu chơi Valorant",
        use_case=UseCase.GAMING,
        budget_max=20_000_000,
        target_games=["Valorant"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_blocked",
        intent=intent,
        catalog=_snapshot(mutated),
    )

    assert artifact.status == "blocked"
    assert artifact.can_approve is False
    assert any(
        result.rule_id == "COMPAT_SOCKET_MISMATCH"
        for result in artifact.compatibility_report.results
    )


def test_generate_endpoint_requires_confirmed_intent() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()

    response = client.post(f"/sessions/{session['build_session_id']}/generate")

    assert response.status_code == 409


def test_generate_endpoint_creates_and_stores_build_artifact() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 20 triệu chơi Valorant và LMHT",
            "confirm": True,
            "preset": "gaming",
        },
    )

    response = client.post(f"/sessions/{session['build_session_id']}/generate")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "generated"
    assert body["budget_status"] == "within_budget"
    assert body["can_approve"] is True
    assert body["total_price_vnd"] == 17_190_000
    assert len(body["items"]) == 7
    assert body["performance_profile"]["use_case"] == "gaming"
    assert body["performance_profile"]["fit_level"] == "good"
    assert [step["agent"] for step in body["orchestration_trace"]] == [
        "catalog",
        "optimizer",
        "compatibility",
        "performance",
        "explainer",
        "validator",
    ]
    assert body["orchestration_trace"][-1]["outputs"]["can_approve"] is True
    assert any(
        fact["label"] == "GPU" and "8GB VRAM" in fact["value"]
        for fact in body["performance_profile"]["evidence"]
    )
    assert all(item["url"].startswith("https://phongvu.vn/") for item in body["items"])

    stored = client.get(f"/builds/{body['build_id']}")
    assert stored.status_code == 200
    assert stored.json()["build_id"] == body["build_id"]
    session_after = client.get(f"/sessions/{session['build_session_id']}").json()
    assert session_after["state"] == "generated"


def test_generate_endpoint_returns_over_budget_artifact_for_low_budget() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 8 triệu chơi Valorant",
            "confirm": True,
            "preset": "gaming",
        },
    )

    response = client.post(f"/sessions/{session['build_session_id']}/generate")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "over_budget"
    assert body["budget_status"] == "over_budget"
    assert body["budget_gap_vnd"] == 9_190_000
    assert body["can_approve"] is False
    assert body["orchestration_trace"][-1]["agent"] == "validator"
    assert body["orchestration_trace"][-1]["status"] == "blocked"


def test_alternative_generator_returns_grounded_validated_variants() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Valorant", "LMHT"],
        performance_targets=["144Hz"],
    )
    base_artifact = generate_build_artifact(
        build_session_id="bs_alternatives",
        intent=intent,
        catalog=_snapshot(),
    )

    response = generate_build_alternatives(
        base_artifact=base_artifact,
        catalog=_snapshot(),
    )
    catalog_skus = {item.sku for item in _items()}
    kinds = {alternative.kind for alternative in response.alternatives}
    profile_text = " ".join(
        [
            alternative.summary_vi
            for alternative in response.alternatives
        ]
    ).casefold()

    assert response.build_id == base_artifact.build_id
    assert response.base_total_price_vnd == 17_190_000
    assert kinds == {"ram_upgrade", "storage_upgrade", "nvidia_gpu", "psu_headroom"}
    assert all(alternative.compatibility_report.can_approve for alternative in response.alternatives)
    assert all(alternative.price_delta_vnd > 0 for alternative in response.alternatives)
    assert all(
        {item.sku for item in alternative.items}.issubset(catalog_skus)
        for alternative in response.alternatives
    )
    assert any(
        changed.slot == BuildSlot.RAM and changed.candidate_sku == "240601032"
        for alternative in response.alternatives
        for changed in alternative.changed_slots
    )
    assert any(
        changed.slot == BuildSlot.VGA and changed.candidate_sku == "231101406"
        for alternative in response.alternatives
        for changed in alternative.changed_slots
    )
    assert "fps" not in profile_text


def test_apply_alternative_generator_returns_versioned_active_artifact() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Valorant", "LMHT"],
        performance_targets=["144Hz"],
    )
    base_artifact = generate_build_artifact(
        build_session_id="bs_apply_alternative",
        intent=intent,
        catalog=_snapshot(),
    )
    alternatives = generate_build_alternatives(
        base_artifact=base_artifact,
        catalog=_snapshot(),
    )
    ram_upgrade = next(item for item in alternatives.alternatives if item.kind == "ram_upgrade")

    applied = apply_build_alternative(
        base_artifact=base_artifact,
        variant_id=ram_upgrade.variant_id,
        catalog=_snapshot(),
    )

    assert applied is not None
    assert applied.build_id != base_artifact.build_id
    assert applied.build_version == 2
    assert applied.status == "generated"
    assert applied.can_approve is True
    assert applied.total_price_vnd == 17_890_000
    assert applied.compatibility_report.build_id == applied.build_id
    assert any(item.sku == "240601032" and item.slot == BuildSlot.RAM for item in applied.items)
    assert len(applied.mock_cart_payload.items) == len(applied.items)
    assert any("Approval" in explanation for explanation in applied.explanations_vi)


def test_alternatives_endpoint_returns_variants_for_stored_build() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    response = client.get(f"/builds/{build['build_id']}/alternatives")

    assert response.status_code == 200
    body = response.json()
    assert body["build_id"] == build["build_id"]
    assert body["base_total_price_vnd"] == build["total_price_vnd"]
    assert len(body["alternatives"]) == 4
    assert {item["kind"] for item in body["alternatives"]} == {
        "ram_upgrade",
        "storage_upgrade",
        "nvidia_gpu",
        "psu_headroom",
    }
    assert all(item["compatibility_report"]["can_approve"] for item in body["alternatives"])


def test_alternatives_endpoint_404s_for_missing_build() -> None:
    client = _client()

    response = client.get("/builds/build_missing/alternatives")

    assert response.status_code == 404


def test_apply_alternative_endpoint_creates_new_stored_build_version_and_can_approve() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()
    alternatives = client.get(f"/builds/{build['build_id']}/alternatives").json()
    ram_upgrade = next(
        item for item in alternatives["alternatives"] if item["kind"] == "ram_upgrade"
    )

    response = client.post(
        f"/builds/{build['build_id']}/alternatives/{ram_upgrade['variant_id']}/apply"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["build_id"] != build["build_id"]
    assert body["build_session_id"] == build["build_session_id"]
    assert body["build_version"] == build["build_version"] + 1
    assert body["total_price_vnd"] == ram_upgrade["total_price_vnd"]
    assert body["total_price_vnd"] == 17_890_000
    assert body["status"] == "generated"
    assert body["can_approve"] is True
    assert body["compatibility_report"]["build_id"] == body["build_id"]
    assert any(item["slot"] == "ram" and item["sku"] == "240601032" for item in body["items"])

    original = client.get(f"/builds/{build['build_id']}").json()
    stored = client.get(f"/builds/{body['build_id']}").json()
    assert original["build_version"] == 1
    assert any(item["slot"] == "ram" and item["sku"] == "210602265" for item in original["items"])
    assert stored["build_id"] == body["build_id"]

    handoff = client.post(f"/builds/{body['build_id']}/approve")
    assert handoff.status_code == 200
    assert handoff.json()["status"] == "cart_ready"
    assert handoff.json()["build_id"] == body["build_id"]
    assert handoff.json()["total_price_vnd"] == body["total_price_vnd"]


def test_apply_alternative_endpoint_404s_for_missing_variant() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    response = client.post(f"/builds/{build['build_id']}/alternatives/variant_missing/apply")

    assert response.status_code == 404
    assert response.json()["detail"] == "variant_id not found"


def test_approve_endpoint_creates_cart_ready_handoff_for_approvable_build() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 20 triệu chơi Valorant và LMHT",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    response = client.post(f"/builds/{build['build_id']}/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cart_ready"
    assert body["build_id"] == build["build_id"]
    assert body["approval"]["status"] == "approved"
    assert body["approval"]["selected_skus"]["cpu"] == "211208130"
    assert body["approval"]["catalog_version"] == "catalog_test_build"
    assert body["total_price_vnd"] == 17_190_000
    assert body["item_count"] == 7
    assert len(body["mock_cart_payload"]["items"]) == 7
    assert "Mock cart" in body["mock_cart_payload"]["disclaimer_vi"]

    session_after = client.get(f"/sessions/{session['build_session_id']}").json()
    assert session_after["state"] == "cart_ready"


def test_approve_endpoint_is_idempotent_for_same_build() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 20 triệu chơi Valorant",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    first = client.post(f"/builds/{build['build_id']}/approve").json()
    second = client.post(f"/builds/{build['build_id']}/approve").json()

    assert second["handoff_id"] == first["handoff_id"]
    assert second["approval"]["approval_id"] == first["approval"]["approval_id"]


def test_approve_endpoint_rejects_over_budget_build() -> None:
    client = _client()
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 8 triệu chơi Valorant",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    response = client.post(f"/builds/{build['build_id']}/approve")

    assert response.status_code == 409
    assert "within budget" in response.json()["detail"]
    session_after = client.get(f"/sessions/{session['build_session_id']}").json()
    assert session_after["state"] == "generated"


def test_approve_endpoint_rejects_blocked_build() -> None:
    items = _items()
    original_mainboard = next(item for item in items if item.sku == "230203929")
    bad_mainboard = original_mainboard.model_copy(
        update={"specs": {**original_mainboard.specs, "socket": "AM5"}}
    )
    mutated = [bad_mainboard if item.sku == bad_mainboard.sku else item for item in items]
    client = TestClient(
        create_app(
            SessionStore(),
            CatalogRepository(snapshot=_snapshot(mutated)),
        )
    )
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 20 triệu chơi Valorant",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    response = client.post(f"/builds/{build['build_id']}/approve")

    assert build["status"] == "blocked"
    assert response.status_code == 409


def test_creator_profile_warns_when_ram_is_below_creator_threshold() -> None:
    intent = BuildIntent(
        raw_text="PC đồ họa 35 triệu dùng Premiere và After Effects",
        use_case=UseCase.CREATOR,
        budget_max=35_000_000,
        target_apps=["Adobe Premiere Pro", "Adobe After Effects"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_creator",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.performance_profile.use_case == "creator"
    assert artifact.performance_profile.fit_level == "limited"
    assert any("RAM 16GB" in note for note in artifact.performance_profile.bottleneck_notes_vi)
    assert any("32GB" in warning for warning in artifact.performance_profile.warnings_vi)
    assert any("32GB" in warning for warning in artifact.warnings_vi)


def test_ai_profile_surfaces_vram_and_ram_limits_without_fps_claims() -> None:
    intent = BuildIntent(
        raw_text="PC AI local LLM 40 triệu, ưu tiên NVIDIA và 32GB RAM",
        use_case=UseCase.AI,
        budget_max=40_000_000,
        target_apps=["Local LLM"],
        brand_preferences=["NVIDIA"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_ai",
        intent=intent,
        catalog=_snapshot(),
    )
    profile_text = " ".join(
        [
            artifact.performance_profile.summary_vi,
            *artifact.performance_profile.fit_notes_vi,
            *artifact.performance_profile.bottleneck_notes_vi,
            *artifact.performance_profile.warnings_vi,
        ]
    ).casefold()

    assert artifact.performance_profile.use_case == "ai"
    assert artifact.performance_profile.fit_level == "adequate"
    assert "vram 8gb" in profile_text
    assert "32gb" in profile_text
    assert "fps" not in profile_text


def test_office_profile_explains_discrete_gpu_when_cpu_has_no_igpu() -> None:
    intent = BuildIntent(
        raw_text="Máy văn phòng khoảng 20 triệu, ưu tiên êm và bền",
        use_case=UseCase.OFFICE,
        budget_max=20_000_000,
        noise_preferences="quiet",
    )

    artifact = generate_build_artifact(
        build_session_id="bs_office",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.performance_profile.use_case == "office"
    assert artifact.performance_profile.fit_level == "good"
    assert any("không có iGPU" in note for note in artifact.performance_profile.fit_notes_vi)

from datetime import UTC, datetime
from pathlib import Path

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

from test_catalog_ingestion import ROOT, _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)
ACTIVE_CATALOG = ROOT / "catalog" / "catalog_snapshot.json"


def _snapshot(items=None) -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_build",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=items or _items(),
    )


def _active_catalog_snapshot() -> CatalogSnapshot:
    return CatalogSnapshot.model_validate_json(
        Path(ACTIVE_CATALOG).read_text(encoding="utf-8")
    )


def _client(snapshot: CatalogSnapshot | None = None) -> TestClient:
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=snapshot or _snapshot())))


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
    assert artifact.performance_profile.balance is not None
    assert artifact.performance_profile.balance.score >= 70
    assert artifact.performance_profile.balance.limiting_component in {
        "cpu",
        "gpu",
        "ram",
        "storage",
    }
    assert any("8GB VRAM" in fact.value for fact in artifact.performance_profile.evidence)
    assert any("144Hz" in fact.value for fact in artifact.performance_profile.evidence)
    assert artifact.catalog_version == "catalog_test_build"
    assert artifact.rules_version == artifact.compatibility_report.rules_version
    assert {item.sku for item in artifact.items}.issubset({item.sku for item in _items()})
    assert all(item.url.startswith("https://phongvu.vn/") for item in artifact.items)
    assert "fps" not in " ".join(artifact.explanations_vi).casefold()
    assert "fps" not in artifact.performance_profile.summary_vi.casefold()


def test_generator_uses_source_backed_benchmark_when_game_gpu_and_targets_match() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1440p", "Ultra", "144Hz"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_benchmark",
        intent=intent,
        catalog=_snapshot(),
        optimize=False,
    )
    benchmark_evidence = [
        fact for fact in artifact.performance_profile.evidence if fact.source == "benchmark"
    ]

    assert artifact.performance_profile.fit_level == "limited"
    assert len(benchmark_evidence) == 1
    assert benchmark_evidence[0].value == "Cyberpunk 2077 1440p Ultra native: 30-35 FPS"
    assert benchmark_evidence[0].source_label
    assert benchmark_evidence[0].source_url
    assert any("PERF_BELOW_TARGET" in warning for warning in artifact.performance_profile.warnings_vi)
    assert all("30-35 FPS" not in warning for warning in artifact.performance_profile.warnings_vi)


def test_generator_applies_benchmark_preserving_gaming_gpu_optimizer_swap() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1440p", "Ultra", "144Hz"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_rtx4060_benchmark",
        intent=intent,
        catalog=_snapshot(),
    )
    benchmark_evidence = [
        fact for fact in artifact.performance_profile.evidence if fact.source == "benchmark"
    ]

    assert artifact.total_price_vnd == 19_190_000
    assert any(item.slot == BuildSlot.VGA and item.sku == "231101406" for item in artifact.items)
    assert len(benchmark_evidence) == 1
    assert benchmark_evidence[0].value == "Cyberpunk 2077 1440p Ultra native: 43 FPS"
    assert benchmark_evidence[0].source_label == "TechSpot Cyberpunk 2077 Phantom Liberty GPU benchmark"
    assert any("Optimizer" in explanation for explanation in artifact.explanations_vi)
    assert any("PERF_BELOW_TARGET" in warning for warning in artifact.performance_profile.warnings_vi)
    assert artifact.optimizer_trace is not None
    assert artifact.optimizer_trace.max_iterations == 2
    assert artifact.optimizer_trace.applied_iteration_count == 1
    assert any(
        decision.decision == "accepted" and decision.candidate_kind == "nvidia_gpu"
        for decision in artifact.optimizer_trace.iterations
    )
    assert artifact.optimizer_trace.budget_allocation.weights["vga"] >= 40


def test_alternative_generator_prioritizes_benchmark_delta_for_gaming_gpu_swap() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1440p", "Ultra", "144Hz"],
    )
    base_artifact = generate_build_artifact(
        build_session_id="bs_gaming_benchmark_rank",
        intent=intent,
        catalog=_snapshot(),
        optimize=False,
    )

    response = generate_build_alternatives(
        base_artifact=base_artifact,
        catalog=_snapshot(),
    )
    top_alternative = response.alternatives[0]

    assert top_alternative.kind == "nvidia_gpu"
    assert top_alternative.ranking.priority == "recommended"
    assert any(
        "benchmark exact-match" in reason.casefold()
        for reason in top_alternative.ranking.reasons_vi
    )
    assert all("fps" not in reason.casefold() for reason in top_alternative.ranking.reasons_vi)


def test_optimizer_trace_records_priority_overrides_without_bypassing_gaming_gate() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Valorant 144Hz, ưu tiên VGA và im lặng",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Valorant"],
        performance_targets=["144Hz"],
        noise_preferences="quiet",
    )

    artifact = generate_build_artifact(
        build_session_id="bs_priority_trace",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.optimizer_trace is not None
    assert artifact.total_price_vnd == 17_190_000
    assert any(item.slot == BuildSlot.VGA and item.sku == "260508255" for item in artifact.items)
    assert "ưu tiên GPU/VGA" in artifact.optimizer_trace.priority_overrides
    assert "ưu tiên vận hành êm" in artifact.optimizer_trace.priority_overrides
    assert artifact.optimizer_trace.budget_allocation.weights["vga"] > 45
    assert artifact.optimizer_trace.rejected_iteration_count > 0
    assert any(
        decision.decision == "rejected"
        and "Gaming auto-swap bị chặn" in decision.reason_vi
        for decision in artifact.optimizer_trace.iterations
    )
    assert not any("Optimizer" in explanation for explanation in artifact.explanations_vi)


def test_generator_keeps_gaming_gpu_optimizer_off_without_candidate_benchmark() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Valorant 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Valorant"],
        performance_targets=["144Hz"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_gaming_no_benchmark_swap",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.total_price_vnd == 17_190_000
    assert any(item.slot == BuildSlot.VGA and item.sku == "260508255" for item in artifact.items)
    assert not any("Optimizer" in explanation for explanation in artifact.explanations_vi)
    assert all(fact.source != "benchmark" for fact in artifact.performance_profile.evidence)


def test_generator_skips_gaming_gpu_optimizer_when_benchmark_fit_is_already_enough() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1080p Ultra 60Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1080p", "Ultra", "60Hz"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_gaming_benchmark_enough",
        intent=intent,
        catalog=_snapshot(),
    )
    benchmark_evidence = [
        fact for fact in artifact.performance_profile.evidence if fact.source == "benchmark"
    ]

    assert artifact.total_price_vnd == 17_190_000
    assert any(item.slot == BuildSlot.VGA and item.sku == "260508255" for item in artifact.items)
    assert len(benchmark_evidence) == 1
    assert benchmark_evidence[0].value == "Cyberpunk 2077 1080p Ultra native: 77 FPS"
    assert not any("Optimizer" in explanation for explanation in artifact.explanations_vi)
    assert not any("PERF_BELOW_TARGET" in warning for warning in artifact.performance_profile.warnings_vi)


def test_generator_warns_when_cpu_gpu_ram_balance_is_severely_imbalanced() -> None:
    items = _items()
    weak_cpu = next(item for item in items if item.sku == "211208130").model_copy(
        update={"specs": {**next(item for item in items if item.sku == "211208130").specs, "cores": 2, "threads": 4}}
    )
    oversized_gpu = next(item for item in items if item.sku == "260508255").model_copy(
        update={"specs": {**next(item for item in items if item.sku == "260508255").specs, "chipset": "RTX 4090", "vram_gb": 24}}
    )
    mutated = [
        weak_cpu if item.sku == weak_cpu.sku else oversized_gpu if item.sku == oversized_gpu.sku else item
        for item in items
    ]
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_imbalance",
        intent=intent,
        catalog=_snapshot(mutated),
        optimize=False,
    )

    assert artifact.performance_profile.balance is not None
    assert artifact.performance_profile.balance.score < 65
    assert artifact.performance_profile.balance.limiting_component == "cpu"
    assert any("PERF_IMBALANCE" in warning for warning in artifact.performance_profile.warnings_vi)


def test_generator_warns_when_requested_monitor_exceeds_benchmark_fps() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra kèm màn hình 144Hz",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1440p", "Ultra", "144Hz"],
        mentioned_components=["monitor"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_monitor_overspec",
        intent=intent,
        catalog=_snapshot(),
    )

    assert any(
        "PERF_MONITOR_OVERSPEC" in warning
        for warning in artifact.performance_profile.warnings_vi
    )
    assert any(
        "PERF_MONITOR_OVERSPEC" in warning
        for warning in artifact.warnings_vi
    )


def test_generator_recommends_optional_monitor_from_real_catalog_without_cart_total() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz kèm màn hình 2K",
        use_case=UseCase.GAMING,
        budget_max=25_000_000,
        target_games=["Cyberpunk 2077"],
        performance_targets=["1440p", "Ultra", "144Hz"],
        mentioned_components=["monitor"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_monitor_addon",
        intent=intent,
        catalog=_active_catalog_snapshot(),
        optimize=False,
    )
    monitor = next(item for item in artifact.recommended_addons if item.kind == "monitor")

    assert monitor.sku == "260602184"
    assert monitor.category == "monitor"
    assert monitor.optional is True
    assert monitor.price_vnd == 4_990_000
    assert "2560x1440" in monitor.reason_vi
    assert monitor.sku not in {item.sku for item in artifact.items}
    assert monitor.sku not in {item["sku"] for item in artifact.mock_cart_payload.items}
    assert artifact.total_price_vnd == sum(item.price_vnd for item in artifact.items)
    assert any("không cộng vào tổng giá" in item for item in artifact.explanations_vi)


def test_generator_keeps_monitor_addon_conservative_without_display_target() -> None:
    intent = BuildIntent(
        raw_text="PC gaming 20 triệu chơi Valorant và LMHT 144Hz",
        use_case=UseCase.GAMING,
        budget_max=20_000_000,
        target_games=["Valorant", "LMHT"],
        performance_targets=["144Hz"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_no_monitor_addon",
        intent=intent,
        catalog=_active_catalog_snapshot(),
        optimize=False,
    )

    assert all(item.kind != "monitor" for item in artifact.recommended_addons)


def test_generator_recommends_optional_cooler_from_real_catalog_with_fit_notes() -> None:
    intent = BuildIntent(
        raw_text="Máy văn phòng khoảng 20 triệu, ưu tiên êm và bền, thêm tản nhiệt CPU",
        use_case=UseCase.OFFICE,
        budget_max=20_000_000,
        noise_preferences="quiet",
        mentioned_components=["cooler"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_cooler_addon",
        intent=intent,
        catalog=_active_catalog_snapshot(),
        optimize=False,
    )
    cooler = next(item for item in artifact.recommended_addons if item.kind == "cooler")

    assert cooler.sku == "251012780"
    assert cooler.category == "cooler"
    assert cooler.optional is True
    assert "vận hành êm" in cooler.reason_vi
    assert any("LGA1700" in note for note in cooler.fit_notes_vi)
    assert any("TDP" in note for note in cooler.fit_notes_vi)
    assert any("giới hạn case" in note for note in cooler.fit_notes_vi)
    assert cooler.sku not in {item.sku for item in artifact.items}
    assert cooler.sku not in {item["sku"] for item in artifact.mock_cart_payload.items}
    assert artifact.total_price_vnd == sum(item.price_vnd for item in artifact.items)


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
    assert body["performance_profile"]["balance"]["score"] >= 70
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
    assert [alternative.ranking.rank for alternative in response.alternatives] == [1, 2, 3, 4]
    assert [alternative.ranking.score for alternative in response.alternatives] == sorted(
        [alternative.ranking.score for alternative in response.alternatives],
        reverse=True,
    )
    assert all(alternative.ranking.reasons_vi for alternative in response.alternatives)
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


def test_alternative_generator_prioritizes_cuda_gpu_for_ai_workload() -> None:
    intent = BuildIntent(
        raw_text="PC AI local LLM 13B 40 triệu",
        use_case=UseCase.AI,
        budget_max=40_000_000,
        target_apps=["Local LLM"],
        performance_targets=["13B"],
    )
    base_artifact = generate_build_artifact(
        build_session_id="bs_ranked_ai_alternatives",
        intent=intent,
        catalog=_snapshot(),
        optimize=False,
    )

    response = generate_build_alternatives(
        base_artifact=base_artifact,
        catalog=_snapshot(),
    )

    assert response.alternatives[0].kind == "nvidia_gpu"
    assert response.alternatives[0].ranking.rank == 1
    assert response.alternatives[0].ranking.priority == "recommended"
    assert any(
        "CUDA" in reason or "NVIDIA" in reason
        for reason in response.alternatives[0].ranking.reasons_vi
    )


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
    assert [item["ranking"]["rank"] for item in body["alternatives"]] == [1, 2, 3, 4]
    assert all(item["ranking"]["score"] > 0 for item in body["alternatives"])
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


def test_addon_recommendations_are_excluded_from_approval_payload() -> None:
    client = _client(_active_catalog_snapshot())
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": (
                "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz "
                "kèm màn hình 2K"
            ),
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()
    addon_skus = {item["sku"] for item in build["recommended_addons"]}

    response = client.post(f"/builds/{build['build_id']}/approve")

    assert response.status_code == 200
    body = response.json()
    assert addon_skus == {"260602184"}
    assert body["total_price_vnd"] == build["total_price_vnd"]
    assert addon_skus.isdisjoint(set(body["approval"]["selected_skus"].values()))
    assert addon_skus.isdisjoint({item["sku"] for item in body["mock_cart_payload"]["items"]})


def test_approve_endpoint_can_include_selected_addons_in_shopping_list() -> None:
    client = _client(_active_catalog_snapshot())
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": (
                "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz "
                "kèm màn hình 2K"
            ),
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()
    addon = build["recommended_addons"][0]

    response = client.post(
        f"/builds/{build['build_id']}/approve",
        json={"selected_addon_skus": [addon["sku"]]},
    )

    assert response.status_code == 200
    body = response.json()
    assert addon["sku"] == "260602184"
    assert body["total_price_vnd"] == build["total_price_vnd"]
    assert body["approval"]["total_price_vnd"] == build["total_price_vnd"]
    assert addon["sku"] not in set(body["approval"]["selected_skus"].values())
    assert body["add_on_total_price_vnd"] == 4_990_000
    assert body["shopping_list_total_price_vnd"] == build["total_price_vnd"] + 4_990_000
    assert body["item_count"] == len(build["items"]) + 1
    assert [item["sku"] for item in body["selected_addons"]] == [addon["sku"]]
    assert addon["sku"] in {item["sku"] for item in body["mock_cart_payload"]["items"]}
    assert any(
        item["name"] == addon["name"]
        for item in body["mock_cart_payload"]["items"]
        if item["sku"] == addon["sku"]
    )
    assert any("tùy chọn" in warning.casefold() for warning in body["warnings_vi"])


def test_approve_endpoint_rejects_addon_sku_that_was_not_recommended() -> None:
    client = _client(_active_catalog_snapshot())
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    build = client.post(f"/sessions/{session['build_session_id']}/generate").json()

    response = client.post(
        f"/builds/{build['build_id']}/approve",
        json={"selected_addon_skus": ["not-recommended-sku"]},
    )

    assert response.status_code == 422
    assert "recommended add-ons" in response.json()["detail"]


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


def test_creator_profile_warns_when_ram_is_below_creator_threshold_without_optimizer() -> None:
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
        optimize=False,
    )

    assert artifact.performance_profile.use_case == "creator"
    assert artifact.performance_profile.fit_level == "limited"
    assert {profile.name for profile in artifact.performance_profile.workload_profiles} == {
        "Adobe Premiere Pro",
        "Adobe After Effects",
    }
    assert all(
        "ram_limited" in profile.bottlenecks
        for profile in artifact.performance_profile.workload_profiles
    )
    assert all(
        "storage_limited" in profile.bottlenecks
        for profile in artifact.performance_profile.workload_profiles
    )
    assert any("RAM 16GB" in note for note in artifact.performance_profile.bottleneck_notes_vi)
    assert any("32GB" in warning for warning in artifact.performance_profile.warnings_vi)
    assert any("32GB" in warning for warning in artifact.warnings_vi)


def test_generator_applies_bounded_multi_swap_optimizer_for_creator() -> None:
    intent = BuildIntent(
        raw_text="PC đồ họa 35 triệu dùng Premiere và After Effects",
        use_case=UseCase.CREATOR,
        budget_max=35_000_000,
        target_apps=["Adobe Premiere Pro", "Adobe After Effects"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_creator_optimized",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.total_price_vnd == 18_490_000
    assert artifact.performance_profile.fit_level == "adequate"
    assert any(item.slot == BuildSlot.RAM and item.sku == "240601032" for item in artifact.items)
    assert any(item.slot == BuildSlot.STORAGE and item.sku == "230900321" for item in artifact.items)
    assert sum("Optimizer" in explanation for explanation in artifact.explanations_vi) == 2
    assert all(
        "ram_limited" not in profile.bottlenecks
        for profile in artifact.performance_profile.workload_profiles
    )
    assert all(
        "storage_limited" not in profile.bottlenecks
        for profile in artifact.performance_profile.workload_profiles
    )
    assert all(
        profile.fit_level == "good"
        for profile in artifact.performance_profile.workload_profiles
    )


def test_photoshop_profile_accepts_entry_creator_specs_without_heavy_video_thresholds() -> None:
    intent = BuildIntent(
        raw_text="PC đồ họa 25 triệu dùng Photoshop",
        use_case=UseCase.CREATOR,
        budget_max=25_000_000,
        target_apps=["Adobe Photoshop"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_photoshop",
        intent=intent,
        catalog=_snapshot(),
    )
    profile = artifact.performance_profile.workload_profiles[0]

    assert profile.name == "Adobe Photoshop"
    assert profile.fit_level == "good"
    assert profile.bottlenecks == []


def test_streaming_profile_surfaces_obs_fit_and_cuda_preference() -> None:
    intent = BuildIntent(
        raw_text="PC stream OBS 25 triệu",
        use_case=UseCase.STREAMING,
        budget_max=25_000_000,
        target_apps=["OBS Studio"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_streaming",
        intent=intent,
        catalog=_snapshot(),
        optimize=False,
    )
    profile = artifact.performance_profile.workload_profiles[0]

    assert artifact.performance_profile.use_case == "streaming"
    assert profile.name == "OBS Studio"
    assert "cuda_preferred" in profile.bottlenecks
    assert any("CUDA" in warning for warning in artifact.performance_profile.warnings_vi)


def test_generator_applies_recommended_cuda_optimizer_swap_for_streaming() -> None:
    intent = BuildIntent(
        raw_text="PC stream OBS 25 triệu",
        use_case=UseCase.STREAMING,
        budget_max=25_000_000,
        target_apps=["OBS Studio"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_streaming_optimized",
        intent=intent,
        catalog=_snapshot(),
    )
    profile = artifact.performance_profile.workload_profiles[0]

    assert artifact.total_price_vnd == 19_190_000
    assert any(item.slot == BuildSlot.VGA and item.sku == "231101406" for item in artifact.items)
    assert any("GPU NVIDIA" in explanation for explanation in artifact.explanations_vi)
    assert profile.fit_level == "good"
    assert "cuda_preferred" not in profile.bottlenecks


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
        optimize=False,
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
    assert artifact.performance_profile.fit_level == "limited"
    assert "vram 8gb" in profile_text
    assert "32gb" in profile_text
    assert "fps" not in profile_text


def test_ai_profile_uses_model_class_vram_tiers_for_13b_llm() -> None:
    intent = BuildIntent(
        raw_text="PC AI local LLM 13B 40 triệu",
        use_case=UseCase.AI,
        budget_max=40_000_000,
        target_apps=["Local LLM"],
        performance_targets=["13B"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_ai_13b",
        intent=intent,
        catalog=_snapshot(),
    )
    profile = artifact.performance_profile.workload_profiles[0]

    assert profile.name == "Local LLM 13B"
    assert profile.fit_level == "limited"
    assert "vram_limited" in profile.bottlenecks
    assert "13B" in profile.requirement_summary_vi
    assert any(item.slot == BuildSlot.VGA and item.sku == "231101406" for item in artifact.items)
    assert any(item.slot == BuildSlot.RAM and item.sku == "240601032" for item in artifact.items)
    assert sum("Optimizer" in explanation for explanation in artifact.explanations_vi) == 2
    assert any("WORKLOAD_LIMITED" in warning for warning in artifact.performance_profile.warnings_vi)


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
    assert any("ưu tiên êm" in note.casefold() for note in artifact.performance_profile.fit_notes_vi)
    assert any(
        item.slot == BuildSlot.VGA and "xuất hình" in item.explanation_vi
        for item in artifact.items
    )


def test_office_profile_warns_when_multi_monitor_outputs_are_unknown() -> None:
    intent = BuildIntent(
        raw_text="Máy văn phòng 20 triệu chạy Excel với 2 màn hình, ưu tiên êm",
        use_case=UseCase.OFFICE,
        budget_max=20_000_000,
        monitor_count=2,
        noise_preferences="quiet",
        mentioned_components=["monitor"],
    )

    artifact = generate_build_artifact(
        build_session_id="bs_office_multi_monitor",
        intent=intent,
        catalog=_snapshot(),
    )

    assert artifact.performance_profile.fit_level == "adequate"
    assert any(
        "OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN" in warning
        for warning in artifact.performance_profile.warnings_vi
    )
    assert any(
        "OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN" in warning
        for warning in artifact.warnings_vi
    )
    assert any(
        evidence.label == "Màn hình" and evidence.value == "2 màn hình"
        for evidence in artifact.performance_profile.evidence
    )


def test_office_profile_supports_igpu_office_build_without_discrete_vga() -> None:
    items = _items()
    original_cpu = next(item for item in items if item.sku == "211208130")
    igpu_cpu = original_cpu.model_copy(
        update={"specs": {**original_cpu.specs, "integrated_graphics": True}}
    )
    mutated = [igpu_cpu if item.sku == igpu_cpu.sku else item for item in items]
    intent = BuildIntent(
        raw_text="Máy văn phòng 20 triệu chạy Excel, ưu tiên êm",
        use_case=UseCase.OFFICE,
        budget_max=20_000_000,
        noise_preferences="quiet",
    )

    artifact = generate_build_artifact(
        build_session_id="bs_office_igpu",
        intent=intent,
        catalog=_snapshot(mutated),
    )

    assert all(item.slot != BuildSlot.VGA for item in artifact.items)
    assert any("iGPU" in note for note in artifact.performance_profile.fit_notes_vi)
    assert all("PERF_IMBALANCE" not in warning for warning in artifact.performance_profile.warnings_vi)

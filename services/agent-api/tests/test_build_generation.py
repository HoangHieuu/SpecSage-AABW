from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.build_generator import generate_build_artifact
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
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

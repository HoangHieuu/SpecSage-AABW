from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.build_iteration import parse_iteration_command
from pc_build_copilot.build_models import BuildIterationRequest
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_iteration",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def _client() -> TestClient:
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=_snapshot())))


def _confirmed_session(client: TestClient, message: str) -> str:
    session = client.post("/sessions", json={"locale": "vi-VN", "channel": "web"}).json()
    session_id = session["build_session_id"]
    response = client.post(
        f"/sessions/{session_id}/intent",
        json={"message": message, "confirm": True, "preset": "gaming"},
    )
    assert response.status_code == 200
    return session_id


def test_iteration_parser_extracts_command_type_and_budget_cap() -> None:
    parsed = parse_iteration_command("Tăng SSD nhưng giữ dưới 20 triệu")

    assert parsed.command_type == "more_storage"
    assert parsed.target_budget_max_vnd == 20_000_000
    assert parsed.priority_label_vi == "ưu tiên SSD/lưu trữ"
    assert "20.000.000 VND" in parsed.summary_vi


def test_iteration_endpoint_applies_storage_command_as_new_build_version() -> None:
    client = _client()
    session_id = _confirmed_session(
        client,
        "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz, ưu tiên VGA",
    )
    generated = client.post(f"/sessions/{session_id}/generate").json()

    response = client.post(
        f"/builds/{generated['build_id']}/iterate",
        json=BuildIterationRequest(command_vi="Tăng SSD nhưng giữ dưới 20 triệu").model_dump(),
    )

    assert response.status_code == 200
    body = response.json()
    applied = body["applied_build"]
    assert body["command"]["command_type"] == "more_storage"
    assert body["selected_alternative"]["kind"] == "storage_upgrade"
    assert applied["build_version"] == generated["build_version"] + 1
    assert applied["total_price_vnd"] <= 20_000_000
    assert any(item["slot"] == "storage" and item["sku"] == "230900321" for item in applied["items"])
    assert applied["optimizer_trace"]["applied_iteration_count"] == 2
    assert any(
        item["decision"] == "accepted" and item["candidate_kind"] == "storage_upgrade"
        for item in applied["optimizer_trace"]["iterations"]
    )
    assert applied["orchestration_trace"][0]["agent"] == "optimizer"
    assert applied["orchestration_trace"][0]["outputs"]["selected_variant_kind"] == "storage_upgrade"
    assert "Đã xử lý yêu cầu điều chỉnh" in applied["explanations_vi"][0]


def test_iteration_endpoint_can_apply_budget_saver_without_changing_public_alternatives() -> None:
    client = _client()
    session_id = _confirmed_session(
        client,
        "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz, ưu tiên VGA",
    )
    generated = client.post(f"/sessions/{session_id}/generate").json()
    public_alternatives = client.get(f"/builds/{generated['build_id']}/alternatives").json()

    response = client.post(
        f"/builds/{generated['build_id']}/iterate",
        json={"command_vi": "Giảm xuống dưới 18 triệu"},
    )

    assert response.status_code == 200
    body = response.json()
    applied = body["applied_build"]
    assert "budget_saver" not in {item["kind"] for item in public_alternatives["alternatives"]}
    assert body["command"]["command_type"] == "cheaper"
    assert body["selected_alternative"]["kind"] == "budget_saver"
    assert applied["total_price_vnd"] <= 18_000_000
    assert any(item["slot"] == "vga" and item["sku"] == "260508255" for item in applied["items"])
    assert any("PERF_BELOW_TARGET" in warning for warning in applied["warnings_vi"])


def test_iteration_endpoint_rejects_unsupported_or_over_budget_command() -> None:
    client = _client()
    session_id = _confirmed_session(client, "PC gaming 25 triệu chơi Valorant 144Hz")
    generated = client.post(f"/sessions/{session_id}/generate").json()

    unsupported = client.post(
        f"/builds/{generated['build_id']}/iterate",
        json={"command_vi": "Đổi sang vỏ màu hồng pastel"},
    )
    impossible_budget = client.post(
        f"/builds/{generated['build_id']}/iterate",
        json={"command_vi": "Tăng SSD nhưng giữ dưới 17 triệu"},
    )

    assert unsupported.status_code == 422
    assert impossible_budget.status_code == 409


def test_iteration_build_versions_appear_in_session_trace() -> None:
    client = _client()
    session_id = _confirmed_session(
        client,
        "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz, ưu tiên VGA",
    )
    generated = client.post(f"/sessions/{session_id}/generate").json()
    iterated = client.post(
        f"/builds/{generated['build_id']}/iterate",
        json={"command_vi": "Tăng SSD nhưng giữ dưới 20 triệu"},
    ).json()

    trace = client.get(f"/sessions/{session_id}/trace").json()

    assert trace["generated_build_count"] == 2
    assert [build["build_version"] for build in trace["builds"]] == [1, 2]
    assert trace["builds"][1]["build_id"] == iterated["applied_build"]["build_id"]
    assert trace["builds"][1]["events"][0]["agent"] == "optimizer"
    assert (
        trace["builds"][1]["events"][0]["outputs_redacted"]["selected_variant_kind"]
        == "storage_upgrade"
    )

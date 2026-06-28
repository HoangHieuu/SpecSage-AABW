from datetime import UTC, datetime

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.build_store import BuildStore
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_demo",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def test_demo_flow_generate_apply_approve_feedback_with_optimizer_trace() -> None:
    client = TestClient(
        create_app(
            store=SessionStore(),
            catalog_repository=CatalogRepository(snapshot=_snapshot()),
            build_store=BuildStore(),
        )
    )

    session = client.post("/sessions", json={"locale": "vi-VN", "channel": "web"}).json()
    session_id = session["build_session_id"]
    message = "PC gaming 25 triệu chơi Cyberpunk 2077 1440p Ultra 144Hz, ưu tiên VGA"

    intent_response = client.post(
        f"/sessions/{session_id}/intent",
        json={"message": message, "confirm": True, "preset": "gaming"},
    )
    assert intent_response.status_code == 200
    assert intent_response.json()["revision"]["confirmed"] is True

    generated_response = client.post(f"/sessions/{session_id}/generate")
    assert generated_response.status_code == 200
    generated = generated_response.json()
    assert generated["status"] == "generated"
    assert generated["optimizer_trace"]["applied_iteration_count"] == 1
    assert "ưu tiên GPU/VGA" in generated["optimizer_trace"]["priority_overrides"]
    assert any(
        item["decision"] == "accepted" and item["candidate_kind"] == "nvidia_gpu"
        for item in generated["optimizer_trace"]["iterations"]
    )
    assert any("PERF_BELOW_TARGET" in warning for warning in generated["warnings_vi"])

    alternatives_response = client.get(f"/builds/{generated['build_id']}/alternatives")
    assert alternatives_response.status_code == 200
    alternatives = alternatives_response.json()["alternatives"]
    assert alternatives

    applied_response = client.post(
        f"/builds/{generated['build_id']}/alternatives/{alternatives[0]['variant_id']}/apply"
    )
    assert applied_response.status_code == 200
    applied = applied_response.json()
    assert applied["build_version"] == 2
    assert applied["optimizer_trace"]["applied_iteration_count"] == 1

    approval_response = client.post(f"/builds/{applied['build_id']}/approve")
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "cart_ready"

    gpu_item = next(item for item in applied["items"] if item["slot"] == "vga")
    feedback_response = client.post(
        f"/builds/{applied['build_id']}/feedback",
        json={
            "rating": "thumbs_down",
            "reason_tags": ["wrong_performance_fit"],
            "comment_vi": "Demo review queue smoke",
            "part_feedback": [
                {
                    "slot": gpu_item["slot"],
                    "sku": gpu_item["sku"],
                    "rating": "thumbs_down",
                }
            ],
        },
    )
    assert feedback_response.status_code == 200
    feedback = feedback_response.json()
    assert feedback["review_queue_status"] == "queued"

    trace_response = client.get(f"/sessions/{session_id}/trace")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["generated_build_count"] == 2
    assert any(
        event["agent"] == "optimizer"
        and event["outputs_redacted"]["accepted_iterations"] == 1
        for build in trace["builds"]
        for event in build["events"]
    )

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pc_build_copilot.api import create_app
from pc_build_copilot.catalog_models import CatalogSnapshot
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.sqlite_store import SqliteBuildStore, SqliteSessionStore
from pc_build_copilot.store import SessionStore

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


def _snapshot() -> CatalogSnapshot:
    return CatalogSnapshot(
        snapshot_version="catalog_test_feedback",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
    )


def _client(db_path: Path | None = None) -> TestClient:
    if db_path is not None:
        return TestClient(
            create_app(
                store=SqliteSessionStore(db_path),
                catalog_repository=CatalogRepository(snapshot=_snapshot()),
                build_store=SqliteBuildStore(db_path),
            )
        )
    return TestClient(create_app(SessionStore(), CatalogRepository(snapshot=_snapshot())))


def _generated_build(client: TestClient) -> dict:
    session = client.post("/sessions", json={}).json()
    client.post(
        f"/sessions/{session['build_session_id']}/intent",
        json={
            "message": "PC gaming 25 triệu chơi Valorant và LMHT 144Hz",
            "confirm": True,
            "preset": "gaming",
        },
    )
    return client.post(f"/sessions/{session['build_session_id']}/generate").json()


def test_submit_build_feedback_links_to_build_and_catalog_snapshot() -> None:
    client = _client()
    build = _generated_build(client)
    cpu = next(item for item in build["items"] if item["slot"] == "cpu")

    response = client.post(
        f"/builds/{build['build_id']}/feedback",
        json={
            "rating": "thumbs_up",
            "reason_tags": ["fits_need", "good_value"],
            "comment_vi": "Cau hinh de hieu va dung nhu cau.",
            "part_feedback": [
                {
                    "slot": "cpu",
                    "sku": cpu["sku"],
                    "rating": "thumbs_up",
                    "reason_tags": ["fits_need"],
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["build_id"] == build["build_id"]
    assert body["build_session_id"] == build["build_session_id"]
    assert body["build_version"] == build["build_version"]
    assert body["catalog_version"] == "catalog_test_feedback"
    assert body["rules_version"] == build["rules_version"]
    assert body["rating"] == "thumbs_up"
    assert body["review_queue_status"] == "not_queued"
    assert body["review_queue_reason_vi"] is None
    assert body["part_feedback"][0]["slot"] == "cpu"
    assert body["part_feedback"][0]["sku"] == cpu["sku"]
    assert body["part_feedback"][0]["name"] == cpu["name"]

    stored = client.get(f"/builds/{build['build_id']}/feedback").json()
    assert [item["feedback_id"] for item in stored] == [body["feedback_id"]]
    assert client.get("/feedback/review-queue").json() == []


def test_low_rating_feedback_is_available_in_review_queue() -> None:
    client = _client()
    build = _generated_build(client)
    gpu = next(item for item in build["items"] if item["slot"] == "vga")

    response = client.post(
        f"/builds/{build['build_id']}/feedback",
        json={
            "rating": "thumbs_down",
            "reason_tags": ["wrong_performance_fit", "price_or_stock_concern"],
            "comment_vi": "Muon xem lai GPU va ly do chon.",
            "part_feedback": [
                {
                    "slot": "vga",
                    "sku": gpu["sku"],
                    "rating": "thumbs_down",
                    "reason_tags": ["wrong_performance_fit"],
                    "comment_vi": "Can giai thich ro hon ve GPU.",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_queue_status"] == "queued"
    assert "review" in body["review_queue_reason_vi"].casefold()

    queue = client.get("/feedback/review-queue").json()
    assert len(queue) == 1
    assert queue[0]["feedback_id"] == body["feedback_id"]
    assert queue[0]["part_feedback"][0]["slot"] == "vga"


def test_feedback_rejects_missing_build_and_part_not_in_build() -> None:
    client = _client()

    missing = client.post(
        "/builds/build_missing/feedback",
        json={"rating": "thumbs_up"},
    )

    assert missing.status_code == 404

    build = _generated_build(client)
    mismatch = client.post(
        f"/builds/{build['build_id']}/feedback",
        json={
            "rating": "thumbs_up",
            "part_feedback": [
                {
                    "slot": "cpu",
                    "sku": "sku_not_in_build",
                    "rating": "thumbs_down",
                }
            ],
        },
    )

    assert mismatch.status_code == 422
    assert "SKU in this build" in mismatch.json()["detail"]


def test_feedback_rejects_duplicate_part_feedback() -> None:
    client = _client()
    build = _generated_build(client)
    ram = next(item for item in build["items"] if item["slot"] == "ram")

    response = client.post(
        f"/builds/{build['build_id']}/feedback",
        json={
            "rating": "thumbs_up",
            "part_feedback": [
                {"slot": "ram", "sku": ram["sku"], "rating": "thumbs_up"},
                {"slot": "ram", "sku": ram["sku"], "rating": "thumbs_down"},
            ],
        },
    )

    assert response.status_code == 422
    assert "once" in response.json()["detail"]


def test_sqlite_feedback_survives_app_reinstantiation(tmp_path: Path) -> None:
    db_path = tmp_path / "feedback.sqlite3"
    client = _client(db_path)
    build = _generated_build(client)
    psu = next(item for item in build["items"] if item["slot"] == "psu")
    feedback = client.post(
        f"/builds/{build['build_id']}/feedback",
        json={
            "rating": "thumbs_down",
            "reason_tags": ["compatibility_concern"],
            "part_feedback": [
                {
                    "slot": "psu",
                    "sku": psu["sku"],
                    "rating": "thumbs_down",
                    "reason_tags": ["compatibility_concern"],
                }
            ],
        },
    ).json()

    restarted = _client(db_path)
    stored = restarted.get(f"/builds/{build['build_id']}/feedback").json()
    queue = restarted.get("/feedback/review-queue").json()

    assert stored[0]["feedback_id"] == feedback["feedback_id"]
    assert stored[0]["build_session_id"] == build["build_session_id"]
    assert stored[0]["part_feedback"][0]["name"] == psu["name"]
    assert queue[0]["feedback_id"] == feedback["feedback_id"]

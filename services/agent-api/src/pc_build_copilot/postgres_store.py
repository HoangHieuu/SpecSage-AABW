from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypeVar

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from pc_build_copilot.build_models import (
    BuildApprovalRequest,
    BuildArtifact,
    BuildFeedback,
    BuildFeedbackRequest,
    BuildStatus,
    CartReadyHandoff,
)
from pc_build_copilot.build_store import (
    BuildStore,
    assert_same_addon_selection,
    build_feedback_from_artifact,
    cart_handoff_from_artifact,
    normalized_selected_addon_skus,
)
from pc_build_copilot.models import BuildSession, IntentRevision, SessionState
from pc_build_copilot.store import SessionStore


ModelT = TypeVar("ModelT", bound=BaseModel)


POSTGRES_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS build_sessions (
        build_session_id TEXT PRIMARY KEY,
        state TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        ttl_expires_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS intent_revisions (
        sequence_id BIGSERIAL PRIMARY KEY,
        revision_id TEXT NOT NULL UNIQUE,
        build_session_id TEXT NOT NULL REFERENCES build_sessions(build_session_id)
            ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL,
        confirmed BOOLEAN NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_intent_revisions_session
        ON intent_revisions(build_session_id, sequence_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_intent_revisions_confirmed
        ON intent_revisions(build_session_id, sequence_id DESC)
        WHERE confirmed = TRUE
    """,
    """
    CREATE TABLE IF NOT EXISTS build_artifacts (
        build_id TEXT PRIMARY KEY,
        build_session_id TEXT NOT NULL REFERENCES build_sessions(build_session_id)
            ON DELETE CASCADE,
        build_version INTEGER NOT NULL,
        generated_at TIMESTAMPTZ NOT NULL,
        status TEXT NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_build_artifacts_session
        ON build_artifacts(build_session_id, build_version, generated_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS cart_handoffs (
        handoff_id TEXT PRIMARY KEY,
        build_id TEXT NOT NULL UNIQUE REFERENCES build_artifacts(build_id)
            ON DELETE CASCADE,
        build_session_id TEXT NOT NULL REFERENCES build_sessions(build_session_id)
            ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL,
        selected_addon_skus JSONB NOT NULL DEFAULT '[]'::JSONB,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_cart_handoffs_session
        ON cart_handoffs(build_session_id, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS build_feedback (
        feedback_id TEXT PRIMARY KEY,
        build_id TEXT NOT NULL REFERENCES build_artifacts(build_id)
            ON DELETE CASCADE,
        build_session_id TEXT NOT NULL REFERENCES build_sessions(build_session_id)
            ON DELETE CASCADE,
        build_version INTEGER NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        rating TEXT NOT NULL,
        review_queue_status TEXT NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_build_feedback_build
        ON build_feedback(build_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_build_feedback_session
        ON build_feedback(build_session_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pg_build_feedback_review_queued
        ON build_feedback(created_at DESC)
        WHERE review_queue_status = 'queued'
    """,
)


def create_postgres_stores(database_url: str) -> tuple[PostgresSessionStore, PostgresBuildStore]:
    _ensure_schema(database_url)
    return PostgresSessionStore(database_url), PostgresBuildStore(database_url)


class PostgresSessionStore(SessionStore):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def create(self, session: BuildSession) -> BuildSession:
        with _connect(self.database_url) as conn:
            conn.execute(
                """
                INSERT INTO build_sessions (
                    build_session_id,
                    state,
                    created_at,
                    updated_at,
                    ttl_expires_at,
                    payload_json
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    session.build_session_id,
                    session.state.value,
                    session.created_at,
                    session.updated_at,
                    session.ttl_expires_at,
                    _model_jsonb(session),
                ),
            )
        return session

    def get(self, build_session_id: str) -> BuildSession:
        with _connect(self.database_url) as conn:
            row = conn.execute(
                "SELECT payload_json FROM build_sessions WHERE build_session_id = %s",
                (build_session_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="build_session_id not found")
        return _model_from_payload(BuildSession, row["payload_json"])

    def add_revision(self, revision: IntentRevision) -> IntentRevision:
        with _connect(self.database_url) as conn:
            session = _get_session(conn, revision.build_session_id)
            next_state = (
                SessionState.INTENT_CONFIRMED
                if revision.confirmed
                else SessionState.INTENT_DRAFT
            )
            session = session.model_copy(
                update={"state": next_state, "updated_at": datetime.now(UTC)}
            )
            _upsert_session(conn, session)
            conn.execute(
                """
                INSERT INTO intent_revisions (
                    revision_id,
                    build_session_id,
                    created_at,
                    confirmed,
                    payload_json
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    revision.revision_id,
                    revision.build_session_id,
                    revision.created_at,
                    revision.confirmed,
                    _model_jsonb(revision),
                ),
            )
        return revision

    def revisions(self, build_session_id: str) -> list[IntentRevision]:
        with _connect(self.database_url) as conn:
            _get_session(conn, build_session_id)
            rows = conn.execute(
                """
                SELECT payload_json
                FROM intent_revisions
                WHERE build_session_id = %s
                ORDER BY sequence_id ASC
                """,
                (build_session_id,),
            ).fetchall()
        return [_model_from_payload(IntentRevision, row["payload_json"]) for row in rows]

    def latest_confirmed_revision(self, build_session_id: str) -> IntentRevision:
        with _connect(self.database_url) as conn:
            _get_session(conn, build_session_id)
            row = conn.execute(
                """
                SELECT payload_json
                FROM intent_revisions
                WHERE build_session_id = %s AND confirmed = TRUE
                ORDER BY sequence_id DESC
                LIMIT 1
                """,
                (build_session_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=409,
                detail="intent must be confirmed before generation",
            )
        return _model_from_payload(IntentRevision, row["payload_json"])

    def mark_generated(self, build_session_id: str) -> BuildSession:
        return self._mark_state(build_session_id, SessionState.GENERATED)

    def mark_reviewing(self, build_session_id: str) -> BuildSession:
        return self._mark_state(build_session_id, SessionState.REVIEWING)

    def mark_approved(self, build_session_id: str) -> BuildSession:
        return self._mark_state(build_session_id, SessionState.APPROVED)

    def mark_cart_ready(self, build_session_id: str) -> BuildSession:
        return self._mark_state(build_session_id, SessionState.CART_READY)

    def _mark_state(
        self,
        build_session_id: str,
        state: SessionState,
    ) -> BuildSession:
        with _connect(self.database_url) as conn:
            session = _get_session(conn, build_session_id)
            session = session.model_copy(
                update={"state": state, "updated_at": datetime.now(UTC)}
            )
            _upsert_session(conn, session)
        return session


class PostgresBuildStore(BuildStore):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def save(self, artifact: BuildArtifact) -> BuildArtifact:
        with _connect(self.database_url) as conn:
            conn.execute(
                """
                INSERT INTO build_artifacts (
                    build_id,
                    build_session_id,
                    build_version,
                    generated_at,
                    status,
                    payload_json
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(build_id) DO UPDATE SET
                    build_session_id = excluded.build_session_id,
                    build_version = excluded.build_version,
                    generated_at = excluded.generated_at,
                    status = excluded.status,
                    payload_json = excluded.payload_json
                """,
                (
                    artifact.build_id,
                    artifact.build_session_id,
                    artifact.build_version,
                    artifact.generated_at,
                    artifact.status.value,
                    _model_jsonb(artifact),
                ),
            )
        return artifact

    def get(self, build_id: str) -> BuildArtifact:
        with _connect(self.database_url) as conn:
            row = conn.execute(
                "SELECT payload_json FROM build_artifacts WHERE build_id = %s",
                (build_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="build_id not found")
        return _model_from_payload(BuildArtifact, row["payload_json"])

    def list_for_session(self, build_session_id: str) -> list[BuildArtifact]:
        with _connect(self.database_url) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM build_artifacts
                WHERE build_session_id = %s
                ORDER BY build_version ASC, generated_at ASC
                """,
                (build_session_id,),
            ).fetchall()
        return [_model_from_payload(BuildArtifact, row["payload_json"]) for row in rows]

    def approve(
        self,
        build_id: str,
        payload: BuildApprovalRequest | None = None,
    ) -> CartReadyHandoff:
        artifact = self.get(build_id)
        payload = payload or BuildApprovalRequest()
        selected_addon_skus = normalized_selected_addon_skus(artifact, payload)
        with _connect(self.database_url) as conn:
            existing = conn.execute(
                "SELECT payload_json FROM cart_handoffs WHERE build_id = %s",
                (build_id,),
            ).fetchone()
            if existing is not None:
                handoff = _model_from_payload(
                    CartReadyHandoff,
                    existing["payload_json"],
                )
                assert_same_addon_selection(handoff, selected_addon_skus)
                return handoff

            if artifact.status != BuildStatus.GENERATED or not artifact.can_approve:
                raise HTTPException(
                    status_code=409,
                    detail="build must be compatible and within budget before approval",
                )

            handoff = cart_handoff_from_artifact(artifact, payload)
            conn.execute(
                """
                INSERT INTO cart_handoffs (
                    handoff_id,
                    build_id,
                    build_session_id,
                    created_at,
                    selected_addon_skus,
                    payload_json
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    handoff.handoff_id,
                    handoff.build_id,
                    handoff.build_session_id,
                    handoff.created_at,
                    Jsonb(list(selected_addon_skus)),
                    _model_jsonb(handoff),
                ),
            )
        return handoff

    def save_feedback(
        self,
        build_id: str,
        payload: BuildFeedbackRequest,
    ) -> BuildFeedback:
        artifact = self.get(build_id)
        feedback = build_feedback_from_artifact(artifact, payload)
        with _connect(self.database_url) as conn:
            conn.execute(
                """
                INSERT INTO build_feedback (
                    feedback_id,
                    build_id,
                    build_session_id,
                    build_version,
                    created_at,
                    rating,
                    review_queue_status,
                    payload_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    feedback.feedback_id,
                    feedback.build_id,
                    feedback.build_session_id,
                    feedback.build_version,
                    feedback.created_at,
                    feedback.rating.value,
                    feedback.review_queue_status.value,
                    _model_jsonb(feedback),
                ),
            )
        return feedback

    def feedback_for_build(self, build_id: str) -> list[BuildFeedback]:
        self.get(build_id)
        with _connect(self.database_url) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM build_feedback
                WHERE build_id = %s
                ORDER BY created_at ASC
                """,
                (build_id,),
            ).fetchall()
        return [_model_from_payload(BuildFeedback, row["payload_json"]) for row in rows]

    def feedback_review_queue(self) -> list[BuildFeedback]:
        with _connect(self.database_url) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM build_feedback
                WHERE review_queue_status = 'queued'
                ORDER BY created_at DESC
                """,
            ).fetchall()
        return [_model_from_payload(BuildFeedback, row["payload_json"]) for row in rows]


def _connect(database_url: str) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(database_url, row_factory=dict_row)


def _ensure_schema(database_url: str) -> None:
    with _connect(database_url) as conn:
        for statement in POSTGRES_SCHEMA_STATEMENTS:
            conn.execute(statement)


def _get_session(
    conn: psycopg.Connection[dict[str, Any]],
    build_session_id: str,
) -> BuildSession:
    row = conn.execute(
        "SELECT payload_json FROM build_sessions WHERE build_session_id = %s",
        (build_session_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="build_session_id not found")
    return _model_from_payload(BuildSession, row["payload_json"])


def _upsert_session(
    conn: psycopg.Connection[dict[str, Any]],
    session: BuildSession,
) -> None:
    conn.execute(
        """
        INSERT INTO build_sessions (
            build_session_id,
            state,
            created_at,
            updated_at,
            ttl_expires_at,
            payload_json
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(build_session_id) DO UPDATE SET
            state = excluded.state,
            updated_at = excluded.updated_at,
            ttl_expires_at = excluded.ttl_expires_at,
            payload_json = excluded.payload_json
        """,
        (
            session.build_session_id,
            session.state.value,
            session.created_at,
            session.updated_at,
            session.ttl_expires_at,
            _model_jsonb(session),
        ),
    )


def _model_jsonb(model: BaseModel) -> Jsonb:
    return Jsonb(model.model_dump(mode="json"))


def _model_from_payload(model_class: type[ModelT], payload: Any) -> ModelT:
    if isinstance(payload, str):
        return model_class.model_validate_json(payload)
    return model_class.model_validate(payload)

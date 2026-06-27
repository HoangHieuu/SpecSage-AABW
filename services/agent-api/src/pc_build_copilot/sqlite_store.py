from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from pc_build_copilot.build_models import (
    BuildApproval,
    BuildArtifact,
    BuildStatus,
    CartReadyHandoff,
)
from pc_build_copilot.build_store import BuildStore
from pc_build_copilot.models import BuildSession, IntentRevision, SessionState
from pc_build_copilot.store import SessionStore


DB_PATH_ENV = "PC_BUILD_COPILOT_DB_PATH"
DEFAULT_DB_PATH = Path(".local") / "pc-build-copilot.sqlite3"


def create_sqlite_stores(
    db_path: str | os.PathLike[str] | None = None,
) -> tuple[SqliteSessionStore, SqliteBuildStore]:
    path = _resolve_db_path(db_path)
    return SqliteSessionStore(path), SqliteBuildStore(path)


class SqliteSessionStore(SessionStore):
    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self.db_path = Path(db_path)
        _ensure_schema(self.db_path)

    def create(self, session: BuildSession) -> BuildSession:
        with _connect(self.db_path) as conn:
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
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.build_session_id,
                    session.state.value,
                    _iso(session.created_at),
                    _iso(session.updated_at),
                    _iso(session.ttl_expires_at),
                    _model_json(session),
                ),
            )
        return session

    def get(self, build_session_id: str) -> BuildSession:
        with _connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM build_sessions WHERE build_session_id = ?",
                (build_session_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="build_session_id not found")
        return BuildSession.model_validate_json(row["payload_json"])

    def add_revision(self, revision: IntentRevision) -> IntentRevision:
        with _connect(self.db_path) as conn:
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
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.build_session_id,
                    _iso(revision.created_at),
                    int(revision.confirmed),
                    _model_json(revision),
                ),
            )
        return revision

    def revisions(self, build_session_id: str) -> list[IntentRevision]:
        with _connect(self.db_path) as conn:
            _get_session(conn, build_session_id)
            rows = conn.execute(
                """
                SELECT payload_json
                FROM intent_revisions
                WHERE build_session_id = ?
                ORDER BY sequence_id ASC
                """,
                (build_session_id,),
            ).fetchall()
        return [IntentRevision.model_validate_json(row["payload_json"]) for row in rows]

    def latest_confirmed_revision(self, build_session_id: str) -> IntentRevision:
        with _connect(self.db_path) as conn:
            _get_session(conn, build_session_id)
            row = conn.execute(
                """
                SELECT payload_json
                FROM intent_revisions
                WHERE build_session_id = ? AND confirmed = 1
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
        return IntentRevision.model_validate_json(row["payload_json"])

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
        with _connect(self.db_path) as conn:
            session = _get_session(conn, build_session_id)
            session = session.model_copy(
                update={"state": state, "updated_at": datetime.now(UTC)}
            )
            _upsert_session(conn, session)
        return session


class SqliteBuildStore(BuildStore):
    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self.db_path = Path(db_path)
        _ensure_schema(self.db_path)

    def save(self, artifact: BuildArtifact) -> BuildArtifact:
        with _connect(self.db_path) as conn:
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
                VALUES (?, ?, ?, ?, ?, ?)
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
                    _iso(artifact.generated_at),
                    artifact.status.value,
                    _model_json(artifact),
                ),
            )
        return artifact

    def get(self, build_id: str) -> BuildArtifact:
        with _connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM build_artifacts WHERE build_id = ?",
                (build_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="build_id not found")
        return BuildArtifact.model_validate_json(row["payload_json"])

    def list_for_session(self, build_session_id: str) -> list[BuildArtifact]:
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM build_artifacts
                WHERE build_session_id = ?
                ORDER BY build_version ASC, generated_at ASC
                """,
                (build_session_id,),
            ).fetchall()
        return [BuildArtifact.model_validate_json(row["payload_json"]) for row in rows]

    def approve(self, build_id: str) -> CartReadyHandoff:
        artifact = self.get(build_id)
        with _connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT payload_json FROM cart_handoffs WHERE build_id = ?",
                (build_id,),
            ).fetchone()
            if existing is not None:
                return CartReadyHandoff.model_validate_json(existing["payload_json"])

            if artifact.status != BuildStatus.GENERATED or not artifact.can_approve:
                raise HTTPException(
                    status_code=409,
                    detail="build must be compatible and within budget before approval",
                )

            approval = BuildApproval(
                build_id=artifact.build_id,
                build_session_id=artifact.build_session_id,
                selected_skus={item.slot.value: item.sku for item in artifact.items},
                total_price_vnd=artifact.total_price_vnd,
                catalog_version=artifact.catalog_version,
                rules_version=artifact.rules_version,
            )
            handoff = CartReadyHandoff(
                build_id=artifact.build_id,
                build_session_id=artifact.build_session_id,
                approval=approval,
                total_price_vnd=artifact.total_price_vnd,
                item_count=len(artifact.items),
                mock_cart_payload=artifact.mock_cart_payload,
                warnings_vi=[
                    *artifact.warnings_vi,
                    "Mock cart: mở từng link sản phẩm Phong Vu để thêm vào giỏ.",
                ],
            )
            conn.execute(
                """
                INSERT INTO cart_handoffs (
                    handoff_id,
                    build_id,
                    build_session_id,
                    created_at,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    handoff.handoff_id,
                    handoff.build_id,
                    handoff.build_session_id,
                    _iso(handoff.created_at),
                    _model_json(handoff),
                ),
            )
        return handoff


def _resolve_db_path(db_path: str | os.PathLike[str] | None) -> Path:
    value = db_path or os.environ.get(DB_PATH_ENV) or DEFAULT_DB_PATH
    return Path(value).expanduser()


def _ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS build_sessions (
                build_session_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ttl_expires_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intent_revisions (
                sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                revision_id TEXT NOT NULL UNIQUE,
                build_session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                confirmed INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_intent_revisions_session
                ON intent_revisions(build_session_id, sequence_id);

            CREATE TABLE IF NOT EXISTS build_artifacts (
                build_id TEXT PRIMARY KEY,
                build_session_id TEXT NOT NULL,
                build_version INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_build_artifacts_session
                ON build_artifacts(build_session_id, build_version);

            CREATE TABLE IF NOT EXISTS cart_handoffs (
                handoff_id TEXT PRIMARY KEY,
                build_id TEXT NOT NULL UNIQUE,
                build_session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cart_handoffs_session
                ON cart_handoffs(build_session_id);
            """
        )


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_session(conn: sqlite3.Connection, build_session_id: str) -> BuildSession:
    row = conn.execute(
        "SELECT payload_json FROM build_sessions WHERE build_session_id = ?",
        (build_session_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="build_session_id not found")
    return BuildSession.model_validate_json(row["payload_json"])


def _upsert_session(conn: sqlite3.Connection, session: BuildSession) -> None:
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
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(build_session_id) DO UPDATE SET
            state = excluded.state,
            updated_at = excluded.updated_at,
            ttl_expires_at = excluded.ttl_expires_at,
            payload_json = excluded.payload_json
        """,
        (
            session.build_session_id,
            session.state.value,
            _iso(session.created_at),
            _iso(session.updated_at),
            _iso(session.ttl_expires_at),
            _model_json(session),
        ),
    )


def _model_json(model: BaseModel) -> str:
    return model.model_dump_json()


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)

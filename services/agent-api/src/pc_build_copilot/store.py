from datetime import UTC, datetime

from fastapi import HTTPException

from pc_build_copilot.models import BuildSession, IntentRevision, SessionState


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, BuildSession] = {}
        self._revisions: dict[str, list[IntentRevision]] = {}

    def create(self, session: BuildSession) -> BuildSession:
        self._sessions[session.build_session_id] = session
        self._revisions[session.build_session_id] = []
        return session

    def get(self, build_session_id: str) -> BuildSession:
        session = self._sessions.get(build_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="build_session_id not found")
        return session

    def add_revision(self, revision: IntentRevision) -> IntentRevision:
        session = self.get(revision.build_session_id)
        session.state = (
            SessionState.INTENT_CONFIRMED if revision.confirmed else SessionState.INTENT_DRAFT
        )
        session.updated_at = datetime.now(UTC)
        self._sessions[session.build_session_id] = session
        self._revisions[session.build_session_id].append(revision)
        return revision

    def revisions(self, build_session_id: str) -> list[IntentRevision]:
        self.get(build_session_id)
        return list(self._revisions[build_session_id])

    def latest_confirmed_revision(self, build_session_id: str) -> IntentRevision:
        self.get(build_session_id)
        for revision in reversed(self._revisions[build_session_id]):
            if revision.confirmed:
                return revision
        raise HTTPException(status_code=409, detail="intent must be confirmed before generation")

    def mark_generated(self, build_session_id: str) -> BuildSession:
        session = self.get(build_session_id)
        session.state = SessionState.GENERATED
        session.updated_at = datetime.now(UTC)
        self._sessions[build_session_id] = session
        return session

    def mark_reviewing(self, build_session_id: str) -> BuildSession:
        session = self.get(build_session_id)
        session.state = SessionState.REVIEWING
        session.updated_at = datetime.now(UTC)
        self._sessions[build_session_id] = session
        return session

    def mark_approved(self, build_session_id: str) -> BuildSession:
        session = self.get(build_session_id)
        session.state = SessionState.APPROVED
        session.updated_at = datetime.now(UTC)
        self._sessions[build_session_id] = session
        return session

    def mark_cart_ready(self, build_session_id: str) -> BuildSession:
        session = self.get(build_session_id)
        session.state = SessionState.CART_READY
        session.updated_at = datetime.now(UTC)
        self._sessions[build_session_id] = session
        return session

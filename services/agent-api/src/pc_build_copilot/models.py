from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Channel(str, Enum):
    WEB = "web"
    STAFF = "staff"
    API = "api"


class SessionState(str, Enum):
    CREATED = "created"
    INTENT_DRAFT = "intent_draft"
    INTENT_CONFIRMED = "intent_confirmed"
    GENERATED = "generated"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    CART_READY = "cart_ready"


class UseCase(str, Enum):
    GAMING = "gaming"
    CREATOR = "creator"
    OFFICE = "office"
    STUDENT = "student"
    AI = "ai"
    STREAMING = "streaming"
    COMPACT = "compact"
    UNKNOWN = "unknown"


class BuildSessionCreate(BaseModel):
    locale: str = "vi-VN"
    channel: Channel = Channel.WEB


class BuildSession(BaseModel):
    build_session_id: str = Field(default_factory=lambda: f"bs_{uuid4().hex}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl_expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + timedelta(hours=24)
    )
    locale: str = "vi-VN"
    channel: Channel = Channel.WEB
    state: SessionState = SessionState.CREATED


class BuildIntent(BaseModel):
    raw_text: str
    use_case: UseCase = UseCase.UNKNOWN
    budget_min: int | None = None
    budget_max: int | None = None
    budget_interpretation: str | None = None
    target_games: list[str] = Field(default_factory=list)
    target_apps: list[str] = Field(default_factory=list)
    performance_targets: list[str] = Field(default_factory=list)
    form_factor: str | None = None
    brand_preferences: list[str] = Field(default_factory=list)
    noise_preferences: str | None = None
    aesthetic_preferences: str | None = None
    mentioned_components: list[str] = Field(default_factory=list)
    safe_defaults: list[str] = Field(default_factory=list)


class IntentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    confirm: bool = False
    preset: UseCase | None = None


class Clarification(BaseModel):
    field: Literal["budget", "use_case", "target_games", "target_apps"] | None = None
    question: str | None = None
    required: bool = False


class IntentRevision(BaseModel):
    revision_id: str = Field(default_factory=lambda: f"ir_{uuid4().hex}")
    build_session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    intent: BuildIntent
    clarification: Clarification
    confirmed: bool = False


class IntentResponse(BaseModel):
    session: BuildSession
    revision: IntentRevision

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from pc_build_copilot.catalog_models import ComponentCategory, SpecsConfidence
from pc_build_copilot.compatibility_models import (
    BuildSlot,
    CompatibilityReport,
)
from pc_build_copilot.models import BuildIntent


class BudgetStatus(str, Enum):
    WITHIN_BUDGET = "within_budget"
    OVER_BUDGET = "over_budget"
    UNKNOWN_BUDGET = "unknown_budget"


class BuildStatus(str, Enum):
    GENERATED = "generated"
    OVER_BUDGET = "over_budget"
    BLOCKED = "blocked"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"


class CartHandoffStatus(str, Enum):
    CART_READY = "cart_ready"


class PerformanceFitLevel(str, Enum):
    GOOD = "good"
    ADEQUATE = "adequate"
    LIMITED = "limited"
    UNKNOWN = "unknown"


class PerformanceConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PerformanceEvidence(BaseModel):
    label: str
    value: str
    source: Literal["catalog_spec", "intent", "rule"]


class PerformanceProfile(BaseModel):
    use_case: str
    fit_level: PerformanceFitLevel
    confidence: PerformanceConfidence
    summary_vi: str
    fit_notes_vi: list[str] = Field(default_factory=list)
    bottleneck_notes_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)
    evidence: list[PerformanceEvidence] = Field(default_factory=list)


class BuildItem(BaseModel):
    slot: BuildSlot
    sku: str
    name: str
    category: ComponentCategory
    price_vnd: int
    url: str
    brand: str | None = None
    specs_confidence: SpecsConfidence
    explanation_vi: str


class MockCartPayload(BaseModel):
    provider: str = "mock_phongvu_link_list"
    disclaimer_vi: str = "Mock cart: mở từng link sản phẩm Phong Vu để thêm vào giỏ."
    items: list[dict[str, str]]


class BuildArtifact(BaseModel):
    build_id: str = Field(default_factory=lambda: f"build_{uuid4().hex}")
    build_session_id: str
    build_version: int = 1
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    intent_snapshot: BuildIntent
    catalog_version: str
    rules_version: str
    total_price_vnd: int
    budget_max_vnd: int | None = None
    budget_gap_vnd: int = 0
    budget_status: BudgetStatus
    status: BuildStatus
    can_approve: bool
    items: list[BuildItem]
    compatibility_report: CompatibilityReport
    performance_profile: PerformanceProfile
    explanations_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)
    mock_cart_payload: MockCartPayload


class BuildApproval(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"appr_{uuid4().hex}")
    build_id: str
    build_session_id: str
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ApprovalStatus = ApprovalStatus.APPROVED
    selected_skus: dict[str, str]
    total_price_vnd: int
    catalog_version: str
    rules_version: str
    disclaimer_vi: str = (
        "Đã duyệt cấu hình từ snapshot nội bộ; giá và tồn kho cần kiểm tra lại trên Phong Vu."
    )


class CartReadyHandoff(BaseModel):
    handoff_id: str = Field(default_factory=lambda: f"cart_{uuid4().hex}")
    build_id: str
    build_session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: CartHandoffStatus = CartHandoffStatus.CART_READY
    approval: BuildApproval
    total_price_vnd: int
    item_count: int
    mock_cart_payload: MockCartPayload
    warnings_vi: list[str] = Field(default_factory=list)

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from pc_build_copilot.catalog_models import ComponentCategory, SpecsConfidence, StockStatus
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


class BuildFeedbackRating(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class BuildFeedbackReason(str, Enum):
    FITS_NEED = "fits_need"
    GOOD_VALUE = "good_value"
    CLEAR_EXPLANATION = "clear_explanation"
    CONFUSING_EXPLANATION = "confusing_explanation"
    OVER_BUDGET = "over_budget"
    MISSING_PART = "missing_part"
    WRONG_PERFORMANCE_FIT = "wrong_performance_fit"
    COMPATIBILITY_CONCERN = "compatibility_concern"
    PRICE_OR_STOCK_CONCERN = "price_or_stock_concern"
    OTHER = "other"


class BuildFeedbackReviewStatus(str, Enum):
    NOT_QUEUED = "not_queued"
    QUEUED = "queued"


class OrchestrationAgent(str, Enum):
    INTENT = "intent"
    CATALOG = "catalog"
    OPTIMIZER = "optimizer"
    COMPATIBILITY = "compatibility"
    PERFORMANCE = "performance"
    EXPLAINER = "explainer"
    COMMERCE = "commerce"
    VALIDATOR = "validator"


class OrchestrationStepStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BuildAlternativeKind(str, Enum):
    RAM_UPGRADE = "ram_upgrade"
    STORAGE_UPGRADE = "storage_upgrade"
    NVIDIA_GPU = "nvidia_gpu"
    PSU_HEADROOM = "psu_headroom"
    BUDGET_SAVER = "budget_saver"


class BuildAddOnKind(str, Enum):
    MONITOR = "monitor"
    COOLER = "cooler"


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
    source: Literal["catalog_spec", "intent", "rule", "benchmark"]
    source_label: str | None = None
    source_url: str | None = None


class PerformanceBalance(BaseModel):
    score: int = Field(ge=0, le=100)
    interpretation_vi: str
    limiting_component: Literal["cpu", "gpu", "ram", "storage", "unknown"]
    suggestions_vi: list[str] = Field(default_factory=list)
    factors: dict[str, int] = Field(default_factory=dict)


class PerformanceWorkloadProfile(BaseModel):
    name: str
    category: Literal["video_editing", "three_d", "photo_editing", "streaming", "local_llm"]
    fit_level: PerformanceFitLevel
    bottlenecks: list[
        Literal[
            "cpu_bound",
            "gpu_bound",
            "ram_limited",
            "storage_limited",
            "vram_limited",
            "cuda_preferred",
        ]
    ] = Field(default_factory=list)
    requirement_summary_vi: str
    recommendation_vi: str


class PerformanceProfile(BaseModel):
    use_case: str
    fit_level: PerformanceFitLevel
    confidence: PerformanceConfidence
    summary_vi: str
    fit_notes_vi: list[str] = Field(default_factory=list)
    bottleneck_notes_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)
    evidence: list[PerformanceEvidence] = Field(default_factory=list)
    balance: PerformanceBalance | None = None
    workload_profiles: list[PerformanceWorkloadProfile] = Field(default_factory=list)


class BuildItem(BaseModel):
    slot: BuildSlot
    sku: str
    name: str
    category: ComponentCategory
    price_vnd: int
    url: str
    image_url: str | None = None
    brand: str | None = None
    warranty_text: str | None = None
    stock_status: StockStatus = StockStatus.UNKNOWN
    stock_quantity: int = Field(default=0, ge=0)
    specs_confidence: SpecsConfidence
    explanation_vi: str


class BuildRecommendedAddOn(BaseModel):
    kind: BuildAddOnKind
    sku: str
    name: str
    category: ComponentCategory
    price_vnd: int
    url: str
    image_url: str | None = None
    brand: str | None = None
    warranty_text: str | None = None
    stock_status: StockStatus = StockStatus.UNKNOWN
    stock_quantity: int = Field(default=0, ge=0)
    specs_confidence: SpecsConfidence
    reason_vi: str
    fit_notes_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)
    optional: bool = True


class MockCartPayload(BaseModel):
    provider: str = "mock_phongvu_link_list"
    disclaimer_vi: str = "Mock cart: mở từng link sản phẩm Phong Vu để thêm vào giỏ."
    items: list[dict[str, str]]


class BuildOrchestrationStep(BaseModel):
    agent: OrchestrationAgent
    status: OrchestrationStepStatus = OrchestrationStepStatus.COMPLETED
    summary_vi: str
    inputs: dict[str, str | int | bool | None] = Field(default_factory=dict)
    outputs: dict[str, str | int | bool | None] = Field(default_factory=dict)
    tool_calls: list[str] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    model_version: str = "deterministic-local-v1"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OptimizerBudgetAllocation(BaseModel):
    use_case: str
    budget_max_vnd: int | None = None
    weights: dict[str, int] = Field(default_factory=dict)
    target_amounts_vnd: dict[str, int] = Field(default_factory=dict)
    reserved_peripherals_vnd: int = Field(default=0, ge=0)
    reserved_services_vnd: int = Field(default=0, ge=0)
    notes_vi: list[str] = Field(default_factory=list)


class OptimizerIterationDecision(BaseModel):
    iteration: int = Field(ge=0)
    candidate_kind: str | None = None
    candidate_label_vi: str | None = None
    decision: Literal["accepted", "rejected", "skipped"]
    score: int | None = Field(default=None, ge=0, le=100)
    priority: str | None = None
    price_delta_vnd: int | None = None
    total_price_vnd: int | None = None
    changed_slots: list[str] = Field(default_factory=list)
    reason_vi: str


class OptimizerTrace(BaseModel):
    max_iterations: int = Field(ge=0)
    applied_iteration_count: int = Field(default=0, ge=0)
    rejected_iteration_count: int = Field(default=0, ge=0)
    priority_overrides: list[str] = Field(default_factory=list)
    budget_allocation: OptimizerBudgetAllocation
    iterations: list[OptimizerIterationDecision] = Field(default_factory=list)


class TraceReplayEvent(BaseModel):
    event_id: str
    sequence: int
    build_session_id: str
    build_id: str
    build_version: int
    generated_at: datetime
    agent: OrchestrationAgent
    status: OrchestrationStepStatus
    summary_vi: str
    inputs_redacted: dict[str, str | int | bool | None] = Field(default_factory=dict)
    tool_calls: list[str] = Field(default_factory=list)
    outputs_redacted: dict[str, str | int | bool | None] = Field(default_factory=dict)
    latency_ms: int = Field(default=0, ge=0)
    model_version: str = "deterministic-local-v1"


class BuildTraceReplay(BaseModel):
    build_session_id: str
    build_id: str
    build_version: int
    generated_at: datetime
    replay_status: Literal["complete", "empty"]
    events: list[TraceReplayEvent] = Field(default_factory=list)


class SessionTraceReplay(BaseModel):
    build_session_id: str
    generated_build_count: int
    redaction_policy_vi: str
    support_export_text: str
    builds: list[BuildTraceReplay] = Field(default_factory=list)


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
    optimizer_trace: OptimizerTrace | None = None
    recommended_addons: list[BuildRecommendedAddOn] = Field(default_factory=list)
    explanations_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)
    orchestration_trace: list[BuildOrchestrationStep] = Field(default_factory=list)
    mock_cart_payload: MockCartPayload


class BuildAlternativeChangedSlot(BaseModel):
    slot: BuildSlot
    current_sku: str
    current_name: str
    candidate_sku: str
    candidate_name: str
    price_delta_vnd: int
    reason_vi: str


class BuildAlternativeRanking(BaseModel):
    rank: int = Field(default=0, ge=0)
    score: int = Field(default=0, ge=0, le=100)
    priority: Literal["recommended", "good_fit", "situational", "low_priority"] = "low_priority"
    reasons_vi: list[str] = Field(default_factory=list)


class BuildAlternative(BaseModel):
    variant_id: str
    kind: BuildAlternativeKind
    label_vi: str
    summary_vi: str
    ranking: BuildAlternativeRanking = Field(default_factory=BuildAlternativeRanking)
    total_price_vnd: int
    price_delta_vnd: int
    budget_status: BudgetStatus
    budget_gap_vnd: int
    status: BuildStatus
    can_approve: bool
    items: list[BuildItem]
    changed_slots: list[BuildAlternativeChangedSlot]
    compatibility_report: CompatibilityReport
    performance_profile: PerformanceProfile
    explanations_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)


class BuildAlternativesResponse(BaseModel):
    build_id: str
    build_session_id: str
    catalog_version: str
    rules_version: str
    base_total_price_vnd: int
    alternatives: list[BuildAlternative] = Field(default_factory=list)


class BuildIterationRequest(BaseModel):
    command_vi: str = Field(min_length=2, max_length=300)


class ParsedBuildIterationCommand(BaseModel):
    command_vi: str
    command_type: Literal[
        "cheaper",
        "quieter",
        "more_performance",
        "more_storage",
        "more_memory",
        "nvidia_gpu",
        "unknown",
    ]
    target_budget_max_vnd: int | None = None
    priority_label_vi: str
    summary_vi: str


class BuildIterationResponse(BaseModel):
    source_build_id: str
    source_build_version: int
    command: ParsedBuildIterationCommand
    selected_alternative: BuildAlternative
    applied_build: BuildArtifact
    rejected_candidates: list[OptimizerIterationDecision] = Field(default_factory=list)


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


class BuildApprovalRequest(BaseModel):
    selected_addon_skus: list[str] = Field(default_factory=list, max_length=8)


class CartReadyHandoff(BaseModel):
    handoff_id: str = Field(default_factory=lambda: f"cart_{uuid4().hex}")
    build_id: str
    build_session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: CartHandoffStatus = CartHandoffStatus.CART_READY
    approval: BuildApproval
    total_price_vnd: int
    add_on_total_price_vnd: int = 0
    shopping_list_total_price_vnd: int = 0
    item_count: int
    selected_addons: list[BuildRecommendedAddOn] = Field(default_factory=list)
    mock_cart_payload: MockCartPayload
    warnings_vi: list[str] = Field(default_factory=list)


class PartFeedbackRequest(BaseModel):
    slot: BuildSlot
    sku: str
    rating: BuildFeedbackRating
    reason_tags: list[BuildFeedbackReason] = Field(default_factory=list, max_length=5)
    comment_vi: str | None = Field(default=None, max_length=500)


class BuildFeedbackRequest(BaseModel):
    rating: BuildFeedbackRating
    reason_tags: list[BuildFeedbackReason] = Field(default_factory=list, max_length=5)
    comment_vi: str | None = Field(default=None, max_length=1000)
    part_feedback: list[PartFeedbackRequest] = Field(default_factory=list, max_length=8)


class PartFeedback(BaseModel):
    slot: BuildSlot
    sku: str
    name: str
    rating: BuildFeedbackRating
    reason_tags: list[BuildFeedbackReason] = Field(default_factory=list)
    comment_vi: str | None = None


class BuildFeedback(BaseModel):
    feedback_id: str = Field(default_factory=lambda: f"fb_{uuid4().hex}")
    build_id: str
    build_session_id: str
    build_version: int
    catalog_version: str
    rules_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    rating: BuildFeedbackRating
    reason_tags: list[BuildFeedbackReason] = Field(default_factory=list)
    comment_vi: str | None = None
    part_feedback: list[PartFeedback] = Field(default_factory=list)
    review_queue_status: BuildFeedbackReviewStatus = BuildFeedbackReviewStatus.NOT_QUEUED
    review_queue_reason_vi: str | None = None

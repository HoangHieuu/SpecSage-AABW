from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from pc_build_copilot.catalog_models import ComponentCategory, SpecsConfidence
from pc_build_copilot.compatibility_models import BuildSlot, RULES_VERSION
from pc_build_copilot.models import UseCase


class UpgradeDecision(str, Enum):
    REUSE = "reuse"
    REPLACE = "replace"
    OPTIONAL_UPGRADE = "optional_upgrade"
    UNKNOWN = "unknown"


class UpgradeImpact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UpgradeCheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class ExistingSystemParseRequest(BaseModel):
    current_pc: str = Field(min_length=3, max_length=4000)


class ExistingSystemOverrides(BaseModel):
    cpu_name: str | None = Field(default=None, max_length=80)
    mainboard_name: str | None = Field(default=None, max_length=80)
    ram_gb: int | None = Field(default=None, ge=0)
    gpu_name: str | None = Field(default=None, max_length=80)
    psu_wattage_w: int | None = Field(default=None, ge=0)
    psu_pcie_8pin_connectors: int | None = Field(default=None, ge=0)
    case_gpu_clearance_mm: int | None = Field(default=None, ge=0)
    storage_summary: str | None = Field(default=None, max_length=120)


class UpgradePlanRequest(BaseModel):
    current_pc: str = Field(min_length=3, max_length=4000)
    target_use_case: UseCase = UseCase.GAMING
    upgrade_budget_max_vnd: int | None = Field(default=None, ge=0)
    target_resolution: str | None = Field(default=None, max_length=40)
    target_refresh_hz: int | None = Field(default=None, ge=30, le=500)
    confirmed_existing_system: ExistingSystemOverrides | None = None


class ExistingSystemSpec(BaseModel):
    raw_text: str
    cpu_name: str | None = None
    cpu_tdp_w: int | None = None
    mainboard_name: str | None = None
    ram_gb: int | None = Field(default=None, ge=0)
    gpu_name: str | None = None
    gpu_tier_score: int | None = Field(default=None, ge=0, le=100)
    psu_wattage_w: int | None = Field(default=None, ge=0)
    psu_pcie_8pin_connectors: int | None = Field(default=None, ge=0)
    case_name: str | None = None
    case_gpu_clearance_mm: int | None = Field(default=None, ge=0)
    storage_summary: str | None = None
    unknown_fields: list[str] = Field(default_factory=list)


class ExistingSystemParseResponse(BaseModel):
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    existing_system: ExistingSystemSpec
    confirmation_required: bool = True
    summary_vi: str
    warnings_vi: list[str] = Field(default_factory=list)
    next_steps_vi: list[str] = Field(default_factory=list)


class ExistingPartDecision(BaseModel):
    slot: BuildSlot
    decision: UpgradeDecision
    reason_vi: str


class UpgradeCompatibilityCheck(BaseModel):
    code: str
    status: UpgradeCheckStatus
    explanation_vi: str
    facts: dict[str, int | str | None] = Field(default_factory=dict)


class UpgradeRecommendation(BaseModel):
    slot: Literal[BuildSlot.VGA] = BuildSlot.VGA
    sku: str
    name: str
    category: ComponentCategory
    price_vnd: int
    url: str
    brand: str | None = None
    specs_confidence: SpecsConfidence
    impact: UpgradeImpact
    replaced_component: str | None = None
    compatibility_status: UpgradeCheckStatus
    checks: list[UpgradeCompatibilityCheck] = Field(default_factory=list)
    reasons_vi: list[str] = Field(default_factory=list)
    warnings_vi: list[str] = Field(default_factory=list)


class UpgradePlanResponse(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"upg_{uuid4().hex}")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    catalog_version: str
    rules_version: str = RULES_VERSION
    request: UpgradePlanRequest
    existing_system: ExistingSystemSpec
    recommendations: list[UpgradeRecommendation] = Field(default_factory=list)
    reuse_decisions: list[ExistingPartDecision] = Field(default_factory=list)
    total_upgrade_cost_vnd: int = Field(default=0, ge=0)
    warnings_vi: list[str] = Field(default_factory=list)
    next_steps_vi: list[str] = Field(default_factory=list)

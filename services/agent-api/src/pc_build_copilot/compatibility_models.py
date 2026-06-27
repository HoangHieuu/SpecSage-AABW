from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from pc_build_copilot.catalog_models import ComponentCategory


RULES_VERSION = "compat_rules_v2026_06_27"


class BuildSlot(str, Enum):
    CPU = "cpu"
    MAINBOARD = "mainboard"
    RAM = "ram"
    STORAGE = "storage"
    VGA = "vga"
    PSU = "psu"
    CASE = "case"
    COOLER = "cooler"


SLOT_TO_CATEGORY: dict[BuildSlot, ComponentCategory] = {
    BuildSlot.CPU: ComponentCategory.CPU,
    BuildSlot.MAINBOARD: ComponentCategory.MAINBOARD,
    BuildSlot.RAM: ComponentCategory.RAM,
    BuildSlot.STORAGE: ComponentCategory.STORAGE,
    BuildSlot.VGA: ComponentCategory.VGA,
    BuildSlot.PSU: ComponentCategory.PSU,
    BuildSlot.CASE: ComponentCategory.CASE,
    BuildSlot.COOLER: ComponentCategory.COOLER,
}


class CompatibilitySeverity(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class CompatibilityStatus(str, Enum):
    APPROVED = "approved"
    WARNING = "warning"
    BLOCKED = "blocked"


class BuildValidationRequest(BaseModel):
    selected_skus: dict[BuildSlot, str] = Field(default_factory=dict)


class CompatibilityResult(BaseModel):
    rule_id: str
    severity: CompatibilitySeverity
    slots: list[BuildSlot] = Field(default_factory=list)
    skus: list[str] = Field(default_factory=list)
    explanation_key: str
    explanation_vi: str
    remediation_vi: str | None = None
    facts: dict[str, Any] = Field(default_factory=dict)


class CompatibilityReport(BaseModel):
    build_id: str
    rules_version: str = RULES_VERSION
    catalog_version: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: CompatibilityStatus
    max_severity: CompatibilitySeverity
    can_approve: bool
    selected_skus: dict[BuildSlot, str]
    results: list[CompatibilityResult]


def report_status(results: list[CompatibilityResult]) -> tuple[
    CompatibilityStatus, CompatibilitySeverity, bool
]:
    if any(result.severity == CompatibilitySeverity.BLOCK for result in results):
        return (
            CompatibilityStatus.BLOCKED,
            CompatibilitySeverity.BLOCK,
            False,
        )
    if any(result.severity == CompatibilitySeverity.WARN for result in results):
        return (
            CompatibilityStatus.WARNING,
            CompatibilitySeverity.WARN,
            True,
        )
    return (
        CompatibilityStatus.APPROVED,
        CompatibilitySeverity.PASS,
        True,
    )


RequiredSlotPolicy = Literal["full_build"]


REQUIRED_FULL_BUILD_SLOTS: tuple[BuildSlot, ...] = (
    BuildSlot.CPU,
    BuildSlot.MAINBOARD,
    BuildSlot.RAM,
    BuildSlot.STORAGE,
    BuildSlot.PSU,
    BuildSlot.CASE,
)

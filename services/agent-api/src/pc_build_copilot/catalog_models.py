from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ComponentCategory(str, Enum):
    CPU = "cpu"
    MAINBOARD = "mainboard"
    RAM = "ram"
    VGA = "vga"
    STORAGE = "storage"
    PSU = "psu"
    CASE = "case"
    COOLER = "cooler"
    MONITOR = "monitor"
    UNKNOWN = "unknown"


class SpecsConfidence(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    INFERRED = "inferred"


class StockStatus(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class CatalogSku(BaseModel):
    sku: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: ComponentCategory
    price_vnd: int = Field(ge=0)
    list_price_vnd: int | None = Field(default=None, ge=0)
    discount_amount_vnd: int | None = Field(default=None, ge=0)
    stock_quantity: int = Field(ge=0)
    stock_status: StockStatus = StockStatus.UNKNOWN
    url: str = Field(min_length=1)
    image_url: str | None = None
    brand: str | None = None
    warranty_text: str | None = None
    highlights: list[str] = Field(default_factory=list)
    specs: dict[str, Any] = Field(default_factory=dict)
    specs_confidence: SpecsConfidence = SpecsConfidence.PARTIAL
    catalog_snapshot_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = "phongvu_next_data_fixture"
    raw_category: str | None = None


class CatalogIssue(BaseModel):
    severity: Literal["block", "warn"]
    code: str
    sku: str | None = None
    field: str | None = None
    message: str


class CatalogValidationReport(BaseModel):
    snapshot_version: str
    generated_at: datetime
    sku_count: int
    issue_count: int
    blocking_issue_count: int
    category_counts: dict[ComponentCategory, int] = Field(default_factory=dict)
    recommended_demo_category_counts: dict[ComponentCategory, int] = Field(
        default_factory=dict
    )
    required_demo_categories: list[ComponentCategory] = Field(default_factory=list)
    missing_required_demo_categories: list[ComponentCategory] = Field(default_factory=list)
    thin_demo_categories: list[ComponentCategory] = Field(default_factory=list)
    demo_ready: bool = False
    issues: list[CatalogIssue] = Field(default_factory=list)


class CatalogSnapshot(BaseModel):
    snapshot_version: str
    generated_at: datetime
    source: str
    items: list[CatalogSku]
    validation: CatalogValidationReport | None = None


class CatalogQueryResponse(BaseModel):
    snapshot_version: str
    catalog_snapshot_at: datetime
    sku_count: int
    items: list[CatalogSku]

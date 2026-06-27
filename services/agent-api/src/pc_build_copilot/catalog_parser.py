from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pc_build_copilot.catalog_models import (
    CatalogSku,
    ComponentCategory,
    SpecsConfidence,
    StockStatus,
)


class CatalogParseError(ValueError):
    pass


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_next_data = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attr_map = dict(attrs)
        self._inside_next_data = attr_map.get("id") == "__NEXT_DATA__"

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside_next_data = False

    def handle_data(self, data: str) -> None:
        if self._inside_next_data:
            self.parts.append(data)


CATEGORY_ALIASES = {
    "cpu": ComponentCategory.CPU,
    "cpu-intel": ComponentCategory.CPU,
    "cpu-amd": ComponentCategory.CPU,
    "mainboard": ComponentCategory.MAINBOARD,
    "mainboard-bo-mach-chu": ComponentCategory.MAINBOARD,
    "bo-mach-chu": ComponentCategory.MAINBOARD,
    "ram": ComponentCategory.RAM,
    "ram-pc": ComponentCategory.RAM,
    "vga": ComponentCategory.VGA,
    "vga-card-man-hinh": ComponentCategory.VGA,
    "o-cung-ssd": ComponentCategory.STORAGE,
    "ssd": ComponentCategory.STORAGE,
    "storage": ComponentCategory.STORAGE,
    "psu": ComponentCategory.PSU,
    "psu-nguon-may-tinh": ComponentCategory.PSU,
    "nguon-may-tinh": ComponentCategory.PSU,
    "case": ComponentCategory.CASE,
    "case-thung-may-tinh": ComponentCategory.CASE,
    "tan-nhiet-pc": ComponentCategory.COOLER,
    "cooler": ComponentCategory.COOLER,
    "man-hinh-may-tinh": ComponentCategory.MONITOR,
    "monitor": ComponentCategory.MONITOR,
}


def extract_next_data_json(html: str) -> dict[str, Any]:
    parser = _NextDataParser()
    parser.feed(html)
    raw_json = "".join(parser.parts).strip()
    if not raw_json:
        raise CatalogParseError("Could not find __NEXT_DATA__ script payload.")
    try:
        loaded = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise CatalogParseError(f"Invalid __NEXT_DATA__ JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise CatalogParseError("__NEXT_DATA__ payload must be a JSON object.")
    return loaded


def parse_next_data_products(html: str) -> list[dict[str, Any]]:
    payload = extract_next_data_json(html)
    products = _find_products(payload)
    if not products:
        raise CatalogParseError("No serverProducts array found in __NEXT_DATA__ payload.")
    return products


def normalize_products(
    raw_products: list[dict[str, Any]],
    *,
    snapshot_at: datetime,
    category_hint: ComponentCategory | None = None,
    source_url: str | None = None,
    source: str = "phongvu_next_data_fixture",
) -> list[CatalogSku]:
    items: list[CatalogSku] = []
    for raw in raw_products:
        sku = _first_str(raw, "sku", "skuId", "productId", "product_id", "id")
        name = _first_str(raw, "name", "productName", "displayName")
        price = _first_int(raw, "latestPrice", "salePrice", "price", "finalPrice")
        if not sku or not name or price is None:
            raise CatalogParseError("Product is missing required sku, name, or price.")

        raw_category = _raw_category(raw)
        category = category_hint or category_from_slug(raw_category)
        highlights = _extract_highlights(raw)
        specs = infer_specs(category, name, highlights)
        stock_quantity = _stock_quantity(raw)
        url = _product_url(raw, sku, source_url)

        items.append(
            CatalogSku(
                sku=sku,
                name=name,
                category=category,
                price_vnd=price,
                list_price_vnd=_first_int(raw, "listPrice", "originalPrice", "marketPrice"),
                discount_amount_vnd=_first_int(raw, "discountAmount", "discount"),
                stock_quantity=stock_quantity,
                stock_status=_stock_status(raw, stock_quantity),
                url=url,
                image_url=_image_url(raw),
                brand=_brand(raw),
                warranty_text=_first_str(raw, "warranty", "warrantyText", "guarantee"),
                highlights=highlights,
                specs=specs,
                specs_confidence=SpecsConfidence.INFERRED if specs else SpecsConfidence.PARTIAL,
                catalog_snapshot_at=snapshot_at,
                source=source,
                raw_category=raw_category,
            )
        )
    return items


def load_overrides(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise CatalogParseError("Override file must contain a JSON object keyed by SKU.")
    return loaded


def apply_overrides(
    items: list[CatalogSku], overrides: dict[str, Any]
) -> list[CatalogSku]:
    enriched: list[CatalogSku] = []
    for item in items:
        override = overrides.get(item.sku, {})
        if not isinstance(override, dict):
            raise CatalogParseError(f"Override for SKU {item.sku} must be an object.")
        specs = dict(item.specs)
        specs.update(override.get("specs", {}))
        confidence = override.get("specs_confidence", item.specs_confidence)
        category = override.get("category", item.category)
        enriched.append(
            item.model_copy(
                update={
                    "category": ComponentCategory(category),
                    "specs": specs,
                    "specs_confidence": SpecsConfidence(confidence),
                }
            )
        )
    return enriched


def category_from_slug(raw_category: str | None) -> ComponentCategory:
    if not raw_category:
        return ComponentCategory.UNKNOWN
    normalized = raw_category.lower().strip().strip("/")
    return CATEGORY_ALIASES.get(normalized, ComponentCategory.UNKNOWN)


def infer_specs(
    category: ComponentCategory, name: str, highlights: list[str]
) -> dict[str, Any]:
    text = " ".join([name, *highlights])
    specs: dict[str, Any] = {}

    if category == ComponentCategory.VGA:
        if match := re.search(r"(\d+)\s*GB\s*(GDDR\d\w*)", text, re.IGNORECASE):
            specs["vram_gb"] = int(match.group(1))
            specs["memory_type"] = match.group(2).upper()
        if match := re.search(r"PCI[- ]?E\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE):
            specs["pcie"] = match.group(1)
        if match := re.search(r"\b(RTX\s*\d{4}\w*|RX\s*\d{4}\w*)\b", text, re.IGNORECASE):
            specs["chipset"] = re.sub(r"\s+", " ", match.group(1).upper())

    if category == ComponentCategory.CPU:
        if "LGA1700" in text.upper() or re.search(r"\b1700\b", text):
            specs["socket"] = "LGA1700"
        if match := re.search(r"(\d+)\s*(?:nhan|nhân|C)\D+(\d+)\s*(?:luong|luồng|T)", text, re.IGNORECASE):
            specs["cores"] = int(match.group(1))
            specs["threads"] = int(match.group(2))

    if category == ComponentCategory.RAM:
        if match := re.search(r"(\d+)\s*x\s*(\d+)\s*GB", text, re.IGNORECASE):
            specs["module_count"] = int(match.group(1))
            specs["capacity_gb"] = int(match.group(1)) * int(match.group(2))
        elif match := re.search(r"(\d+)\s*GB", text, re.IGNORECASE):
            specs["module_count"] = 1
            specs["capacity_gb"] = int(match.group(1))
        if match := re.search(r"DDR(\d)", text, re.IGNORECASE):
            specs["memory_type"] = f"DDR{match.group(1)}"
        if match := re.search(r"(\d{4,5})\s*MHz", text, re.IGNORECASE):
            specs["speed_mhz"] = int(match.group(1))

    if category == ComponentCategory.STORAGE:
        if match := re.search(r"(\d+)\s*(TB|GB)", text, re.IGNORECASE):
            value = int(match.group(1))
            specs["capacity_gb"] = value * 1024 if match.group(2).upper() == "TB" else value
        if "NVME" in text.upper():
            specs["interface"] = "NVMe"
        elif "SATA" in text.upper():
            specs["interface"] = "SATA"

    if category == ComponentCategory.PSU:
        if match := re.search(r"(\d{3,4})\s*W", text, re.IGNORECASE):
            specs["wattage_w"] = int(match.group(1))
        if match := re.search(r"80\s*Plus\s*(Bronze|Silver|Gold|Platinum|Titanium)", text, re.IGNORECASE):
            specs["efficiency_rating"] = f"80 Plus {match.group(1).title()}"

    return specs


def _find_products(node: Any) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        for key in ("serverProducts", "products"):
            value = node.get(key)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
        for value in node.values():
            found = _find_products(value)
            if found:
                return found
    if isinstance(node, list):
        for value in node:
            found = _find_products(value)
            if found:
                return found
    return []


def _first_str(raw: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            value = value.get("name") or value.get("value") or value.get("text")
        if isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                return text
    return None


def _first_int(raw: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            digits = re.sub(r"\D", "", value)
            if digits:
                return int(digits)
    return None


def _raw_category(raw: dict[str, Any]) -> str | None:
    category = raw.get("category") or raw.get("primaryCategory") or raw.get("categorySlug")
    if isinstance(category, dict):
        return _first_str(category, "slug", "code", "name")
    if isinstance(category, str):
        return category
    categories = raw.get("categories")
    if isinstance(categories, list) and categories:
        first = categories[0]
        if isinstance(first, dict):
            return _first_str(first, "slug", "code", "name")
        if isinstance(first, str):
            return first
    return None


def _extract_highlights(raw: dict[str, Any]) -> list[str]:
    value = raw.get("highlight") or raw.get("highlights") or raw.get("attributeLabels") or []
    if isinstance(value, str):
        value = [value]
    highlights: list[str] = []
    if not isinstance(value, list):
        return highlights
    for item in value:
        if isinstance(item, dict):
            item = item.get("name") or item.get("value") or item.get("text")
        if isinstance(item, str):
            text = _strip_tags(item)
            if text:
                highlights.append(text)
    return highlights


def _strip_tags(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(without_tags)).strip()


def _stock_quantity(raw: dict[str, Any]) -> int:
    quantity = _first_int(raw, "stockQuantity", "availableQuantity", "quantity")
    if quantity is not None:
        return quantity
    if raw.get("inStock") is True:
        return 1
    return 0


def _stock_status(raw: dict[str, Any], quantity: int) -> StockStatus:
    status = _first_str(raw, "stockStatus", "availability")
    if status:
        normalized = status.lower()
        if "pre" in normalized:
            return StockStatus.PREORDER
        if "out" in normalized or "het" in normalized:
            return StockStatus.OUT_OF_STOCK
    if quantity == 0:
        return StockStatus.OUT_OF_STOCK
    if quantity <= 5:
        return StockStatus.LOW_STOCK
    return StockStatus.IN_STOCK


def _product_url(raw: dict[str, Any], sku: str, source_url: str | None) -> str:
    url = _first_str(raw, "url", "productUrl", "canonicalUrl")
    if url:
        if url.startswith("http"):
            return url.split("?")[0]
        return f"https://phongvu.vn/{url.lstrip('/')}"
    slug = _first_str(raw, "slug")
    if slug:
        path = slug.strip("/")
        if f"--s{sku}" not in path:
            path = f"{path}--s{sku}"
        return f"https://phongvu.vn/{path}"
    if source_url:
        return source_url
    return f"https://phongvu.vn/search?q={sku}"


def _brand(raw: dict[str, Any]) -> str | None:
    value = raw.get("brand") or raw.get("brandName") or raw.get("manufacturer")
    if isinstance(value, dict):
        return _first_str(value, "name", "displayName", "code")
    if isinstance(value, str):
        return value.strip() or None
    return None


def _image_url(raw: dict[str, Any]) -> str | None:
    direct = _first_str(raw, "imageUrl", "thumbnail", "image")
    if direct:
        return direct
    images = raw.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            return _first_str(first, "url", "src")
        if isinstance(first, str):
            return first
    return None

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from pc_build_copilot.catalog_cli import CatalogSourceInput, load_source_manifest
from pc_build_copilot.catalog_models import ComponentCategory
from pc_build_copilot.catalog_parser import (
    CatalogParseError,
    normalize_products,
    parse_next_data_products,
)


@dataclass(frozen=True)
class CatalogSourceReportRow:
    input_path: Path
    source: str
    enabled: bool
    category_hint: ComponentCategory | None
    product_count: int
    invalid_product_count: int
    unique_sku_count: int
    category_counts: dict[ComponentCategory, int]


@dataclass(frozen=True)
class CatalogSourceReport:
    source_count: int
    enabled_source_count: int
    staged_source_count: int
    candidate_count: int
    invalid_candidate_count: int
    unique_candidate_count: int
    duplicate_candidate_count: int
    enabled_candidate_count: int
    staged_candidate_count: int
    category_counts: dict[ComponentCategory, int]
    enabled_category_counts: dict[ComponentCategory, int]
    staged_category_counts: dict[ComponentCategory, int]
    sources: list[CatalogSourceReportRow]


def build_source_report(
    *,
    manifest_path: Path,
    snapshot_at: datetime,
) -> CatalogSourceReport:
    sources = load_source_manifest(manifest_path, include_disabled=True)
    source_rows: list[CatalogSourceReportRow] = []
    all_items_by_sku: dict[str, ComponentCategory] = {}
    enabled_items_by_sku: dict[str, ComponentCategory] = {}
    staged_items_by_sku: dict[str, ComponentCategory] = {}
    candidate_count = 0
    enabled_candidate_count = 0
    staged_candidate_count = 0

    for source in sources:
        raw_products = parse_next_data_products(
            source.input_path.read_text(encoding="utf-8")
        )
        normalized_items = []
        invalid_product_count = 0
        for raw_product in raw_products:
            try:
                normalized_items.extend(
                    normalize_products(
                        [raw_product],
                        snapshot_at=snapshot_at,
                        category_hint=source.category_hint,
                        source_url=source.source_url,
                        source=source.source,
                    )
                )
            except CatalogParseError:
                invalid_product_count += 1
        candidate_count += len(normalized_items)
        if source.enabled:
            enabled_candidate_count += len(normalized_items)
        else:
            staged_candidate_count += len(normalized_items)

        per_source_skus = {item.sku for item in normalized_items}
        per_source_counts = Counter(item.category for item in normalized_items)
        for item in normalized_items:
            all_items_by_sku.setdefault(item.sku, item.category)
            if source.enabled:
                enabled_items_by_sku.setdefault(item.sku, item.category)
            else:
                staged_items_by_sku.setdefault(item.sku, item.category)

        source_rows.append(
            CatalogSourceReportRow(
                input_path=source.input_path,
                source=source.source,
                enabled=source.enabled,
                category_hint=source.category_hint,
                product_count=len(normalized_items),
                invalid_product_count=invalid_product_count,
                unique_sku_count=len(per_source_skus),
                category_counts=dict(per_source_counts),
            )
        )

    category_counts = Counter(all_items_by_sku.values())
    enabled_category_counts = Counter(enabled_items_by_sku.values())
    staged_category_counts = Counter(staged_items_by_sku.values())
    return CatalogSourceReport(
        source_count=len(sources),
        enabled_source_count=sum(1 for source in sources if source.enabled),
        staged_source_count=sum(1 for source in sources if not source.enabled),
        candidate_count=candidate_count,
        invalid_candidate_count=sum(row.invalid_product_count for row in source_rows),
        unique_candidate_count=len(all_items_by_sku),
        duplicate_candidate_count=max(0, candidate_count - len(all_items_by_sku)),
        enabled_candidate_count=enabled_candidate_count,
        staged_candidate_count=staged_candidate_count,
        category_counts=dict(category_counts),
        enabled_category_counts=dict(enabled_category_counts),
        staged_category_counts=dict(staged_category_counts),
        sources=source_rows,
    )


def source_report_to_dict(report: CatalogSourceReport) -> dict[str, Any]:
    return {
        "source_count": report.source_count,
        "enabled_source_count": report.enabled_source_count,
        "staged_source_count": report.staged_source_count,
        "candidate_count": report.candidate_count,
        "invalid_candidate_count": report.invalid_candidate_count,
        "unique_candidate_count": report.unique_candidate_count,
        "duplicate_candidate_count": report.duplicate_candidate_count,
        "enabled_candidate_count": report.enabled_candidate_count,
        "staged_candidate_count": report.staged_candidate_count,
        "category_counts": _category_counts_to_dict(report.category_counts),
        "enabled_category_counts": _category_counts_to_dict(
            report.enabled_category_counts
        ),
        "staged_category_counts": _category_counts_to_dict(
            report.staged_category_counts
        ),
        "sources": [
            {
                "input": str(row.input_path),
                "source": row.source,
                "enabled": row.enabled,
                "category_hint": row.category_hint.value
                if row.category_hint
                else None,
                "product_count": row.product_count,
                "invalid_product_count": row.invalid_product_count,
                "unique_sku_count": row.unique_sku_count,
                "category_counts": _category_counts_to_dict(row.category_counts),
            }
            for row in report.sources
        ],
    }


def _category_counts_to_dict(
    counts: dict[ComponentCategory, int]
) -> dict[str, int]:
    return {category.value: count for category, count in sorted(counts.items())}


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" in argv:
        argv.remove("--")

    parser = argparse.ArgumentParser(
        description="Report candidate coverage across enabled and staged catalog sources."
    )
    parser.add_argument(
        "--source-manifest",
        required=True,
        type=Path,
        help="Path to catalog_sources.json.",
    )
    parser.add_argument(
        "--snapshot-at",
        default="2026-06-27T00:00:00Z",
        help="Timestamp used while normalizing captured products.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args(argv)

    try:
        snapshot_at = datetime.fromisoformat(
            args.snapshot_at.replace("Z", "+00:00")
        )
        if snapshot_at.tzinfo is None:
            snapshot_at = snapshot_at.replace(tzinfo=UTC)
        report = build_source_report(
            manifest_path=args.source_manifest,
            snapshot_at=snapshot_at,
        )
    except (CatalogParseError, ValueError) as exc:
        print(f"Catalog source report failed: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(source_report_to_dict(report), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(
        "Catalog source report: "
        f"{report.unique_candidate_count} unique SKU candidates "
        f"from {report.source_count} source(s); "
        f"{report.enabled_source_count} enabled, {report.staged_source_count} staged."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

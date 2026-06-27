from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from pc_build_copilot.catalog_models import CatalogSnapshot, ComponentCategory
from pc_build_copilot.catalog_parser import (
    apply_overrides,
    load_overrides,
    normalize_products,
    parse_next_data_products,
)
from pc_build_copilot.catalog_validation import validate_catalog


def build_snapshot(
    *,
    input_path: Path,
    output_path: Path,
    overrides_path: Path | None,
    snapshot_at: datetime,
    snapshot_version: str,
    category_hint: ComponentCategory | None,
    source_url: str | None,
) -> CatalogSnapshot:
    raw_products = parse_next_data_products(input_path.read_text(encoding="utf-8"))
    items = normalize_products(
        raw_products,
        snapshot_at=snapshot_at,
        category_hint=category_hint,
        source_url=source_url,
    )
    if overrides_path is not None:
        items = apply_overrides(items, load_overrides(overrides_path))

    report = validate_catalog(
        items,
        snapshot_version=snapshot_version,
        generated_at=snapshot_at,
    )
    snapshot = CatalogSnapshot(
        snapshot_version=snapshot_version,
        generated_at=snapshot_at,
        source=str(input_path),
        items=items,
        validation=report,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return snapshot


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic local catalog snapshot from saved Phong Vu payloads."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--snapshot-at", required=True)
    parser.add_argument("--snapshot-version", default="catalog_v2026_06_27_fixture")
    parser.add_argument("--category-hint", choices=[item.value for item in ComponentCategory])
    parser.add_argument("--source-url")
    args = parser.parse_args(argv)

    snapshot = build_snapshot(
        input_path=args.input,
        output_path=args.output,
        overrides_path=args.overrides,
        snapshot_at=datetime.fromisoformat(args.snapshot_at.replace("Z", "+00:00")),
        snapshot_version=args.snapshot_version,
        category_hint=ComponentCategory(args.category_hint) if args.category_hint else None,
        source_url=args.source_url,
    )
    blocking = snapshot.validation.blocking_issue_count if snapshot.validation else 0
    print(
        f"Wrote {len(snapshot.items)} SKUs to {args.output} "
        f"with {blocking} blocking validation issues."
    )
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())

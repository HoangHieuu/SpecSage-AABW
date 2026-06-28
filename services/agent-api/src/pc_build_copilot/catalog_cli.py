from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from pc_build_copilot.catalog_models import CatalogSnapshot, ComponentCategory
from pc_build_copilot.catalog_parser import (
    CatalogParseError,
    apply_overrides,
    load_overrides,
    normalize_products,
    parse_next_data_products,
)
from pc_build_copilot.catalog_validation import validate_catalog


@dataclass(frozen=True)
class CatalogSourceInput:
    input_path: Path
    category_hint: ComponentCategory | None = None
    source_url: str | None = None
    source: str = "phongvu_next_data_fixture"


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
    return build_snapshot_from_sources(
        sources=[
            CatalogSourceInput(
                input_path=input_path,
                category_hint=category_hint,
                source_url=source_url,
            )
        ],
        output_path=output_path,
        overrides_path=overrides_path,
        snapshot_at=snapshot_at,
        snapshot_version=snapshot_version,
        source_description=str(input_path),
    )


def build_snapshot_from_sources(
    *,
    sources: Sequence[CatalogSourceInput],
    output_path: Path,
    overrides_path: Path | None,
    snapshot_at: datetime,
    snapshot_version: str,
    source_description: str,
) -> CatalogSnapshot:
    if not sources:
        raise CatalogParseError("Catalog source manifest must contain at least one source.")

    items_by_sku = {}
    for source in sources:
        raw_products = parse_next_data_products(source.input_path.read_text(encoding="utf-8"))
        normalized_items = normalize_products(
            raw_products,
            snapshot_at=snapshot_at,
            category_hint=source.category_hint,
            source_url=source.source_url,
            source=source.source,
        )
        for item in normalized_items:
            items_by_sku.setdefault(item.sku, item)

    items = list(items_by_sku.values())
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
        source=source_description,
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


def load_source_manifest(path: Path) -> list[CatalogSourceInput]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise CatalogParseError("Catalog source manifest must be a JSON object.")

    sources = loaded.get("sources")
    if not isinstance(sources, list) or not sources:
        raise CatalogParseError("Catalog source manifest must include a non-empty sources list.")

    parsed_sources: list[CatalogSourceInput] = []
    for index, raw_source in enumerate(sources):
        if not isinstance(raw_source, dict):
            raise CatalogParseError(f"Catalog source {index} must be a JSON object.")

        input_value = raw_source.get("input") or raw_source.get("path")
        if not isinstance(input_value, str) or not input_value.strip():
            raise CatalogParseError(f"Catalog source {index} is missing input path.")

        category_hint = _optional_category(raw_source.get("category_hint"), index)
        source_url = _optional_str(raw_source.get("source_url"), "source_url", index)
        source = _optional_str(raw_source.get("source"), "source", index)

        input_path = Path(input_value)
        if not input_path.is_absolute():
            input_path = (path.parent / input_path).resolve()

        parsed_sources.append(
            CatalogSourceInput(
                input_path=input_path,
                category_hint=category_hint,
                source_url=source_url,
                source=source or "phongvu_next_data_fixture",
            )
        )
    return parsed_sources


def _optional_category(value: Any, index: int) -> ComponentCategory | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise CatalogParseError(f"Catalog source {index} category_hint must be a string.")
    try:
        return ComponentCategory(value)
    except ValueError as exc:
        raise CatalogParseError(
            f"Catalog source {index} category_hint {value!r} is not supported."
        ) from exc


def _optional_str(value: Any, field: str, index: int) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise CatalogParseError(f"Catalog source {index} {field} must be a string.")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic local catalog snapshot from saved Phong Vu payloads."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path)
    source_group.add_argument("--source-manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--snapshot-at", required=True)
    parser.add_argument("--snapshot-version", default="catalog_v2026_06_27_fixture")
    parser.add_argument("--category-hint", choices=[item.value for item in ComponentCategory])
    parser.add_argument("--source-url")
    args = parser.parse_args(argv)

    snapshot_at = datetime.fromisoformat(args.snapshot_at.replace("Z", "+00:00"))
    if args.source_manifest is not None:
        if args.category_hint or args.source_url:
            parser.error("--category-hint and --source-url are only valid with --input.")
        sources = load_source_manifest(args.source_manifest)
        snapshot = build_snapshot_from_sources(
            sources=sources,
            output_path=args.output,
            overrides_path=args.overrides,
            snapshot_at=snapshot_at,
            snapshot_version=args.snapshot_version,
            source_description=str(args.source_manifest),
        )
    else:
        snapshot = build_snapshot(
            input_path=args.input,
            output_path=args.output,
            overrides_path=args.overrides,
            snapshot_at=snapshot_at,
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

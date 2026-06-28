from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from pc_build_copilot.catalog_models import ComponentCategory
from pc_build_copilot.catalog_parser import CatalogParseError, parse_next_data_products


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; PCBuildCopilotCatalogCapture/0.1; "
    "+https://phongvu.vn)"
)


@dataclass(frozen=True)
class CatalogCaptureResult:
    output_path: Path
    product_count: int
    manifest_path: Path | None = None


def capture_category_payload(
    *,
    output_path: Path,
    manifest_path: Path | None = None,
    input_path: Path | None = None,
    url: str | None = None,
    category_hint: ComponentCategory | None = None,
    source: str = "phongvu_public_category_capture",
    source_url: str | None = None,
    timeout_seconds: float = 20.0,
) -> CatalogCaptureResult:
    if (input_path is None) == (url is None):
        raise CatalogParseError("Provide exactly one of input_path or url.")

    html = (
        input_path.read_text(encoding="utf-8")
        if input_path is not None
        else _fetch_url(url or "", timeout_seconds)
    )
    product_count = len(parse_next_data_products(html))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    resolved_source_url = source_url or url
    if manifest_path is not None:
        _upsert_manifest_source(
            manifest_path=manifest_path,
            output_path=output_path,
            category_hint=category_hint,
            source=source,
            source_url=resolved_source_url,
        )

    return CatalogCaptureResult(
        output_path=output_path,
        product_count=product_count,
        manifest_path=manifest_path,
    )


def _fetch_url(url: str, timeout_seconds: float) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CatalogParseError(f"Catalog capture URL is invalid: {url!r}.")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
            "User-Agent": DEFAULT_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise CatalogParseError(f"Catalog capture returned HTTP {status} for {url}.")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise CatalogParseError(f"Failed to fetch catalog capture URL {url}: {exc}") from exc


def _upsert_manifest_source(
    *,
    manifest_path: Path,
    output_path: Path,
    category_hint: ComponentCategory | None,
    source: str,
    source_url: str | None,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(manifest_path)
    sources = manifest["sources"]

    entry: dict[str, str] = {
        "input": _manifest_relative_path(manifest_path, output_path),
        "source": source,
    }
    if source_url:
        entry["source_url"] = source_url
    if category_hint is not None:
        entry["category_hint"] = category_hint.value

    for index, existing in enumerate(sources):
        if existing.get("input") == entry["input"] or (
            source_url and existing.get("source_url") == source_url
        ):
            sources[index] = entry
            break
    else:
        sources.append(entry)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_manifest(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {"sources": []}

    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise CatalogParseError("Catalog source manifest must be a JSON object.")

    sources = loaded.get("sources")
    if sources is None:
        loaded["sources"] = []
        sources = loaded["sources"]
    if not isinstance(sources, list) or not all(isinstance(item, dict) for item in sources):
        raise CatalogParseError("Catalog source manifest sources must be a list of objects.")

    return loaded  # type: ignore[return-value]


def _manifest_relative_path(manifest_path: Path, output_path: Path) -> str:
    relative = os.path.relpath(output_path.resolve(), manifest_path.parent.resolve())
    return Path(relative).as_posix()


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--"]:
        argv = argv[1:]

    parser = argparse.ArgumentParser(
        description=(
            "Capture a saved Phong Vu public category payload and optionally "
            "upsert it into the catalog source manifest."
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url")
    source_group.add_argument("--input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--category-hint", choices=[item.value for item in ComponentCategory])
    parser.add_argument("--source", default="phongvu_public_category_capture")
    parser.add_argument("--source-url")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args(argv)

    try:
        result = capture_category_payload(
            input_path=args.input,
            url=args.url,
            output_path=args.output,
            manifest_path=args.manifest,
            category_hint=ComponentCategory(args.category_hint)
            if args.category_hint
            else None,
            source=args.source,
            source_url=args.source_url,
            timeout_seconds=args.timeout_seconds,
        )
    except CatalogParseError as exc:
        print(f"Catalog capture failed: {exc}", file=sys.stderr)
        return 1

    manifest_text = (
        f"; manifest updated at {result.manifest_path}" if result.manifest_path else ""
    )
    print(
        f"Captured {result.product_count} SKU candidates to {result.output_path}"
        f"{manifest_text}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

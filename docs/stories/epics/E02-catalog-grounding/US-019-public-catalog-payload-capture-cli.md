# US-019 Public Catalog Payload Capture CLI

## Status

implemented

## Lane

normal

## Product Contract

Catalog expansion must have a repeatable local command for turning a public
Phong Vu category page, or a saved copy of one, into a fixture that can be
listed in `catalog_sources.json`. The command must validate that the captured
payload contains parseable product data before writing it or updating the
manifest.

This story does not make catalog sync live, automated, or dependent on
Phong Vu availability during tests. It creates a controlled capture boundary
before broader SKU expansion.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/decisions/0019-catalog-source-manifest-before-live-scraping.md`

## Acceptance Criteria

- A `pnpm catalog:capture` command can capture from either `--url` or a local
  `--input` HTML file.
- The command validates `__NEXT_DATA__` product payloads before writing the
  fixture.
- The command can upsert a deterministic manifest entry with relative input
  path, source label, optional source URL, and optional category hint.
- Re-running capture for the same output/source URL does not duplicate manifest
  entries.
- Existing `pnpm catalog:sync`, API checks, and local evals continue to pass.

## Design Notes

- Commands:
  - `pnpm catalog:capture -- --url <phongvu-category-url> --output <fixture> --manifest services/agent-api/catalog/catalog_sources.json`
  - `pnpm catalog:capture -- --input <saved-html> --output <fixture> --manifest <manifest>`
- Domain rules:
  - Capture validates parseability but does not enrich compatibility specs.
  - Compatibility-critical enrichment remains in `sku_specs_overrides.json`.
  - The manifest remains the only input to `pnpm catalog:sync`.
- API/UI:
  - No public API or UI surface changes.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-019 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused capture tests cover local input capture, manifest upsert idempotency, and invalid payload rejection. |
| Integration | `pnpm catalog:capture` smoke command, `pnpm catalog:sync`, `pnpm check`, and `pnpm eval:run`. |
| E2E | Not required; this is local catalog tooling. |
| Platform | Not required; no hosted provider integration. |
| Release | `scripts/bin/harness-cli story verify US-019`. |

## Harness Delta

The story adds a durable Phase 2 proof row for the capture step that feeds the
existing manifest ingestion workflow.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py`
  passed with 8 focused catalog/capture tests.
- `pnpm catalog:capture -- --input services/agent-api/fixtures/phongvu-category-components.html --output /tmp/pc-build-copilot-capture-smoke.html --manifest /tmp/pc-build-copilot-catalog-sources.json --source test_capture_smoke --category-hint vga --source-url https://phongvu.vn/c/vga-card-man-hinh`
  captured 11 SKU candidates and upserted a manifest entry.
- `pnpm catalog:sync` wrote 11 SKUs with 0 blocking validation issues.
- `pnpm check` passed with Next.js build and 74 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-019` passed.

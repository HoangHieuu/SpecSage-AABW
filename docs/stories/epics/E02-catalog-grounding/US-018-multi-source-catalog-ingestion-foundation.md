# US-018 Multi-Source Catalog Ingestion Foundation

## Status

implemented

## Lane

normal

## Product Contract

Catalog sync must support more than one saved Phong Vu public payload so the
local mirror can grow toward broader product coverage without changing parser
code for every category. Source expansion should be deterministic, auditable,
deduplicated by SKU, and still validated before the snapshot is used by agents.

This is a Phase 2 catalog-completeness slice. It does not add live scraping,
Firecrawl, Phong Vu/Teko private APIs, Typesense, Postgres, or admin catalog
editing.

## Relevant Product Docs

- `SPEC.md` Phase 2 / `US-2.1 Grounded Product Catalog`
- `Data.md` Layer 1 category scraping and local catalog mirror strategy
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-002-catalog-snapshot-ingestion.md`
- `docs/stories/epics/E02-catalog-grounding/US-016-catalog-demo-readiness-health.md`
- `docs/stories/epics/E02-catalog-grounding/US-017-catalog-demo-variety-health.md`

## Acceptance Criteria

- Catalog sync accepts a manifest listing multiple saved public payload sources.
- Manifest paths may be relative to the manifest file.
- Each source can declare a category hint, source URL, and provenance label.
- Sync merges all source products deterministically and deduplicates by SKU.
- Curated overrides still apply after source merging.
- `pnpm catalog:sync` uses the source manifest and writes the generated
  snapshot with source provenance.
- Existing single-input CLI mode remains supported for focused tests and
  debugging.
- Existing build generation and eval behavior remain grounded in local snapshot
  SKUs.

## Design Notes

- CLI:
  - Keep `--input` for single saved payloads.
  - Add `--source-manifest` for multi-source snapshot builds.
- Data:
  - Add `services/agent-api/catalog/catalog_sources.json` as the editable
    source manifest.
  - Keep saved public payloads under `services/agent-api/fixtures/`.
  - Keep curated compatibility specs in
    `services/agent-api/catalog/sku_specs_overrides.json`.
- Determinism:
  - Sources are processed in manifest order.
  - First occurrence of a SKU wins before overrides are applied.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-018 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Catalog CLI test merges manifest sources, resolves relative paths, dedupes SKUs, and applies overrides |
| Integration | `pnpm catalog:sync` writes the real snapshot through `catalog_sources.json` |
| E2E | Not required; catalog ingestion infrastructure has no direct UI surface |
| Platform | Not required; no external provider or deployment change |
| Release | `pnpm catalog:sync`; `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-018` |

## Harness Delta

Move catalog expansion from one hard-coded fixture path to an auditable source
manifest so broad SKU coverage can be added source-by-source.

## Evidence

- Focused catalog ingestion tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py`.
- `pnpm catalog:sync` wrote 11 SKUs through
  `services/agent-api/catalog/catalog_sources.json` with 0 blocking validation
  issues.
- `scripts/bin/harness-cli story verify US-018` passed with
  `pnpm catalog:sync && pnpm check && pnpm eval:run`.
- `pnpm check` passed with Next.js build and 72 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.

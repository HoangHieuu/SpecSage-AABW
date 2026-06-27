# US-016 Catalog Demo Readiness Health

## Status

implemented

## Lane

normal

## Product Contract

The local catalog health report must show whether the current snapshot has the
minimum category coverage needed for the hackathon demo build flow. The report
should make missing full-build categories visible before a generation or eval
run fails later.

This is a foundation slice for SPEC Phase 2 catalog grounding and Data.md's
local catalog mirror strategy. It does not add live scraping, Firecrawl,
Phong Vu/Teko private APIs, Typesense, Postgres, or admin catalog editing.

## Relevant Product Docs

- `SPEC.md` Phase 2 / `US-2.1 Grounded Product Catalog`
- `Data.md` minimum viable catalog and trust contract
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-002-catalog-snapshot-ingestion.md`

## Acceptance Criteria

- Catalog validation reports per-category SKU counts.
- Catalog validation marks the snapshot demo-ready only when all required
  full-build categories exist: CPU, mainboard, RAM, storage, VGA, PSU, and case.
- Missing required demo categories produce blocking validation issues.
- `GET /catalog/health` exposes the category counts, missing category list, and
  demo-ready flag.
- `pnpm catalog:sync` writes the new health fields into
  `catalog_snapshot.json`.
- Existing build generation and eval behavior remain deterministic and grounded
  in local snapshot SKUs.

## Design Notes

- API:
  - `GET /catalog/health`
- Domain:
  - Extend `CatalogValidationReport` with category coverage fields.
  - Keep compatibility-required per-SKU spec checks unchanged.
- Data:
  - The current fixture remains the source for this slice.
  - The current 11-SKU fixture should be demo-ready for the first full-build
    flow because it contains all required component categories.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-016 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Catalog validation reports category coverage and blocks missing required categories |
| Integration | Catalog health endpoint exposes demo readiness and category counts |
| E2E | Not required; no user-visible UI change |
| Platform | Not required; no external provider or deployment change |
| Release | `pnpm catalog:sync`; `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-016` |

## Harness Delta

Add a catalog-health proof point before expanding to live scraping or larger
curated SKU coverage.

## Evidence

- Focused catalog tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`.
- `pnpm catalog:sync` wrote 11 SKUs with 0 blocking validation issues and
  embedded `demo_ready: true`, required categories, missing categories, and
  per-category counts in `catalog_snapshot.json`.
- `pnpm check` passed with Next.js build and 71 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-016` passed with
  `pnpm catalog:sync && pnpm check && pnpm eval:run`.

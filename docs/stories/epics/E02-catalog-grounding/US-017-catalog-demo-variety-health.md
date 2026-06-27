# US-017 Catalog Demo Variety Health

## Status

implemented

## Lane

normal

## Product Contract

Catalog health must distinguish between a blocking missing-category failure and
a non-blocking thin-coverage warning. The first demo can run when each required
full-build category exists, but the health report should still reveal when the
local snapshot has too little choice for credible alternatives or fallback
parts.

This extends `US-016` without adding live scraping, Firecrawl, Phong Vu/Teko
private APIs, Typesense, Postgres, or admin catalog editing.

## Relevant Product Docs

- `SPEC.md` Phase 2 / `US-2.1 Grounded Product Catalog`
- `Data.md` minimum viable catalog and trust contract
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-016-catalog-demo-readiness-health.md`
- `docs/decisions/0017-catalog-demo-readiness-before-live-scraping.md`

## Acceptance Criteria

- Catalog validation reports recommended minimum demo SKU counts per required
  full-build category.
- Catalog validation reports thin demo categories when a required category has
  at least one SKU but fewer than the recommended demo count.
- Thin category coverage produces warning issues, not blocking issues.
- Missing required demo categories remain blocking validation issues.
- `GET /catalog/health` exposes recommended counts and thin categories.
- `pnpm catalog:sync` writes the new variety health fields into
  `catalog_snapshot.json`.
- Existing build generation and eval behavior remain deterministic and grounded
  in local snapshot SKUs.

## Design Notes

- API:
  - `GET /catalog/health`
- Domain:
  - Extend `CatalogValidationReport` with recommended demo category counts and
    thin category lists.
  - Keep `demo_ready` based on blocking validation issues and missing required
    full-build categories only.
- Data:
  - The current fixture remains the source for this slice.
  - The recommended minimum is two SKUs for each required full-build category:
    CPU, mainboard, RAM, storage, VGA, PSU, and case.
  - Cooler and monitor remain optional for this slice.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-017 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Catalog validation warns on thin categories and keeps missing categories blocking |
| Integration | Catalog health endpoint exposes recommended counts and thin category warnings |
| E2E | Not required; no user-visible UI change |
| Platform | Not required; no external provider or deployment change |
| Release | `pnpm catalog:sync`; `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-017` |

## Harness Delta

Add a catalog-variety proof point before expanding the fixture into broader
curated SKU coverage.

## Evidence

- Focused catalog tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`.
- `pnpm catalog:sync` wrote 11 SKUs with `demo_ready=true`, 0 blocking
  issues, and 3 warning issues for thin CPU, mainboard, and case coverage.
- `scripts/bin/harness-cli story verify US-017` passed with
  `pnpm catalog:sync && pnpm check && pnpm eval:run`.
- `pnpm check` passed with Next.js build and 71 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.

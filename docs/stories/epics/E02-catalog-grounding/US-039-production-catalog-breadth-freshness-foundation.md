# US-039 Production Catalog Breadth And Freshness Foundation

## Status

implemented

## Lane

normal

## Product Contract

The local catalog mirror distinguishes demo, pilot, and production readiness
without claiming full catalog coverage. The active snapshot has enough curated
SKU breadth for a stronger pilot build loop, reports snapshot freshness, exposes
spec confidence counts, and keeps production coverage gaps visible until broader
verified curation is selected.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-022-curated-catalog-subset-promotion.md`

## Acceptance Criteria

- The active catalog contains at least three active SKUs for CPU, mainboard,
  RAM, storage, VGA, PSU, and case.
- Newly promoted SKUs come from staged Phong Vu fixtures through curated
  `include_skus` entries, not broad full-category enablement.
- Catalog validation reports `demo_ready`, `pilot_ready`, and
  `production_ready` separately.
- Catalog validation reports freshness fields, including a 7-day stale window
  and stale warning issue when the snapshot is too old.
- Catalog validation reports spec-confidence counts and production target gaps.
- `GET /catalog/health` exposes the new readiness, freshness, confidence, and
  production-gap fields.
- The active snapshot remains zero-blocking and pilot-ready, while
  production-ready remains false until production target counts are met.

## Design Notes

- Commands:
  - `pnpm catalog:sync`
  - `pnpm catalog:source-report`
  - `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  - `pnpm check:web`
- Domain rules:
  - `demo_ready` remains the existing hard gate for the current full-build demo.
  - `pilot_ready` requires at least three SKUs in each required full-build
    category and a fresh snapshot.
  - `production_ready` requires full production target category counts and a
    fresh snapshot.
  - Partial specs may satisfy deterministic compatibility gates, but the report
    must count them so the product does not overclaim catalog maturity.
- API:
  - `GET /catalog/health`
- UI surfaces:
  - None. This story is catalog infrastructure and API health.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-039 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused catalog tests cover stale snapshots, pilot readiness, production gaps, and the real manifest reaching three SKUs per required category. |
| Integration | `pnpm catalog:sync`, `pnpm catalog:source-report`, focused API health tests, and `pnpm check:web`. |
| E2E | Not required; this is catalog health and data readiness. |
| Platform | Not required; no hosted scraper, scheduler, database migration, or production deployment. |
| Release | `scripts/bin/harness-cli story verify US-039`. |

## Harness Delta

No Harness operating-model changes are required. This story updates the existing
catalog story row and product/test matrix records.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  passed with 22 focused catalog/API tests.
- `pnpm catalog:sync` wrote 21 SKUs with 0 blocking validation issues,
  `pilot_ready=true`, `production_ready=false`, and one production-gap warning.
- `pnpm catalog:source-report` reported 370 unique SKU candidates from 17
  sources, with 8 enabled sources and 9 staged sources.
- `pnpm check:web` passed.
- `scripts/bin/harness-cli story verify US-039` passed.

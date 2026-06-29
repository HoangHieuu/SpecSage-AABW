# US-040 Optional Cooler And Monitor Catalog Curation

## Status

implemented

## Lane

normal

## Product Contract

The active local catalog includes a curated optional-category foundation for CPU
coolers and monitors. These SKUs come from staged Phong Vu public fixtures,
carry compatibility-critical fields, and pass deterministic catalog validation
without making cooler or monitor required in the default full-build generator.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-039-production-catalog-breadth-freshness-foundation.md`

## Acceptance Criteria

- The active catalog contains at least three cooler SKUs and three monitor SKUs.
- Cooler and monitor rows are promoted through curated `include_skus` entries,
  while broad cooler and monitor category captures remain staged.
- Promoted cooler rows include `socket_support`, `tdp_rating_w`, and
  `height_mm`.
- Promoted monitor rows include `resolution` and `refresh_rate_hz`.
- Catalog validation reports zero blocking issues and keeps `pilot_ready=true`.
- Catalog validation keeps `production_ready=false` until production target
  counts are met.
- Default build generation required slots are unchanged; cooler and monitor
  are optional catalog rows for future stories.

## Design Notes

- Commands:
  - `pnpm catalog:sync`
  - `pnpm catalog:source-report`
  - `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  - `pnpm check:web`
- Domain rules:
  - `include_skus` remains the promotion gate.
  - Optional categories reduce production-gap risk but do not change
    `DEMO_REQUIRED_CATEGORIES` or `REQUIRED_FULL_BUILD_SLOTS`.
  - New optional rows use `partial` spec confidence until richer detail-page or
    manufacturer-source ingestion is implemented.
- API:
  - `GET /catalog/health`
  - `GET /catalog/skus?category=cooler`
  - `GET /catalog/skus?category=monitor`
- UI surfaces:
  - None. This is catalog infrastructure and API health.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-040 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused catalog tests cover the real manifest reaching three cooler and three monitor SKUs with no missing required specs. |
| Integration | `pnpm catalog:sync`, `pnpm catalog:source-report`, focused API health tests, and `pnpm check:web`. |
| E2E | Not required; this is catalog data readiness, not a customer UI workflow. |
| Platform | Not required; no hosted scraper, scheduler, database migration, or production deployment. |
| Release | `scripts/bin/harness-cli story verify US-040`. |

## Harness Delta

No Harness operating-model changes are required. This story updates the
catalog story row and product/test matrix records.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  passed with 22 focused catalog/API tests.
- `pnpm catalog:sync` wrote 27 SKUs with 0 blocking validation issues, 3
  cooler SKUs, 3 monitor SKUs, `pilot_ready=true`, and
  `production_ready=false`.
- `pnpm catalog:source-report` reported 370 unique SKU candidates from 19
  sources, with 10 enabled sources and 9 staged sources.
- `pnpm check:web` passed.
- `scripts/bin/harness-cli story verify US-040` passed.

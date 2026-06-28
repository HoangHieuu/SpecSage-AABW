# US-022 Curated Catalog Subset Promotion

## Status

implemented

## Lane

normal

## Product Contract

The local catalog mirror can promote a reviewed subset of SKUs from staged
Phong Vu public category captures without enabling the full unverified category
page. Promoted SKUs must be real Phong Vu SKUs, must have compatibility-critical
overrides, and must pass the same deterministic catalog validation as the
existing active snapshot.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/decisions/0021-staged-catalog-captures-before-recommendations.md`
- `docs/decisions/0023-curated-catalog-subsets-before-source-enablement.md`

## Acceptance Criteria

- `catalog_sources.json` supports enabled entries with `include_skus`.
- `pnpm catalog:sync` includes only the listed SKUs from an `include_skus`
  source and fails if a listed SKU is absent from that source.
- `pnpm catalog:source-report` counts curated enabled candidates while keeping
  full category captures staged.
- The active snapshot includes at least two SKUs for CPU, mainboard, RAM,
  storage, VGA, PSU, and case.
- The active snapshot has zero blocking catalog validation issues and no thin
  required demo categories.
- Existing recommendation behavior continues to use only active snapshot SKUs.

## Design Notes

- Commands:
  - `pnpm catalog:source-report`
  - `pnpm catalog:sync`
  - `pnpm check`
  - `pnpm eval:run`
- Domain rules:
  - `include_skus` is a promotion gate, not a broad scrape gate.
  - Curated sources may reuse staged fixtures, but full staged entries stay
    `enabled=false`.
  - Promoted SKUs require overrides for all fields in
    `catalog_validation.REQUIRED_SPECS`.
- API/UI:
  - No public API or UI surface changes.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-022 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused catalog tests cover `include_skus`, missing include failures, source-report counts, and curated snapshot validation. |
| Integration | `pnpm catalog:source-report`, `pnpm catalog:sync`, `pnpm check`, and `pnpm eval:run`. |
| E2E | Not required; this is catalog data/tooling infrastructure. |
| Platform | Not required; no hosted provider or scheduled scraper integration. |
| Release | `scripts/bin/harness-cli story verify US-022`. |

## Harness Delta

This story adds a manifest-level promotion mechanism for curated staged SKUs.
No Harness operating-model changes are required.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py`
  passed with 17 focused catalog tests.
- `pnpm catalog:source-report` reported 370 unique SKU candidates from 13
  sources, with 4 enabled sources and 9 staged sources.
- `pnpm catalog:sync` wrote 14 SKUs with 0 blocking validation issues and no
  thin required demo categories.
- `pnpm check` passed with Next.js build and 83 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-022` passed.

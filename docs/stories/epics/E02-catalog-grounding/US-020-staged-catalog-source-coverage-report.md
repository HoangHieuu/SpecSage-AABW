# US-020 Staged Catalog Source Coverage Report

## Status

implemented

## Lane

normal

## Product Contract

The local catalog mirror must be able to stage captured public Phong Vu category
payloads before those SKUs are eligible for recommendations. Staged sources are
parseable, auditable inputs for future enrichment, but `catalog:sync` must skip
them until compatibility-critical overrides are verified.

The repo must also expose a local source report that counts enabled and staged
SKU candidates by category, duplicate count, and invalid rows.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/decisions/0021-staged-catalog-captures-before-recommendations.md`

## Acceptance Criteria

- `catalog_sources.json` supports staged entries with `enabled=false`.
- `pnpm catalog:sync` ignores staged sources and keeps the active snapshot
  validation-clean.
- `pnpm catalog:source-report` parses enabled and staged sources and reports
  candidate counts, duplicate counts, invalid row counts, and category coverage.
- Captured public category fixtures exist for CPU, mainboard, RAM, VGA,
  storage, PSU, case, cooler, and monitor.
- Existing recommendation behavior continues to use only enabled snapshot SKUs.

## Design Notes

- Commands:
  - `pnpm catalog:capture -- --url <category-url> --output <fixture> --manifest services/agent-api/catalog/catalog_sources.json --staged`
  - `pnpm catalog:source-report`
  - `pnpm catalog:sync`
- Domain rules:
  - Staged sources are not recommendation-eligible.
  - Staged candidates may be normalized for reporting, but still need curated
    `sku_specs_overrides.json` entries before they can be enabled.
  - Missing compatibility fields remain blocking only when a source is enabled
    into the active snapshot.
- API/UI:
  - No public API or UI surface changes.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-020 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused catalog tests cover disabled manifest skip, staged capture entries, current Teko listing normalization, source report counts, and invalid staged rows. |
| Integration | `pnpm catalog:source-report`, `pnpm catalog:sync`, `pnpm check`, and `pnpm eval:run`. |
| E2E | Not required; this is catalog data/tooling infrastructure. |
| Platform | Not required; no hosted provider or scheduled scraper integration. |
| Release | `scripts/bin/harness-cli story verify US-020`. |

## Harness Delta

This story adds a durable coverage-report step between raw public category
capture and recommendation-eligible catalog sync.

## Evidence

Validation passed:

- `pnpm catalog:source-report` reported 370 unique SKU candidates from 10
  sources, with 1 enabled source and 9 staged sources.
- `pnpm catalog:sync` kept the active 11-SKU snapshot validation-clean with 0
  blocking issues.
- `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py`
  passed with 13 focused catalog tests.
- `pnpm check` passed with Next.js build and 79 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-020` passed.

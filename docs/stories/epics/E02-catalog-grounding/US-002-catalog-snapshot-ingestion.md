# US-002 Catalog Snapshot Ingestion

## Status

implemented

## Lane

high-risk

## Product Contract

The system can build a reproducible local catalog snapshot from public Phong Vu
product data and enrich enough specs to support grounded recommendations and
deterministic compatibility checks.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- Catalog sync extracts real SKU IDs, names, categories, prices, stock signals,
  product URLs, brand fields, and highlight specs from public pages.
- Enrichment produces structured fields required by the first compatibility
  rules.
- Curated overrides are auditable and versioned.
- Every generated build references only SKUs in the current catalog snapshot.
- UI/API output exposes catalog snapshot timestamp and data-confidence state.

## Design Notes

- Commands: run category sync, run enrichment, validate catalog.
- Queries: filter SKUs by category, price, stock, socket, wattage, capacity.
- API: internal catalog search endpoint or application service.
- Tables/files: first slice may use JSON/SQLite; production shape can move to
  PostgreSQL and Typesense.
- Domain rules: missing critical compatibility fields block affected SKU use.
- UI surfaces: build table links each selected SKU to Phong Vu.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | parser and enrichment tests against saved fixtures |
| Integration | sync job creates snapshot and validation report |
| E2E | no browser proof required for ingestion alone |
| Platform | none until live scheduled sync or deploy exists |
| Release | story verify command must not depend on live Phong Vu availability |

## Harness Delta

Expanded high-risk packet:

- `docs/stories/epics/E02-catalog-grounding/US-002-catalog-snapshot-ingestion/execplan.md`
- `docs/stories/epics/E02-catalog-grounding/US-002-catalog-snapshot-ingestion/overview.md`
- `docs/stories/epics/E02-catalog-grounding/US-002-catalog-snapshot-ingestion/design.md`
- `docs/stories/epics/E02-catalog-grounding/US-002-catalog-snapshot-ingestion/validation.md`

## Evidence

- `pnpm catalog:sync` generated `services/agent-api/catalog/catalog_snapshot.json`
  with 7 SKUs and 0 blocking validation issues.
- `.venv/bin/python -m pytest services/agent-api/tests` passed with 14 tests.
- `GET /catalog/health` and `GET /catalog/skus` expose snapshot timestamp,
  validation state, SKU fields, and confidence labels.
- Live scraping and provider APIs are intentionally out of scope for this
  reproducible fixture-based slice.

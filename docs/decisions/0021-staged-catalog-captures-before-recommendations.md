# 0021 Staged Catalog Captures Before Recommendations

## Status

Accepted

## Context

The project can now capture public Phong Vu category payloads, but enabling all
captured SKUs immediately would weaken the deterministic recommendation
contract. The public listing pages expose useful SKU, price, stock, brand,
image, link, and highlight data, but compatibility-critical fields still need
curated overrides before a SKU can safely feed build generation.

## Decision

Extend the catalog source manifest with staged sources:

- Manifest entries default to enabled.
- Entries with `enabled=false` are parsed by `pnpm catalog:source-report`.
- `pnpm catalog:sync` skips staged sources.
- Captured public category pages for CPU, mainboard, RAM, VGA, storage, PSU,
  case, cooler, and monitor are kept as staged fixtures until overrides are
  verified.

## Consequences

- The repo can track real public category coverage without allowing unverified
  SKUs into recommendations.
- Catalog expansion becomes measurable: staged candidate counts and category
  gaps are visible before curation work starts.
- The next Phase 2 implementation can promote a small verified subset by adding
  overrides and flipping specific sources or curated payloads to enabled.

## Follow-Ups

- Curate 2-5 verified SKUs per weak category from staged sources.
- Add product-detail capture when listing highlights are not enough for
  compatibility fields.
- Keep `catalog:source-report` in the local release checklist while broadening
  catalog coverage.

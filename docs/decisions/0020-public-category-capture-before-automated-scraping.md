# 0020 Public Category Capture Before Automated Scraping

## Status

Accepted

## Context

`US-018` introduced a manifest for saved catalog payloads, but creating those
payloads was still manual. Jumping directly to scheduled scraping, Firecrawl, or
private Teko APIs would add external availability and credential risk before the
local catalog contract has enough coverage and validation history.

## Decision

Add a small local capture CLI before automated scraping:

- `pnpm catalog:capture` can fetch a public category URL or copy a saved HTML
  file.
- Capture validates that the payload contains parseable `__NEXT_DATA__`
  products before writing the fixture.
- Capture can upsert a deterministic `catalog_sources.json` entry.
- `pnpm catalog:sync` remains the only command that builds the normalized
  catalog snapshot used by the agents.

This is still a local mirror workflow. It does not claim live freshness, private
Phong Vu/Teko API access, a scheduled crawler, or full catalog coverage.

## Consequences

- Future SKU expansion has a repeatable command instead of ad hoc fixture
  copying.
- Tests can validate capture behavior without contacting Phong Vu.
- Live category captures can be run intentionally when network access and
  product timing allow, then reviewed as ordinary fixture and override changes.

## Follow-Ups

- Capture saved payloads for the weakest required categories.
- Add overrides for compatibility-critical fields before using captured SKUs in
  recommendation flows.
- Promote capture into a scheduled catalog-sync service only after the local
  fixture workflow is validated at broader coverage.

# 0019 Catalog Source Manifest Before Live Scraping

## Status

Accepted

## Context

The project needs to move beyond the first fixture without jumping straight to
live scraping or private Phong Vu/Teko APIs. Live scraping introduces external
availability, rate-limit, and freshness concerns, while the current local
snapshot path is reproducible but too hard-coded to scale across many saved
category payloads.

## Decision

Add a catalog source manifest as the next Phase 2 ingestion boundary:

- `services/agent-api/catalog/catalog_sources.json` lists saved public payload
  sources.
- `pnpm catalog:sync` reads that manifest.
- The catalog CLI keeps single-input mode for tests and debugging.
- Multi-source sync processes sources in manifest order, deduplicates by SKU,
  applies curated overrides, and validates the final snapshot.

This does not add live scraping, Firecrawl, Phong Vu/Teko private APIs,
Typesense, PostgreSQL, or admin catalog editing.

## Consequences

- Expanding coverage becomes an auditable data change: add a saved payload,
  add a manifest entry, add or update overrides, then run the same validation
  gate.
- Snapshot source provenance now points to the manifest and each SKU can carry
  the source label from its payload entry.
- Future live scraping can reuse the same manifest contract as a staging input
  before replacing the source collection mechanism.

## Follow-Ups

- Add saved category payloads for CPU, mainboard, case, cooler, and monitor.
- Curate compatibility overrides for the expanded SKU set before using those
  SKUs in generation or alternatives.
- Introduce a real catalog-sync service only after the local manifest workflow
  proves the data contract.

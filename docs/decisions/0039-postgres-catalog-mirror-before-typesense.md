# 0039 Postgres Catalog Mirror Before Typesense

Date: 2026-06-30

## Status

Accepted

## Context

`US-039` and `US-040` made the local catalog pilot-ready for core full-build
categories and added optional cooler/monitor rows. The active catalog is still
a validated JSON snapshot bundled with the deployment. That is reproducible,
but it is not yet a production-owned catalog data layer.

`techstack.md` names PostgreSQL tables (`skus`, `sku_specs`,
`catalog_versions`) as the Phase 2 primary datastore, with Typesense and
pgvector as search layers after the catalog data exists. `Data.md` says the
practical source of truth remains a mirrored public Phong Vu snapshot refreshed
on a schedule.

## Decision

Add a Postgres catalog mirror before Typesense, pgvector, or scheduled scraping.

The current `catalog_snapshot.json` remains the validated ingestion artifact.
A loader imports it into:

- `catalog_versions`
- `catalog_skus`

The deployed API prefers the active Postgres catalog when a database URL is
configured and falls back to the JSON snapshot when no active catalog version
exists.

## Alternatives Considered

1. Keep JSON-only catalog in production. Rejected because production catalog
   freshness needs database-owned active versions and queryable SKU rows.
2. Add Typesense first. Deferred because Typesense should index from durable
   catalog tables, not replace them.
3. Add pgvector first. Deferred because semantic retrieval is less urgent than
   exact SKU, price, stock, category, and spec filters.
4. Schedule live scraping now. Deferred because the load/read path should be
   reliable before an automated job starts writing production data.
5. Move directly to real Teko APIs. Deferred until official access exists.

## Consequences

Positive:

- Production catalog state can be inspected in Neon.
- Active catalog versioning prepares build revalidation and future freshness
  jobs.
- Existing deterministic catalog validation remains the gate before load.
- API and UI response contracts remain unchanged.

Tradeoffs:

- This is not yet a scheduled fresh scrape.
- Typesense, pgvector, and admin review are still future work.
- The active snapshot still has production coverage gaps until more SKUs are
  curated.

## Follow-Up

- Add scheduled catalog capture/sync/load after the manual load path is stable.
- Add richer product detail pass and spec enrichment before expanding to
  production target counts.
- Add Typesense only after Postgres catalog rows are the durable source.
- Add real cart/checkout only after catalog freshness and official API access
  are in place.

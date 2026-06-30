# 0040 Catalog Publish Audit Before Cron

Date: 2026-06-30

## Status

Accepted

## Context

`US-048` created the durable Postgres catalog mirror and loaded the active
validated snapshot into Neon. The next production risk is refresh safety: before
a cron job or scheduled scraper writes catalog data automatically, operators
need durable evidence of each publish attempt and whether validation blocked,
failed, or activated a version.

`Data.md` recommends a sync job that crawls, enriches, validates, indexes, and
tags catalog snapshots. `techstack.md` recommends queues and scheduled jobs for
catalog sync later. The current product is not ready for automated live scraping
or Typesense/pgvector indexing, but it can safely record manual publish runs.

## Decision

Add `catalog_publish_runs` before scheduled catalog automation.

`pnpm catalog:load-postgres` records a publish run with validation counts,
status, timestamps, load options, and error text. Blocked validation attempts
are persisted without writing SKU rows by default. Successful loads activate the
catalog version and mark the run loaded.

## Alternatives Considered

1. Add Vercel Cron immediately. Deferred because the load path needs durable
   run history before unattended writes.
2. Add Typesense indexing first. Deferred because search should index from
   trustworthy catalog publish events.
3. Keep stdout-only publish logs. Rejected because logs are not the product's
   durable catalog audit trail.
4. Build an admin UI for publish history. Deferred until staff/admin auth and
   mutation boundaries are selected.

## Consequences

Positive:

- Operators can inspect catalog publish history in Postgres.
- Future cron, queue, and search-index jobs have an audit anchor.
- Blocked validation attempts become visible without mutating active SKU rows.

Tradeoffs:

- There is still no scheduled scraping.
- There is no customer-facing UI change.
- Failed publish recording is best-effort when the database itself is
  unavailable.

## Follow-Up

- Add a scheduled refresh job only after manual publish audit is stable.
- Add search indexing from `catalog_publish_runs` and active `catalog_skus`.
- Add staff/admin publish history only after the auth boundary is selected.

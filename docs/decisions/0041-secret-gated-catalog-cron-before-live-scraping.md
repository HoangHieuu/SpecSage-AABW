# 0041 Secret-Gated Catalog Cron Before Live Scraping

Date: 2026-07-01

## Status

Accepted

## Context

`US-048` added a Postgres catalog mirror, and `US-049` added durable publish-run
audit rows. The next production gap is unattended refresh execution. A cron job
that writes catalog rows without authentication or audit would be unsafe, but a
full live scraper would expand provider, rate-limit, and validation risk before
the publish path itself has scheduled proof.

Vercel Cron is the smallest deployed scheduler available in the current hosting
shape, and it invokes HTTP endpoints in production.

## Decision

Add a secret-gated Vercel Cron endpoint before live scraping.

The route is:

```text
GET /api/catalog/refresh
Authorization: Bearer <CRON_SECRET>
```

The endpoint reads the deployed validated `catalog_snapshot.json`, resolves the
configured Postgres URL, and calls the existing audited catalog loader with
`allow_blocking = false` and `trigger = vercel_cron`.

It does not fetch live public pages, call private Teko APIs, or index
Typesense/pgvector. Those remain later stories after the scheduled publish path
is proven.

## Alternatives Considered

1. Schedule live public-page scraping immediately. Deferred because unattended
   network scraping needs rate-limit, fixture capture, and validation controls.
2. Add ARQ/BullMQ workers first. Deferred because the current deployment can
   prove daily scheduled publish without a separate worker service.
3. Leave refresh manual only. Rejected because production catalog freshness
   needs an unattended path before demo usage grows.
4. Use an unprotected endpoint with an obscure URL. Rejected because the route
   mutates production catalog state.

## Consequences

Positive:

- Production can refresh the active Postgres catalog from the deployed
  validated snapshot on a schedule.
- Every scheduled publish still creates durable audit rows.
- Bad snapshots fail closed and do not activate.
- The route has no customer UI and requires `CRON_SECRET`.

Tradeoffs:

- This is not yet live Phong Vu scraping.
- Freshness is bounded by the deployed snapshot until a later capture/sync
  story runs public-page collection safely.
- Platform proof now requires both `CRON_SECRET` and a managed Postgres URL in
  production.

## Follow-Up

- Add live public-page capture only after rate-limit and fixture controls are
  selected.
- Add Typesense/pgvector indexing from loaded catalog versions.
- Add an admin publish-history UI after staff/admin auth exists.

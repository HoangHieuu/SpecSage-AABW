# Overview

## Current Behavior

`US-049` records durable `catalog_publish_runs` rows when an operator manually
loads the validated catalog snapshot into Postgres. The deployed API can read
that active catalog version, but there is no scheduled production path that
keeps Postgres aligned with the validated snapshot bundled in a deployment.

## Target Behavior

Vercel Cron invokes a secret-gated backend endpoint once per day. The endpoint
validates the `Authorization: Bearer <CRON_SECRET>` header, resolves the
configured Postgres URL, reads the deployed validated `catalog_snapshot.json`,
and loads it through the existing Postgres catalog publish/audit path.

Successful cron runs record normal `loaded` publish audit rows. Blocked
catalog validation returns a non-2xx response and leaves the active catalog
unchanged through the existing loader behavior.

## Affected Users

- Operators who need unattended proof that production catalog publish refreshes
  are running.
- Developers debugging Vercel/Neon catalog refresh behavior.
- Future catalog-search work that needs a trustworthy scheduled publish base.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0041-secret-gated-catalog-cron-before-live-scraping.md`

## Non-Goals

- Live public-page scraping from the cron endpoint.
- Typesense, pgvector, or embedding index refresh.
- Admin UI for publish history.
- Real Phong Vu/Teko private catalog API access.
- Checkout, promo, or cart integration.

# Overview

## Current Behavior

`US-048` loads a validated JSON catalog snapshot into Postgres and activates one
catalog version for deployed reads. Operators can verify the resulting active
version and SKU row count, but a publish attempt itself is not yet recorded as
a durable audit event.

## Target Behavior

Every Postgres catalog publish records a `catalog_publish_runs` row with the
snapshot version, source, validation counts, SKU count, status, timestamps, load
options, and any blocking or failure text. Successful publishes still activate
exactly one catalog version. Blocked publishes record proof and do not write SKU
rows unless explicitly allowed.

## Affected Users

- Operators publishing the catalog snapshot to Neon.
- Developers debugging catalog refreshes.
- Future scheduled catalog jobs that need run history before automation.

## Affected Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `Data.md`
- `techstack.md`

## Non-Goals

- Scheduled scraping or cron execution.
- Typesense or pgvector indexing.
- Admin UI for catalog runs.
- Real Phong Vu/Teko private catalog API access.
- Checkout, promo, or cart integration.

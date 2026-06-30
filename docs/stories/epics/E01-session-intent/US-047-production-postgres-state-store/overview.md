# Overview

## Current Behavior

`US-010` made sessions, intent revisions, build artifacts, applied build
versions, cart handoffs, and feedback durable in a local SQLite file. The
deployed Vercel API currently falls back to `/tmp` SQLite when no database URL
is configured, which is not durable across serverless instance replacement.

## Target Behavior

The default Agent API chooses PostgreSQL when a production database URL is
present and keeps SQLite as the no-credential local fallback. Production state
for sessions, intent revisions, generated builds, applied build versions, cart
handoffs, feedback, and trace replay survives API restarts and serverless
instance replacement.

## Affected Users

- Customers using a deployed PC Build Copilot session.
- Developers deploying the API to Vercel with a managed Postgres database.
- Operators reviewing generated build feedback and support traces.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/data-strategy.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `techstack.md`
- `Data.md`

## Non-Goals

- Staff login, user accounts, RBAC, checkout, or admin console.
- Catalog migration to Postgres, pgvector, or Typesense.
- Redis session TTL, LangGraph checkpointing, queues, or analytics warehouse.
- Backfilling old local SQLite demo rows into hosted Postgres.

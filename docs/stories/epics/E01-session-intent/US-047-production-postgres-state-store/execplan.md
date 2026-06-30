# Exec Plan

## Goal

Move deployed PC Build Copilot state from demo-only serverless SQLite fallback
to production-capable PostgreSQL while preserving the existing API and local
development behavior.

## Scope

In scope:

- Add a Postgres-backed implementation for existing session and build stores.
- Select Postgres from production database environment variables.
- Keep SQLite as local/no-credential fallback.
- Add tests for selection, schema shape, and existing restart-survival behavior.
- Update product docs, test matrix, and the durable architecture decision.

Out of scope:

- Staff/admin auth or account-linked saved builds.
- Redis TTL and LangGraph checkpointing.
- Catalog migration to Postgres, pgvector, or Typesense.
- Live Phong Vu/Teko commerce integration.
- Migrating old local SQLite demo data.

## Risk Classification

Risk flags:

- Data model.
- External systems.
- Public contracts.
- Existing behavior.
- Weak proof until focused persistence tests pass and platform proof is run.

Hard gates:

- External provider behavior.

The direction is not ambiguous: `techstack.md` names PostgreSQL as the primary
database, existing product docs mark SQLite as local-only, and the current
deployment needs durable state.

## Work Phases

1. Discovery: read stack/data/product docs and current SQLite store contracts.
2. Design: choose managed Postgres on Vercel/Neon for current deployment and
   defer larger AWS/RDS/catalog/search infrastructure.
3. Validation planning: define selector, fallback, schema, and platform checks.
4. Implementation: add Postgres store, persistence selector, dependency, and
   focused tests.
5. Verification: run focused persistence tests, full `pnpm check`, and harness
   story verification.
6. Harness update: record intake, story, matrix, and decision rows.

## Stop Conditions

Pause for human confirmation if:

- A live database URL is required to finish platform proof.
- Existing deployed data must be migrated from SQLite instead of starting fresh.
- The target database provider changes from managed Vercel/Neon Postgres.
- Validation requirements need to be weakened.

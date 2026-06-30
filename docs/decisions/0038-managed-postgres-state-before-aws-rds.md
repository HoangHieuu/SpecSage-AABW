# 0038 Managed Postgres State Before AWS RDS

Date: 2026-06-30

## Status

Accepted

## Context

`US-010` intentionally chose SQLite as a no-credential local bridge before
production database work. The app is now deployed on Vercel, and the SQLite
fallback uses serverless instance storage when no database URL is configured.
That is acceptable for a demo process restart, but not for real product
sessions, build history, approval handoffs, feedback, or trace replay.

`techstack.md` names PostgreSQL 16 as the primary database and Redis as the
future session/checkpoint cache. The current deployment target makes a managed
Postgres URL through Vercel Marketplace or Neon the smallest durable step. An
AWS ECS/RDS move would introduce broader infrastructure work before the current
web/API product path needs it.

## Decision

Use managed PostgreSQL as the production state store before moving the backend
to AWS RDS.

The Agent API selects Postgres when one of these environment variables is
present:

- `DATABASE_URL`
- `POSTGRES_URL`
- `POSTGRES_URL_NON_POOLING`

Without those variables, the API keeps the existing local SQLite fallback.

The Postgres store persists the current session/build domain objects in these
tables:

- `build_sessions`
- `intent_revisions`
- `build_artifacts`
- `cart_handoffs`
- `build_feedback`

Each table keeps query-critical metadata columns plus a full Pydantic
`payload_json jsonb` column so the HTTP response contract and trace replay
behavior remain unchanged.

## Alternatives Considered

1. Keep `/tmp` SQLite on Vercel. Rejected because state can disappear when a
   serverless instance is replaced.
2. Move immediately to AWS RDS. Deferred because it expands the deployment
   footprint while the current product is already hosted on Vercel.
3. Add Redis first. Rejected because Redis is a TTL/cache/checkpoint layer, not
   the durable source for build artifacts, approvals, and feedback.
4. Migrate catalog/search into Postgres and Typesense now. Deferred because
   catalog breadth/search is a separate Phase 2 data problem.

## Consequences

Positive:

- Hosted sessions, generated builds, handoffs, feedback, and traces can survive
  serverless instance replacement.
- Local development still works with no external credentials.
- The API shape and deterministic product rules remain unchanged.
- The schema is compatible with later account history, retention, and analytics
  work.

Tradeoffs:

- Platform proof now requires a real managed Postgres URL.
- SQLite demo rows are not automatically migrated.
- Redis TTL, LangGraph checkpointing, catalog database, pgvector, and Typesense
  remain future stories.

## Follow-Up

- Configure Vercel/Neon Postgres and set `DATABASE_URL` for production.
- Redeploy and record platform proof for `US-047`.
- Add explicit retention/deletion rules before introducing accounts or PII.
- Add Redis/checkpointing only after the multi-agent runtime needs recoverable
  intermediate graph state.

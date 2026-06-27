# 0011 Local SQLite Product State Before Postgres

Date: 2026-06-27

## Status

Accepted

## Context

The stack direction names PostgreSQL and Redis for production session,
checkpoint, catalog, and audit state. The current hackathon app has working
FastAPI and Next.js slices, but sessions, intent revisions, build artifacts,
applied variants, and mock cart handoffs are still in memory. That means a
local API restart loses demo progress and blocks a credible future LangGraph
orchestration layer.

The user has not provisioned a Postgres instance or database credentials yet.
`Data.md` explicitly lists SQLite as a valid local storage option for the
hackathon path.

## Decision

Use a local SQLite file as the first product durable store for `US-010`.

The SQLite implementation stores full Pydantic payload JSON for:

- `build_sessions`
- `intent_revisions`
- `build_artifacts`
- `cart_handoffs`

The default Agent API app uses the SQLite store without requiring credentials.
Tests can still inject in-memory stores for isolated behavior. The local DB
path can be overridden with `PC_BUILD_COPILOT_DB_PATH`.

PostgreSQL remains the target production database for later LangGraph
checkpointing, saved builds, catalog/search expansion, and multi-user account
history.

## Alternatives Considered

1. Keep in-memory state until LangGraph. Rejected because process restart
   survival is a demo reliability requirement and a prerequisite for meaningful
   orchestration.
2. Require PostgreSQL now. Rejected because it adds credentials and local setup
   friction before the product needs multi-user or production database features.
3. Store state in browser localStorage only. Rejected because the Agent API must
   own build artifacts, compatibility proof, and handoff state.

## Consequences

Positive:

- Demo state survives local API process restart.
- No external credentials are needed.
- The API contract remains unchanged.
- Future Postgres work can migrate from the same logical tables.

Tradeoffs:

- SQLite is local-only and not a production multi-user store.
- Payload JSON is simple and robust for this slice, but it is not ideal for
  advanced querying or analytics.
- A later Postgres story will need migration/export logic if demo state must be
  preserved.

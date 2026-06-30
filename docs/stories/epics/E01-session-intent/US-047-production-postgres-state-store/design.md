# Design

## Domain Model

This story does not add new customer-facing entities. It moves the existing
state entities behind a production-capable store:

- `BuildSession`
- `IntentRevision`
- `BuildArtifact`
- `CartReadyHandoff`
- `BuildFeedback`

Compatibility, budget, add-on selection, review queue, and approval rules stay
inside the existing deterministic code paths.

## Application Flow

The FastAPI app creates stores through `create_persistent_stores()`:

1. If `DATABASE_URL`, `POSTGRES_URL`, or `POSTGRES_URL_NON_POOLING` is present,
   use the Postgres stores.
2. Otherwise use the existing SQLite stores.

Tests can still inject `SessionStore`, `BuildStore`, `SqliteSessionStore`, or
`SqliteBuildStore` directly.

## Interface Contract

No HTTP routes, request DTOs, response DTOs, or error strings change.

The existing routes continue to read and write through the store interfaces:

- `POST /sessions`
- `POST /sessions/{build_session_id}/intent`
- `GET /sessions/{build_session_id}`
- `GET /sessions/{build_session_id}/intent-revisions`
- `POST /sessions/{build_session_id}/generate`
- `GET /sessions/{build_session_id}/trace`
- `GET /builds/{build_id}`
- `GET /builds/{build_id}/trace`
- `GET /builds/{build_id}/alternatives`
- `POST /builds/{build_id}/alternatives/{variant_id}/apply`
- `POST /builds/{build_id}/iterate`
- `POST /builds/{build_id}/approve`
- `POST /builds/{build_id}/feedback`
- `GET /builds/{build_id}/feedback`
- `GET /feedback/review-queue`

## Data Model

Postgres tables:

- `build_sessions`
  - Primary key: `build_session_id`
  - Metadata columns: state and timestamps.
  - Full payload: `payload_json jsonb`.
- `intent_revisions`
  - `sequence_id bigserial` preserves insertion order.
  - `revision_id` unique.
  - Foreign key to `build_sessions`.
  - Indexes for session revision replay and latest confirmed revision lookup.
- `build_artifacts`
  - Primary key: `build_id`.
  - Foreign key to `build_sessions`.
  - Index for session trace replay by build version and generated timestamp.
- `cart_handoffs`
  - Primary key: `handoff_id`.
  - Unique `build_id` preserves approval idempotency.
  - Foreign keys to build and session.
  - `selected_addon_skus jsonb` stores the idempotency input separately.
- `build_feedback`
  - Primary key: `feedback_id`.
  - Foreign keys to build and session.
  - Indexes for feedback-by-build, feedback-by-session, and queued review rows.

All full Pydantic domain payloads are stored as `jsonb` to preserve the
existing replay and response contract while metadata columns support common
queries. Foreign keys use `ON DELETE CASCADE`, but this story introduces no
customer-facing delete operation and no data migration from SQLite.

## UI / Platform Impact

No UI changes. On Vercel, the project needs a managed Postgres URL in the
backend environment and a redeploy before hosted sessions are durable.

## Observability

No new telemetry provider is added. Platform proof should verify that the
deployed API can connect to the configured database and that a session can be
created and read after redeploy.

## Alternatives Considered

1. Keep `/tmp` SQLite on Vercel. Rejected because serverless instance storage
   is not product-durable.
2. Move immediately to AWS ECS and RDS. Deferred because the deployed app is
   already on Vercel and the smallest production data step is a managed
   Postgres URL.
3. Use Redis only. Rejected because generated build artifacts, handoffs, and
   feedback need durable relational history before TTL cache behavior.
4. Migrate the catalog to Postgres now. Deferred because this story is about
   customer session/build state, not catalog breadth or search.

# US-010 Persistent Session and Build Store

## Status

implemented

## Lane

normal

## Product Contract

Build sessions, intent revisions, generated builds, applied build versions, and
mock cart handoffs survive Agent API process restart in local development. The
API contract remains unchanged, and the local durable store must require no
external credentials.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/data-strategy.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `Data.md`
- `techstack.md`

## Acceptance Criteria

- Default Agent API app uses a local SQLite file for sessions and builds.
- Tests can still inject in-memory stores for isolated unit/integration proof.
- `POST /sessions`, `POST /sessions/{id}/intent`,
  `GET /sessions/{id}`, and `GET /sessions/{id}/intent-revisions` read/write
  persisted data.
- `POST /sessions/{id}/generate`, `GET /builds/{id}`,
  `GET /builds/{id}/alternatives`,
  `POST /builds/{id}/alternatives/{variant_id}/apply`, and
  `POST /builds/{id}/approve` read/write persisted build and handoff data.
- Existing approval idempotency still works after re-instantiating the store.
- Missing session/build/variant behavior remains unchanged.
- Local database files are ignored by git.

## Design Notes

- Commands: no user-facing runtime command; `PC_BUILD_COPILOT_DB_PATH` can
  override the local SQLite path.
- Queries: key-value style table lookups by session, revision, build, and
  handoff IDs.
- API: no endpoint shape changes.
- Tables: `build_sessions`, `intent_revisions`, `build_artifacts`,
  `cart_handoffs`.
- Domain rules: compatibility, budget, approval, and cart gates remain
  deterministic and unchanged.
- UI surfaces: no new visible surface; browser proof verifies the existing flow
  continues against persistent stores.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-010 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | SQLite stores round-trip Pydantic session/build/handoff models |
| Integration | Re-instantiated FastAPI apps can fetch sessions, revisions, builds, applied variants, and idempotent handoffs from the same SQLite file |
| E2E | Browser happy path still generates, applies, and approves a build with the default persistent API |
| Platform | Not required; no external DB or deployment target added |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-010` |

## Harness Delta

No harness behavior change expected.

## Evidence

- `.venv/bin/python -m pytest services/agent-api/tests/test_sqlite_persistence.py`
  passed: SQLite restart-survival tests cover sessions, intent revisions, build
  artifacts, applied variants, idempotent handoffs, and
  `PC_BUILD_COPILOT_DB_PATH`.
- `pnpm check` passed: Next.js production build plus 55 Agent API tests.
- `scripts/bin/harness-cli story verify US-010` passed with the same release
  proof.
- Browser E2E against the default persistent API passed: started a session,
  parsed Vietnamese intent with the OpenRouter advisor available, generated a
  compatible 7-SKU build, applied the RAM upgrade as build version 2, approved
  the applied build, and rendered a mock cart handoff with total
  `17.890.000 VND`, 7 SKUs, and upgraded RAM SKU `240601032`.
- Playwright network proof showed 200 responses for `/sessions`,
  `/sessions/{id}/intent`, `/sessions/{id}/generate`,
  `/builds/{id}/alternatives`, `/builds/{id}/alternatives/{variant_id}/apply`,
  and `/builds/{id}/approve`.
- Mobile browser proof at 390px viewport had no horizontal overflow
  (`scrollWidth` = `clientWidth`); console output only had the expected missing
  favicon 404 in dev.
- Local SQLite proof after the browser flow contained 1 session, 2 intent
  revisions, 2 build artifacts, and 1 cart handoff.

# Validation

## Proof Strategy

The story is done when the app selects Postgres in production configuration,
keeps local SQLite behavior unchanged, preserves API persistence semantics, and
documents the platform step needed for Vercel deployment.

Unit and integration proof do not require a live hosted database. Platform
proof requires a real managed Postgres connection string and should be recorded
after `DATABASE_URL` or an equivalent Vercel Postgres URL is configured.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Persistence selector prefers `DATABASE_URL`; selector falls back to SQLite without Postgres env; Postgres schema uses `jsonb`, `timestamptz`, and indexed review queue/session paths. |
| Integration | Existing SQLite restart-survival tests still pass; feedback and trace replay continue to work through persisted build artifacts. |
| E2E | Existing browser flow remains unchanged after production database selection work. |
| Platform | Configure managed Postgres on Vercel, redeploy, create a session, reload/read it from the deployed API, and verify no `/tmp` SQLite fallback is used. |
| Performance | No new load target; indexes cover session replay, latest confirmed revision, build lookup, and queued feedback scans. |
| Logs/Audit | No new audit table; no secrets are logged or committed. |

## Fixtures

- Existing catalog snapshot and API test fixtures.
- Optional live managed Postgres database URL stored only in local/Vercel
  environment variables.

## Commands

```text
.venv/bin/python -m pytest services/agent-api/tests/test_persistence_selection.py services/agent-api/tests/test_sqlite_persistence.py services/agent-api/tests/test_build_feedback.py services/agent-api/tests/test_trace_replay.py
pnpm check
scripts/bin/harness-cli story verify US-047
```

## Acceptance Evidence

- Focused persistence tests passed: selector, schema contract, SQLite restart
  survival, feedback persistence, and trace replay.
- `pnpm check` passed with the Next.js production build and 136 Agent API
  tests.
- `scripts/bin/harness-cli story verify US-047` passed with focused
  persistence tests plus `pnpm check`.
- Platform proof passed after configuring production `DATABASE_URL` on Vercel
  and redeploying: `POST /api/sessions` on
  `https://specsage-aabw.vercel.app` created session
  `bs_4b9d176c15f741009d260ccd6824faed`, and the same row was found in Neon
  `build_sessions` with state `created`.

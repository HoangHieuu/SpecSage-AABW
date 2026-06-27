# US-012 Agent Trace Session Replay Foundation

## Status

implemented

## Lane

normal

## Product Contract

Engineers can replay agent decisions for a generated session from local product
state. The trace is linked to `build_session_id` and build version, includes
agent name, redacted inputs, tool-call labels, outputs, local latency, and
model/runtime version metadata, and provides a support-export text payload.

This is a local hackathon observability foundation. It does not require
Langfuse credentials and does not move SKU, budget, compatibility, performance,
approval, or cart handoff decisions into an LLM.

## Relevant Product Docs

- `SPEC.md` Phase 11 / `US-11.1 Agent Trace & Session Replay`
- `techstack.md` Phase 11 observability recommendation
- `tools.md` Langfuse MCP observability note
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/decisions/0012-langgraph-build-orchestration-before-autonomous-optimization.md`

## Acceptance Criteria

- `GET /builds/{build_id}/trace` returns replay events for that build.
- `GET /sessions/{build_session_id}/trace` returns replay events grouped by
  build version and linked to the session id.
- Replay events include agent name, redacted inputs, tool-call labels, redacted
  outputs, latency, status, and model/runtime version metadata.
- The response includes a support-export text payload.
- The web app renders a trace replay panel after build generation.
- PII-sensitive trace keys and obvious email/phone values are redacted.

## Design Notes

- Commands:
  - `scripts/bin/harness-cli query tools --capability observability --status present`
  - `.venv/bin/python -m pytest services/agent-api/tests/test_trace_replay.py ...`
  - `pnpm check`
- Queries:
  - Harness observability query returned no present Langfuse MCP, so this slice
    stays local.
- API:
  - `GET /builds/{build_id}/trace`
  - `GET /sessions/{build_session_id}/trace`
- Tables:
  - No new table. Replay is derived from persisted `build_artifacts`
    payload JSON so it survives local API restarts without duplicate state.
- Domain rules:
  - Replay is diagnostic metadata only. Deterministic build gates remain the
    authority for SKU, price, budget, compatibility, workload fit, approval,
    alternatives, and handoff.
- UI surfaces:
  - `Trace replay` panel in the generated build view.
  - Support trace copy action.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-012 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Trace replay builder returns event metadata and redacts sensitive payloads |
| Integration | Build/session trace endpoints return build-version-linked replay data; SQLite replay survives app restart |
| E2E | Browser flow generates a build and renders `Trace replay` with six events and export action |
| Platform | Not required; Langfuse remains a later keyed integration |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-012` |

## Harness Delta

No Harness CLI change. The trace record for this story should note that
observability MCP capability was absent, so local replay was implemented before
external Langfuse integration.

## Evidence

- `scripts/bin/harness-cli query tools --capability observability --status present`
  returned no present observability tool, so local replay was selected before
  Langfuse integration.
- `.venv/bin/python -m pytest services/agent-api/tests/test_trace_replay.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_sqlite_persistence.py`
  passed with 28 tests.
- `pnpm check` passed with Next.js build and 61 API tests.
- `scripts/bin/harness-cli story verify US-012` passed with the same release
  check.
- Browser QA on `http://127.0.0.1:3000/` generated a 25M VND gaming build and
  rendered `Trace replay` with `1 build / 6 event`, Catalog through Validator
  events, tool-call labels, model/runtime metadata, redacted payload details,
  and a support-export copy button that reached `Đã copy trace`.
- Browser console check reported no errors or warnings. Current desktop
  viewport and 390px mobile viewport had no page-wide horizontal overflow
  (`scrollWidth` = `clientWidth`) and no framework runtime overlay.
- Screenshots:
  - `/tmp/specsage-us012-trace-replay-desktop.png`
  - `/tmp/specsage-us012-trace-replay-mobile.png`

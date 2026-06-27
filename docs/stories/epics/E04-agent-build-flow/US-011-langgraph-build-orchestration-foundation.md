# US-011 LangGraph Build Orchestration Foundation

## Status

implemented

## Lane

normal

## Product Contract

Build generation runs through a LangGraph `StateGraph` with named agent steps
for catalog, optimizer, compatibility, performance, explainer, and validator
responsibilities. The graph preserves the existing deterministic SKU selection,
compatibility, budget, workload fit, explanations, approval gate, and API shape.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `SPEC.md`
- `techstack.md`
- `Data.md`

## Acceptance Criteria

- `POST /sessions/{id}/generate` uses the LangGraph orchestration service
  instead of calling the deterministic build generator directly.
- Generated build artifacts include an orchestration trace with ordered,
  schema-valid agent step records.
- Agent step names cover `catalog`, `optimizer`, `compatibility`,
  `performance`, `explainer`, and `validator`.
- The graph may only use local catalog snapshot SKUs and deterministic
  compatibility/performance outputs.
- Existing generated build totals, SKU choices, budget status, workload fit,
  alternatives, apply, approval, and SQLite persistence behavior remain
  compatible with `US-004` through `US-010`.
- Provider calls, LangGraph checkpointing, PostgreSQL, Redis, OR-Tools, staff
  surfaces, auth, and real checkout remain out of scope.

## Design Notes

- Commands: `generate_build_with_orchestration(...)` wraps the existing
  deterministic generator.
- Queries: no new catalog query endpoint.
- API: no endpoint shape change; `BuildArtifact.orchestration_trace` adds
  optional build metadata to existing JSON.
- Tables: no schema migration; SQLite stores full Pydantic build JSON.
- Domain rules: compatibility, PSU, RAM, clearance, stock, and budget gates
  remain code paths, not LLM decisions.
- UI surfaces: no new controls; browser proof can inspect generated build JSON
  or continue using the existing generated build UI.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-011 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | LangGraph service returns the expected agent sequence and preserves deterministic build output |
| Integration | Generate endpoint returns `orchestration_trace` and existing alternatives/apply/approve flows still work |
| E2E | Browser flow still generates a visible build from Vietnamese intent through the default app |
| Platform | Not required; no deployment or provider behavior added |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-011` |

## Harness Delta

No harness behavior change expected.

## Evidence

- Context7 LangGraph docs were checked for current `StateGraph`, `START`,
  `END`, `compile()`, and `invoke()` API usage.
- `.venv/bin/python -m pytest services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_sqlite_persistence.py`
  passed: focused graph, generation, alternatives/apply/approve, and SQLite
  persistence proof.
- `pnpm check` passed: Next.js production build plus 57 Agent API tests.
- `scripts/bin/harness-cli story verify US-011` passed with the same release
  proof.
- Browser E2E against local dev servers passed: Vietnamese intent analyzed and
  confirmed, build generated through API, `Agent orchestration` panel rendered
  with 6 LangGraph steps, total remained `17.190.000 VND`, API requests returned
  200, and console had no errors or warnings.
- Mobile browser proof at 390px viewport had no horizontal overflow
  (`scrollWidth` = `clientWidth`) and the trace panel rendered as a single-column
  sequence.

# US-035 Phase 5 Multi-Agent Optimizer Loop Foundation

## Status

implemented

## Lane

normal

## Product Contract

Build generation should expose a bounded optimizer loop that behaves like a
deterministic Phase 5 agent rather than a hidden helper function. The loop must
derive a use-case budget allocation plan, recognize priority overrides from
confirmed Vietnamese intent, evaluate candidate swaps, and record why each
iteration was accepted or rejected.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0036-config-driven-optimizer-loop-before-pareto-search.md`
- `docs/stories/epics/E05-build-iteration/US-029-budget-aware-optimizer-improvement-pass.md`
- `docs/stories/epics/E05-build-iteration/US-033-bounded-multi-swap-optimizer-search.md`
- `docs/stories/epics/E05-build-iteration/US-034-benchmark-delta-gaming-alternative-ranking.md`

## Acceptance Criteria

- Optimizer behavior is driven by a use-case allocation config instead of only
  implicit branch logic.
- Confirmed intent can record priority overrides for GPU, quiet operation, and
  RGB/aesthetic preference.
- The build artifact includes `optimizer_trace` with max iterations, budget
  allocation, priority overrides, and per-iteration decisions.
- The LangGraph optimizer step reports accepted/rejected iteration counts and
  priority override count.
- Existing deterministic gates remain in force: catalog SKUs only,
  compatibility rules in code, budget gate, benchmark-only numeric claims, and
  benchmark-preserving gaming auto-swap guard.
- The web UI renders the optimizer loop so demo viewers can inspect the
  allocation and decision trail.

## Design Notes

- Commands: no new runtime command.
- Queries: no external query; use local catalog snapshot and benchmark evidence.
- API: `BuildArtifact` gains typed `optimizer_trace` metadata.
- Tables: no schema change; existing artifact JSON persistence carries the new
  model.
- Domain rules: priority overrides can boost ranking/trace decisions, but cannot
  bypass compatibility, budget, or gaming benchmark gates.
- UI surfaces: generated build view shows optimizer strategy and iteration
  decisions.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-035 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Optimizer trace includes allocation config, priority overrides, and accepted/rejected candidate decisions |
| Integration | LangGraph optimizer step exposes optimizer-loop counts without changing generated build safety gates |
| E2E | Covered by `US-036` |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-035` |

## Harness Delta

Adds `US-035` and decision `0036` to the Phase 5 build iteration contract.

## Evidence

- `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_demo_e2e_flow.py` passed with 39 tests.
- `pnpm check` passed with Next.js build and 108 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-035` passed.

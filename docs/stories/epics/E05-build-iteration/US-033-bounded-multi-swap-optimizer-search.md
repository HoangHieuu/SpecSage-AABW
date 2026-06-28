# US-033 Bounded Multi-Swap Optimizer Search

## Status

implemented

## Lane

normal

## Product Contract

Generated builds can apply a small deterministic optimizer search of up to two
eligible alternatives before returning. Each applied variant must remain within
budget, pass compatibility, and be rebuilt through the normal artifact path.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0034-bounded-two-swap-optimizer-before-full-search.md`
- `docs/stories/epics/E05-build-iteration/US-029-budget-aware-optimizer-improvement-pass.md`
- `docs/stories/epics/E05-build-iteration/US-031-benchmark-preserving-gaming-gpu-optimizer-guard.md`

## Acceptance Criteria

- Creator generation can apply RAM and SSD upgrades in sequence when both are
  ranked eligible and budget-safe.
- AI/local LLM generation can apply NVIDIA GPU and RAM upgrades in sequence
  when both are ranked eligible and budget-safe.
- Streaming generation can still stop after one CUDA-relevant GPU swap when no
  second recommended swap is eligible.
- Gaming generation uses the stricter benchmark-preserving GPU guard from
  `US-031`.
- Each applied swap reruns compatibility, budget, performance profile,
  warnings, explanations, mock cart payload, and orchestration trace metadata.
- The optimizer remains bounded; it does not run full combinatorial search,
  external solvers, or LLM SKU selection.

## Design Notes

- Commands: no new runtime command.
- Queries: no external query; reuse generated artifact plus ranked alternatives.
- API: same `POST /sessions/{build_session_id}/generate` response shape.
- Tables: no new persistence.
- Domain rules: at most two swaps, each one selected from deterministic ranked
  alternatives and rebuilt before the next pass.
- UI surfaces: existing build explanations show one optimizer note per applied
  swap.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-033 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Generator applies creator RAM+SSD and AI GPU+RAM sequences while streaming stops after one eligible swap |
| Integration | Orchestration and SQLite persistence still store generated artifacts and traces after optimizer changes |
| E2E | Not required; response shape is unchanged |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-033` |

## Harness Delta

Adds `US-033` to E05 Build Iteration and decision `0034`.

## Evidence

- Focused benchmark/build/orchestration/persistence tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_performance_benchmarks.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_sqlite_persistence.py`
- `pnpm check` passed with Next.js production build and 104 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-033` passed.

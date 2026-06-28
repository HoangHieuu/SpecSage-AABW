# US-029 Budget-Aware Optimizer Improvement Pass

## Status

implemented

## Lane

normal

## Product Contract

Generated creator, AI, and streaming builds run a bounded deterministic
improvement pass before being returned. The pass starts from the cheapest
compatible build, evaluates ranked alternatives from the same catalog snapshot,
and applies one `recommended` variant only when it remains compatible and within
budget. Gaming, office, and student generation stay unchanged in this slice.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0030-one-swap-budget-optimizer-before-full-search.md`
- `docs/stories/epics/E05-build-iteration/US-028-performance-aware-alternative-ranking.md`

## Acceptance Criteria

- Generated creator builds can auto-apply the recommended RAM upgrade when the
  budget supports it.
- Generated streaming builds can auto-apply the recommended NVIDIA/CUDA swap
  when the budget supports it.
- Generated AI/local LLM builds can auto-apply a recommended workload swap when
  the budget supports it.
- Gaming benchmark-backed builds do not auto-swap to GPUs without benchmark
  evidence in this slice.
- Optimized builds rerun compatibility, budget, performance profile, warnings,
  explanations, mock cart payload, and orchestration trace fields.
- Optimizer explanations remain Vietnamese and grounded in deterministic
  ranking reasons.

## Design Notes

- Commands: no new runtime command.
- Queries: no external query; reuse generated artifact plus ranked alternatives.
- API: same `POST /sessions/{build_session_id}/generate` response shape.
- Tables: no new persistence.
- Domain rules: one-swap, recommended-only, budget-safe, compatibility-safe.
- UI surfaces: existing build explanations show optimizer notes.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-029 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Generator applies creator RAM and streaming NVIDIA recommended swaps; raw profile tests can disable optimizer |
| Integration | Generate endpoint still returns stored, approvable artifacts and low-budget artifacts remain blocked |
| E2E | Not required; response shape is unchanged and existing UI renders explanations generically |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-029` |

## Harness Delta

Adds `US-029` to E05 Build Iteration and decision `0030`.

## Evidence

- Focused build/orchestration/persistence tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_sqlite_persistence.py`
- `pnpm check` passed with Next.js production build and 100 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-029` passed.

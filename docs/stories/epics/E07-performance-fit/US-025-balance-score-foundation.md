# US-025 Balance Score Foundation

## Status

implemented

## Lane

normal

## Product Contract

Generated builds include a deterministic balance score that explains CPU, GPU,
RAM, and storage balance without changing SKU selection. Severe imbalance is
reported as `PERF_IMBALANCE`.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0026-balance-score-before-optimizer-weighting.md`

## Acceptance Criteria

- `BuildArtifact.performance_profile.balance` returns a 0-100 score,
  Vietnamese interpretation, limiting component, factor values, and upgrade
  suggestions when required catalog facts exist.
- Generated build UI renders the balance score in the existing workload fit
  panel.
- Severe imbalance raises `PERF_IMBALANCE` in performance warnings and generated
  build warnings.
- The score is deterministic and based on catalog/build artifact fields, not LLM
  output.
- This slice does not alter SKU selection, alternatives ranking, or approval
  gates.

## Design Notes

- Commands: no new runtime command.
- Queries: no external query; score uses selected SKU facts already in memory.
- API: optional `PerformanceProfile.balance`.
- Tables: none.
- Domain rules: formula uses CPU core/thread factor, GPU chipset/VRAM factor,
  RAM capacity factor, and storage interface/capacity factor.
- UI surfaces: existing `Workload fit` panel.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-025 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Generator returns normal balance score and severe imbalance warning |
| Integration | Generate endpoint returns `performance_profile.balance` |
| E2E | Not required; UI rendering covered by `pnpm check:web` |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-025` |

## Harness Delta

Adds `US-025` to E07 Performance Fit and decision `0026`.

## Evidence

- Focused backend tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_trace_replay.py`
- Frontend type/build check passed: `pnpm check:web`.
- `pnpm check` passed with Next.js production build and 90 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-025` passed.

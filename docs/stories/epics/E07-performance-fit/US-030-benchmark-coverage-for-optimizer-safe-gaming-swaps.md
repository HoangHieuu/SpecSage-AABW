# US-030 Benchmark Coverage for Optimizer-Safe Gaming Swaps

## Status

implemented

## Lane

normal

## Product Contract

The gaming benchmark matrix expands only with source-backed exact rows so future
gaming optimizer swaps do not hide below-target warnings. For active GPU
candidates, a generated build must still show benchmark evidence and
`PERF_BELOW_TARGET` when the selected GPU is below the requested high-refresh
target.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0024-local-benchmark-matrix-before-performance-claims.md`
- `docs/decisions/0031-benchmark-coverage-before-gaming-gpu-auto-swaps.md`

## Acceptance Criteria

- The benchmark matrix includes a source-backed RTX 4060 row for Cyberpunk 2077
  1440p Ultra native.
- Exact lookup returns RTX 4060 1440p Ultra evidence with source label and URL.
- A generated gaming build that selects RTX 4060 for Cyberpunk 2077 1440p Ultra
  144Hz emits benchmark evidence and `PERF_BELOW_TARGET`.
- No interpolation, LLM FPS estimate, or unsupported FPS claim is added.
- Gaming optimizer auto-swaps remain out of scope until benchmark evidence can
  be preserved for the requested target.

## Design Notes

- Commands: no new runtime command.
- Queries: no runtime external query; source data is curated into the local
  JSON matrix.
- API: unchanged; evidence still appears in `PerformanceProfile.evidence`.
- Tables: `services/agent-api/benchmarks/gaming_benchmark_matrix.json`.
- Domain rules: exact-match benchmark lookup only.
- UI surfaces: existing workload fit evidence links render the source URL.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-030 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Benchmark matrix loads and RTX 4060 1440p Ultra lookup returns source-backed evidence |
| Integration | Build generation emits RTX 4060 benchmark evidence and below-target warning |
| E2E | Not required; UI evidence rendering is unchanged |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-030` |

## Harness Delta

Adds `US-030` to E07 Performance Fit and decision `0031`.

## Evidence

- Focused benchmark/build tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_performance_benchmarks.py services/agent-api/tests/test_build_generation.py`
- `pnpm check` passed with Next.js production build and 102 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-030` passed.

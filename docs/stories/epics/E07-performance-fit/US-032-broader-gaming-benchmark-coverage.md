# US-032 Broader Gaming Benchmark Coverage

## Status

implemented

## Lane

normal

## Product Contract

The gaming benchmark matrix can expand only with source-backed exact rows.
Broader coverage improves optimizer safety and workload evidence without
introducing interpolation, LLM estimates, or unsupported FPS claims.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0024-local-benchmark-matrix-before-performance-claims.md`
- `docs/decisions/0033-source-backed-benchmark-coverage-before-broader-fps-claims.md`

## Acceptance Criteria

- The benchmark matrix includes a source-backed RX 7600 row for Cyberpunk 2077
  1080p Ultra native.
- Exact lookup returns RX 7600 1080p Ultra evidence with source label and URL.
- Unsupported resolutions remain unsupported instead of falling back to nearby
  rows.
- Generated builds can show the new evidence when the selected GPU, game,
  resolution, and preset match exactly.
- No interpolation, LLM FPS estimate, or unsupported FPS claim is added.

## Design Notes

- Commands: no new runtime command.
- Queries: no runtime external query; curated source data lives in the local
  JSON matrix.
- API: unchanged; evidence appears in `PerformanceProfile.evidence`.
- Tables: `services/agent-api/benchmarks/gaming_benchmark_matrix.json`.
- Domain rules: exact-match benchmark lookup only.
- UI surfaces: existing workload fit evidence links render source URLs.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-032 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Benchmark matrix loads four source-backed rows and RX 7600 1080p Ultra lookup succeeds |
| Integration | Build generation emits RX 7600 1080p benchmark evidence for exact matching requests |
| E2E | Not required; UI evidence rendering is unchanged |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-032` |

## Harness Delta

Adds `US-032` to E07 Performance Fit and decision `0033`.

## Evidence

- Focused benchmark/build/orchestration/persistence tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_performance_benchmarks.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_sqlite_persistence.py`
- `pnpm check` passed with Next.js production build and 104 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-032` passed.

# US-023 Benchmark-Backed Gaming Performance Foundation

## Status

implemented

## Lane

normal

## Product Contract

Generated gaming builds may show FPS evidence only when a maintained local
benchmark matrix has an exact match for the selected GPU chipset, target game,
resolution, and preset. Unsupported numeric FPS claims remain blocked.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0024-local-benchmark-matrix-before-performance-claims.md`

## Acceptance Criteria

- A versioned local gaming benchmark matrix exists with source labels, URLs,
  matrix version, and Vietnamese disclaimer.
- Gaming performance lookup returns estimates only when game, GPU chipset,
  resolution, and preset match a matrix row.
- `BuildArtifact.performance_profile.evidence` can include
  `source="benchmark"` FPS evidence with source provenance.
- If a matched benchmark row is below a declared high-refresh target, the
  profile raises a deterministic `PERF_BELOW_TARGET` warning and downgrades fit.
- Existing no-benchmark behavior remains for unmatched requests.
- The web workload-fit panel renders benchmark source links without breaking
  existing catalog/intent/rule evidence.
- Local evals still reject unsupported numeric FPS claims while allowing
  source-backed benchmark evidence.

## Design Notes

- Commands: no new runtime command.
- Queries: no external runtime query; matrix is read from local JSON.
- API: optional `source_label` and `source_url` on `PerformanceEvidence`.
- Tables: `services/agent-api/benchmarks/gaming_benchmark_matrix.json`.
- Domain rules: exact-match benchmark lookup; no interpolation or LLM scoring.
- UI surfaces: existing `Mức phù hợp` evidence grid can display source links.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-023 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Benchmark matrix loading, exact-match lookup, FPS target parsing |
| Integration | Build generation adds benchmark evidence and `PERF_BELOW_TARGET` only on matched rows |
| E2E | Not required for this slice; UI rendering covered by `pnpm check` |
| Platform | Not required; local JSON data only |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-023` |

## Harness Delta

Adds `US-023` to E07 Performance Fit and decision `0024`.

## Evidence

- Focused API tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_performance_benchmarks.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_evaluation_suite.py`
- `pnpm check` passed with Next.js production build and 87 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-023` passed.

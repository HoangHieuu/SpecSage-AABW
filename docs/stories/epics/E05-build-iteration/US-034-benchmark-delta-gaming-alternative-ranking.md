# US-034 Benchmark-Delta Gaming Alternative Ranking

## Status

implemented

## Lane

normal

## Product Contract

Gaming alternatives should use exact source-backed benchmark deltas when both
the base build and candidate build have matching benchmark evidence for the
same target. A GPU alternative with a benchmark-backed lift should rank ahead
of generic storage, RAM, or PSU alternatives for below-target gaming requests.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0035-benchmark-delta-ranking-before-broader-gaming-search.md`
- `docs/stories/epics/E05-build-iteration/US-031-benchmark-preserving-gaming-gpu-optimizer-guard.md`
- `docs/stories/epics/E05-build-iteration/US-033-bounded-multi-swap-optimizer-search.md`

## Acceptance Criteria

- Cyberpunk 2077 1440p Ultra alternatives rank the RTX 4060 GPU swap first
  because the candidate has a higher exact benchmark row than the RX 7600 base.
- Benchmark delta scoring uses only benchmark evidence already present on
  `PerformanceProfile.evidence`.
- Ranking reasons can mention benchmark-backed improvement but must not add
  raw numeric FPS text to generated build explanations.
- Gaming generation still auto-applies a benchmark-preserving GPU swap only
  when the base build is below the declared target.
- Non-gaming alternative ranking remains unchanged except for normal sort order
  from the existing deterministic signals.

## Design Notes

- Commands: no new runtime command.
- Queries: no runtime external query; use local benchmark evidence emitted by
  `performance_profile`.
- API: unchanged alternatives and generate response shapes.
- Tables: no new persistence.
- Domain rules: exact benchmark target comparison only; no interpolation.
- UI surfaces: existing alternative ranking reasons can display the benchmark
  improvement reason.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-034 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Gaming alternatives rank the source-backed RTX 4060 Cyberpunk swap first and ranking reasons avoid raw FPS text |
| Integration | Generation still preserves the `US-031` no-auto-swap behavior when the base benchmark already meets target |
| E2E | Not required; response shapes are unchanged |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-034` |

## Harness Delta

Adds `US-034` to E05 Build Iteration and decision `0035`.

## Evidence

- Focused benchmark/build tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_performance_benchmarks.py`
- `pnpm check` passed with Next.js build and 105 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-034` passed.

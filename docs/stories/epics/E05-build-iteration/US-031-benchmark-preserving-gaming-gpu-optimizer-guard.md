# US-031 Benchmark-Preserving Gaming GPU Optimizer Guard

## Status

implemented

## Lane

normal

## Product Contract

Gaming generation may auto-apply a GPU swap only when the selected alternative
preserves exact benchmark evidence for the requested target. The optimizer must
not auto-apply qualitative gaming swaps or non-GPU gaming variants that could
hide benchmark warnings.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0032-benchmark-preserving-gaming-optimizer-guard.md`
- `docs/stories/epics/E07-performance-fit/US-030-benchmark-coverage-for-optimizer-safe-gaming-swaps.md`

## Acceptance Criteria

- Cyberpunk 2077 1440p Ultra 144Hz generation can auto-swap from RX 7600 to RTX
  4060 only because the RTX 4060 candidate has exact benchmark evidence.
- The optimized gaming build still emits benchmark evidence and
  `PERF_BELOW_TARGET` when the matched FPS is below the declared target.
- Valorant or other gaming requests without candidate benchmark evidence do not
  auto-swap GPUs.
- Gaming requests whose matched benchmark already satisfies the declared target
  do not swap merely because a GPU alternative is compatible and affordable.
- Gaming optimizer auto-apply remains limited to GPU alternatives; storage, RAM,
  and PSU alternatives stay manual alternatives for gaming builds.

## Design Notes

- Commands: no new runtime command.
- Queries: no runtime external query; use local benchmark matrix rows.
- API: unchanged `POST /sessions/{build_session_id}/generate`.
- Tables: no new persistence.
- Domain rules: gaming optimizer requires compatible, within-budget,
  GPU-kind alternative with benchmark evidence and ranking lift.
- UI surfaces: existing build explanations show optimizer notes.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-031 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Build generation tests cover benchmark-preserving gaming swap, no-benchmark no-swap, and already-enough benchmark no-swap |
| Integration | Generated artifact still reruns compatibility, budget, performance, warnings, and explanations after the swap |
| E2E | Not required; response shape is unchanged |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-031` |

## Harness Delta

Adds `US-031` to E05 Build Iteration and decision `0032`.

## Evidence

- Focused benchmark/build/orchestration/persistence tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_performance_benchmarks.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_sqlite_persistence.py`
- `pnpm check` passed with Next.js production build and 104 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-031` passed.

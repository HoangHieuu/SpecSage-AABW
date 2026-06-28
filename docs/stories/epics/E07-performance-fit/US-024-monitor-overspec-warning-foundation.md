# US-024 Monitor Overspec Warning Foundation

## Status

implemented

## Lane

normal

## Product Contract

When a customer asks for a monitor or display target, generated gaming builds
warn if source-backed benchmark evidence is below the requested refresh rate.
The system must not recommend monitor SKUs until active monitor catalog SKUs
are curated and verified.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0025-monitor-overspec-warning-before-monitor-sku-recommendations.md`

## Acceptance Criteria

- Vietnamese or English monitor mentions are captured in `BuildIntent`.
- If a benchmark-backed FPS estimate is below a requested monitor refresh
  target, the performance profile raises `PERF_MONITOR_OVERSPEC`.
- The warning also appears in generated build warnings so approval/review
  surfaces can display it.
- The warning is deterministic and depends on a matched benchmark row, not LLM
  inference.
- No monitor SKU is added to a generated build in this slice.

## Design Notes

- Commands: no new runtime command.
- Queries: no catalog monitor query yet because active monitor SKUs are absent.
- API: no schema change; warning appears in existing `warnings_vi` fields.
- Tables: reuses `services/agent-api/benchmarks/gaming_benchmark_matrix.json`.
- Domain rules: monitor overspec warning is emitted only when benchmark FPS is
  below the requested Hz target and the user mentions monitor/display.
- UI surfaces: existing build and performance warning lists.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-024 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Intent parser captures monitor mentions |
| Integration | Build generation raises `PERF_MONITOR_OVERSPEC` from matched benchmark evidence |
| E2E | Not required; existing warning list renders API warnings |
| Platform | Not required; no external platform added |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-024` |

## Harness Delta

Adds `US-024` to E07 Performance Fit and decision `0025`.

## Evidence

- Focused parser/build tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_intent_parser.py services/agent-api/tests/test_build_generation.py`
- `pnpm check` passed with Next.js production build and 89 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-024` passed.

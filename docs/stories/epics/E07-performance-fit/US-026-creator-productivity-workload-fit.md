# US-026 Creator & Productivity Workload Fit

## Status

implemented

## Lane

normal

## Product Contract

Generated builds include deterministic app-level workload fit profiles for
creator, productivity, streaming, and local LLM workflows. The profiles use
configured thresholds from catalog facts and never invent app benchmark numbers.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0027-config-driven-workload-profiles-before-app-benchmarks.md`

## Acceptance Criteria

- `BuildIntent` captures OBS/streaming and local LLM model classes such as
  `7B`, `13B`, and `70B`.
- `PerformanceProfile.workload_profiles` includes app-fit rows for Premiere,
  After Effects, Photoshop, Blender, OBS/streaming, and local LLM.
- App profiles return fit level, bottleneck labels, requirement summary, and
  recommendation text.
- Creator profiles enforce RAM, VRAM, CPU-thread, and NVMe storage thresholds by
  app.
- Local LLM profiles provide qualitative VRAM tiers for 7B/13B/70B classes.
- Streaming profiles surface NVIDIA/CUDA/encoder preference as an advisory
  warning.
- The slice does not claim render time, token throughput, or benchmark numbers.

## Design Notes

- Commands: no new runtime command.
- Queries: no external query; profiles use selected SKU facts already in memory.
- API: `PerformanceProfile.workload_profiles`.
- Tables: in-code threshold config for this slice.
- Domain rules: deterministic threshold checks, no LLM scoring.
- UI surfaces: existing `Mức phù hợp` panel gains an `Ứng dụng` row list.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-026 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Parser captures streaming apps and LLM model classes |
| Integration | Build generation returns app-fit rows and workload warnings |
| E2E | Not required; UI rendering covered by `pnpm check:web` |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-026` |

## Harness Delta

Adds `US-026` to E07 Performance Fit and decision `0027`.

## Evidence

- Focused parser/build tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_intent_parser.py services/agent-api/tests/test_build_generation.py`
- Frontend type/build check passed: `pnpm check:web`.
- `pnpm check` passed with Next.js production build and 94 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-026` passed.

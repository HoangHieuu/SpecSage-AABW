# US-007 Deterministic Performance Fit Profile

## Status

in_progress

## Lane

normal

## Product Contract

Generated builds include a deterministic qualitative workload fit profile built
from catalog facts and the confirmed `BuildIntent`. The profile may label
workload suitability, bottleneck risk, and upgrade focus, but it must not show
FPS estimates, benchmark deltas, or numeric performance claims until maintained
benchmark tables exist.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- `BuildArtifact` includes `performance_profile` with use case, fit level,
  confidence, evidence facts, fit notes, bottleneck notes, and warnings.
- Gaming builds explain eSports/high-refresh suitability qualitatively from GPU
  VRAM, CPU cores/threads, RAM, and NVMe facts without FPS claims.
- Creator/AI/office profiles use deterministic RAM, VRAM, storage, and GPU
  presence thresholds.
- Profile warnings are included in generated build warnings when they affect
  trust or next-step guidance.
- Frontend renders the performance profile in the generated build view.
- Unit, integration, and browser proof cover the generated profile.

## Design Notes

- Commands: no new runtime command.
- Queries: no new catalog query; the generator uses selected SKU facts already
  available in memory.
- API: `BuildArtifact.performance_profile`.
- Tables: none; benchmark tables remain future Phase 4 scope.
- Domain rules: qualitative only; no LLM and no invented FPS.
- UI surfaces: build panel adds a "Workload fit" section after metrics.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Performance profile tests for gaming, creator, AI, and office thresholds |
| Integration | Generate endpoint returns `performance_profile` |
| E2E | Browser flow displays workload fit after build generation |
| Platform | Not required; no external platform or provider added |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-007` |

## Harness Delta

No harness behavior change expected.

## Evidence

Pending validation.

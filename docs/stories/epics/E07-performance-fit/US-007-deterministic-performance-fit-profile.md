# US-007 Deterministic Performance Fit Profile

## Status

implemented

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

- `pnpm check` passed with Next.js production build and 46 API tests.
- `scripts/bin/harness-cli story verify US-007` passed.
- Playwright browser flow opened the local app, analyzed intent through the
  OpenRouter advisor, confirmed intent, generated a valid 7-SKU build, and
  displayed `Workload fit` with `Phù hợp tốt`, `RX 7600 · 8GB VRAM`, `144Hz`,
  and qualitative fit notes.
- Direct Playwright extraction confirmed the performance profile panel contains
  no `fps` text.
- Mobile viewport check at 390px showed no page-wide horizontal overflow.
- Console had one non-blocking 404 for `/favicon.ico`.

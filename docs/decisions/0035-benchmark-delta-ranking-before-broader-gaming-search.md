# 0035 Benchmark Delta Ranking Before Broader Gaming Search

Date: 2026-06-28

## Status

Accepted

## Context

`US-031` allowed gaming GPU auto-swaps only when exact benchmark evidence is
preserved. The ranking score still treated the GPU swap mostly as a generic
gaming/CUDA preference, so storage and PSU alternatives could outrank a GPU
swap even when exact benchmark rows showed the GPU improved the requested game
target.

## Decision

Add a benchmark-delta score term for gaming GPU alternatives. The term compares
only benchmark evidence already emitted on the base and candidate performance
profiles for the same exact target. Positive deltas increase the ranking score,
with a larger bonus when the base build is below the declared target.

The generated build auto-apply guard remains stricter: gaming generation still
requires the base profile to carry `PERF_BELOW_TARGET` before applying a GPU
swap automatically.

## Alternatives Considered

1. Keep generic gaming bonuses and rely on the auto-apply guard.
2. Parse benchmark matrix rows directly inside the alternative scorer.
3. Show numeric FPS deltas in optimizer explanations.

## Consequences

Positive:

- Gaming alternatives rank GPU swaps by actual source-backed performance
  evidence when available.
- Below-target Cyberpunk 1440p builds prioritize the RTX 4060 swap before
  generic capacity/headroom alternatives.
- The scorer remains offline and deterministic.

Tradeoffs:

- The score still depends on narrow benchmark matrix coverage.
- Ranking reasons intentionally avoid raw FPS text so generated explanations do
  not violate the no-unsupported-FPS eval gate.

## Follow-Up

- Add price-per-FPS and target-satisfaction scoring once the matrix covers more
  active GPU/game combinations.

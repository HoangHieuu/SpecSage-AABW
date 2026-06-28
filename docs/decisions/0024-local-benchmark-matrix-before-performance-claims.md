# 0024 Local Benchmark Matrix Before Performance Claims

## Status

Accepted

## Context

`US-007` intentionally blocked numeric FPS claims because the product only had
catalog specs and qualitative workload rules. Phase 4 still needs a path to
show gaming performance expectations, but the product guardrail remains strict:
LLMs cannot invent FPS, and generated builds must not turn unsupported
performance guesses into customer-facing claims.

## Decision

Add a small local gaming benchmark matrix before showing any numeric FPS
evidence. FPS appears only when the selected GPU chipset, target game,
resolution, and preset match a row in the matrix.

Each matrix row carries:

- Game and GPU aliases for deterministic matching.
- Resolution, preset, render mode, and FPS value/range.
- Source label and URL.
- Matrix version and Vietnamese disclaimer.

The performance profile remains qualitative by default. If no benchmark row
matches, the build shows the existing no-benchmark warning for demanding
requests instead of estimating FPS.

## Consequences

- Numeric FPS evidence is source-backed and auditable.
- `PERF_BELOW_TARGET` can be raised deterministically when a matched benchmark
  row is below a declared high-refresh target.
- The UI can show benchmark source links next to FPS evidence.
- The local quality eval gate still rejects unsupported numeric FPS claims.

## Follow-Ups

- Expand the matrix with more game/GPU/resolution rows only after source review.
- Add benchmark freshness checks before broad public demo claims.
- Add monitor-pairing recommendations after benchmark coverage is broader.

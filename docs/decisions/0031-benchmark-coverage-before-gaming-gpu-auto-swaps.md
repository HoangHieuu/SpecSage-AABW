# 0031 Benchmark Coverage Before Gaming GPU Auto-Swaps

Date: 2026-06-28

## Status

Accepted

## Context

`US-029` intentionally left gaming generation unchanged because a GPU swap can
hide benchmark-backed warnings if the candidate GPU lacks an exact benchmark
row. That would weaken the product guardrail that FPS and high-refresh claims
must come from maintained benchmark evidence.

The local catalog currently has RX 7600 and RTX 4060 GPU choices. The benchmark
matrix already covered Cyberpunk 2077 1440p Ultra for RX 7600 and 1080p Ultra
for RTX 4060, but it did not cover RTX 4060 at 1440p Ultra.

## Decision

Expand the local gaming benchmark matrix before enabling gaming GPU auto-swaps.
Add a source-backed Cyberpunk 2077 1440p Ultra native row for RTX 4060, and
test that generated RTX 4060 builds still emit below-target warnings when the
user asks for 1440p Ultra 144Hz.

Gaming optimizer auto-swaps remain deferred until candidate GPUs can preserve
benchmark evidence for the requested game, resolution, and preset.

## Alternatives Considered

1. Enable gaming GPU swaps and fall back to qualitative warnings.
2. Infer RTX 4060 1440p performance from another resolution.
3. Wait for a large benchmark table before adding any new row.

## Consequences

Positive:

- Future gaming optimizer work can evaluate RTX 4060 without losing warning
  provenance for Cyberpunk 2077 1440p Ultra.
- The benchmark matrix grows incrementally with source labels and URLs.
- Existing exact-match and no-interpolation rules remain intact.

Tradeoffs:

- Coverage is still narrow and game-specific.
- Gaming auto-swaps are still blocked for games or targets without exact rows.

## Follow-Up

- Add more exact rows for the active GPU SKUs and common target games.
- Add a candidate-swap guard that only allows gaming GPU swaps when benchmark
  evidence is preserved for the requested target.

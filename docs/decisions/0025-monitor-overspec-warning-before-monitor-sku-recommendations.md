# 0025 Monitor Overspec Warning Before Monitor SKU Recommendations

## Status

Accepted

## Context

Phase 4 includes monitor pairing, but the active catalog snapshot currently has
no verified monitor SKUs. Broad monitor category captures remain staged and are
not recommendation-eligible. Recommending a monitor SKU now would weaken the
catalog-grounding rule.

The product can still use benchmark-backed FPS evidence to protect users from
buying a display target that the generated PC is unlikely to sustain.

## Decision

Add a warning-only monitor pairing foundation. When a user mentions a monitor
or display and a matched benchmark row is below the requested refresh target,
the performance profile raises `PERF_MONITOR_OVERSPEC`.

Do not add monitor SKUs to generated builds and do not recommend monitor
products until monitor SKUs are promoted into the active catalog with verified
resolution and refresh-rate fields.

## Consequences

- Users get a deterministic warning when a requested monitor target exceeds the
  source-backed performance estimate.
- The system preserves the rule that recommendations use only active,
  verified catalog SKUs.
- Future monitor SKU recommendations have a clear dependency: curated active
  monitor catalog coverage.

## Follow-Ups

- Promote a small reviewed monitor subset from staged captures.
- Add monitor SKU selection only after active monitor SKUs include resolution,
  refresh-rate, panel-size, and price fields.
- Add dual-monitor and ultrawide checks as separate slices.

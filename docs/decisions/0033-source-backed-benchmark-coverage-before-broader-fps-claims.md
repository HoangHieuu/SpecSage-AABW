# 0033 Source-Backed Benchmark Coverage Before Broader FPS Claims

Date: 2026-06-28

## Status

Accepted

## Context

The performance profile may show FPS only from exact local benchmark rows.
Gaming optimizer work benefits from more rows, but adding broad or inferred FPS
coverage would violate the product rule that numeric claims come from catalog,
benchmark, rule, or build artifact fields.

## Decision

Expand the benchmark matrix incrementally with source-backed exact rows only.
Add RX 7600 Cyberpunk 2077 1080p Ultra native evidence from TechSpot, while
keeping unsupported resolutions unsupported.

## Alternatives Considered

1. Interpolate nearby rows such as 1080p to 1440p.
2. Ask an LLM to estimate missing FPS.
3. Wait for a complete matrix before adding any rows.

## Consequences

Positive:

- 1080p Cyberpunk requests using RX 7600 now get source-backed evidence.
- Exact-match lookup rules remain simple and auditable.
- Optimizer guards can rely on local evidence rather than runtime web access.

Tradeoffs:

- Coverage is still narrow.
- Adding rows requires source review and tests.

## Follow-Up

- Continue with common demo targets and active GPU SKUs.
- Prefer sources that report explicit native settings and average FPS.

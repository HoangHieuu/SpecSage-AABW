# 0030 One-Swap Budget Optimizer Before Full Search

Date: 2026-06-28

## Status

Accepted

## Context

The generator originally returned the cheapest compatible build. Phase 5 needs
the base recommendation to use available budget better, but the catalog is
still a curated hackathon snapshot and not broad enough for a full optimizer
loop. A full combinatorial search would also risk hiding benchmark-backed
warnings when a swapped GPU has no maintained benchmark row.

## Decision

Add a bounded one-swap improvement pass before returning generated builds:

- Start from the cheapest compatible build.
- Reuse the deterministic ranked alternatives from `US-028`.
- Auto-apply only the top alternative when it is within budget, approvable, and
  ranked `recommended`.
- Limit this slice to creator, AI, and streaming use cases.
- Keep gaming, office, and student base generation unchanged until their
  optimizer rules have stronger proof and benchmark coverage.

The optimizer writes an explanation note into the build artifact. Approval,
compatibility, budget, and cart handoff gates remain unchanged.

## Alternatives Considered

1. Keep returning only the cheapest compatible build.
2. Auto-apply every `good_fit` alternative until the budget is used.
3. Run a full multi-slot combinatorial optimizer immediately.

## Consequences

Positive:

- Creator and AI/streaming builds use the available budget for clear workload
  improvements.
- The behavior stays explainable and testable with the existing alternatives
  scoring surface.
- Gaming benchmark-backed warnings remain visible until more benchmark rows
  exist.

Tradeoffs:

- The optimizer can apply only one swap per generated build.
- Some leftover budget may remain unused by design.
- Broader gaming/office optimization remains future work.

## Follow-Up

- Add benchmark rows for additional GPUs before gaming GPU auto-swaps.
- Add multi-slot search after catalog coverage and eval scenarios expand.
- Track optimizer decisions as structured fields if product analytics need
  machine-readable optimizer telemetry.

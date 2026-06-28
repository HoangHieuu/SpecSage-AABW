# 0029 Deterministic Alternative Ranking Before Autonomous Optimization

Date: 2026-06-28

## Status

Accepted

## Context

Phase 5 needs better build iteration, but the current snapshot still has a
small curated catalog and no autonomous optimizer loop. Alternatives already
rerun compatibility and performance profiles, but they were shown in generation
order rather than ordered by workload relevance.

The product guardrails require SKU eligibility, budget, compatibility, and
numeric claims to remain deterministic. Ranking should therefore reuse existing
build facts instead of asking an LLM to decide which variant is best.

## Decision

Rank build alternatives with a deterministic local scoring function before
introducing autonomous optimization. The ranking score uses:

- compatibility and budget eligibility
- performance fit changes
- balance score deltas
- app workload fit deltas
- warning deltas
- use-case relevance for RAM, storage, NVIDIA GPU, and PSU headroom swaps

The score is advisory UI metadata. It does not bypass compatibility, approval,
budget, or cart handoff gates.

## Alternatives Considered

1. Keep alternatives in fixed generation order.
2. Ask an LLM to choose the best alternative.
3. Replace the current generator with a full optimizer loop immediately.

## Consequences

Positive:

- Customers see the most relevant variant first.
- Ranking reasons are explainable from existing facts.
- Future optimizer work can reuse the same proof surface.

Tradeoffs:

- The score is heuristic and local to the current curated snapshot.
- It ranks one-slot swaps only; multi-step optimization remains separate work.

## Follow-Up

- Add budget-aware base-build improvement as a separate story.
- Add optimizer weighting only after broader SKU coverage and regression tests
  exist.

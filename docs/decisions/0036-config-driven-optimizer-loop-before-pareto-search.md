# 0036 Config-Driven Optimizer Loop Before Pareto Search

Date: 2026-06-28

## Status

Accepted

## Context

Phase 5 calls for a multi-agent optimizer loop with budget allocation,
natural-language refinement, slot alternatives, and Pareto variants. The current
implementation already has deterministic generation, alternatives, apply flow,
bounded two-swap optimization, LangGraph trace replay, and benchmark-gated
gaming swaps, but the optimizer internals still read like a wrapped function
rather than an inspectable agent loop.

Jumping directly to OR-Tools, provider-backed agents, checkpointers, or parallel
Pareto branches would increase demo risk and make validation harder before the
current deterministic path is fully explainable.

## Decision

Add a config-driven optimizer loop foundation first. The optimizer will compute
use-case budget allocation weights, parse priority overrides from confirmed
intent, record each candidate decision as accepted or rejected, and expose that
trace on the build artifact and UI.

This remains deterministic and bounded. It does not add autonomous LLM
selection, OR-Tools, LangGraph checkpointing, PostgreSQL/Redis checkpointers,
real checkout, staff/admin surfaces, or full Pareto variant generation.

## Alternatives Considered

1. Build the E2E demo before improving the optimizer loop.
2. Implement full Pareto variants and side-by-side comparison immediately.
3. Introduce OR-Tools and a larger solver before exposing current decisions.

## Consequences

Positive:

- Phase 5 behavior becomes inspectable and demoable without weakening safety
  gates.
- Budget allocation and priority overrides become explicit product contract
  fields rather than hidden scoring heuristics.
- Future Pareto and refinement stories can reuse the same optimizer trace model.

Tradeoffs:

- This is still a foundation, not full Phase 5 completion.
- Some priority overrides may be recorded but not auto-applied when existing
  benchmark, compatibility, or catalog gates block them.

## Follow-Up

- Add natural-language `/iterate` commands after the optimizer trace is stable.
- Add Best Value, Balanced, and Best Performance variants once candidate
  coverage and comparison fields are broader.

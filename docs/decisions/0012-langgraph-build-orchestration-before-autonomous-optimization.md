# 0012 LangGraph Build Orchestration Before Autonomous Optimization

Date: 2026-06-27

## Status

Accepted

## Context

The product contract calls for a multi-agent PC advisory workflow, and
`techstack.md` recommends LangGraph for Phase 5 orchestration. The current
build path already has deterministic catalog grounding, compatibility rules,
performance fit, alternatives, approval gates, and local persistence. Replacing
that working path with a broad autonomous optimizer would add risk before the
hackathon demo is ready.

## Decision

Introduce LangGraph first as a bounded orchestration layer around the existing
deterministic build-generation path. The graph records named agent steps for
catalog, optimizer, compatibility, performance, explainer, and validator
responsibilities, then returns the same build artifact plus
`orchestration_trace` metadata.

## Alternatives Considered

1. Keep direct function calls until full optimizer work starts.
2. Replace the generator with a full LangGraph optimizer loop immediately.
3. Add Pydantic AI agents and provider calls inside generation now.

## Consequences

Positive:

- The demo now shows real multi-agent orchestration without weakening SKU,
  price, budget, compatibility, or approval guarantees.
- Existing tests and browser flows continue to validate deterministic behavior.
- Later stories can replace individual graph nodes with richer tools one at a
  time.

Tradeoffs:

- The first graph is mostly sequential and wraps existing deterministic logic.
- LangGraph checkpointing, PostgreSQL checkpointers, OR-Tools, Pydantic AI
  generation agents, and parallel Pareto variants remain future work.

## Follow-Up

- Add checkpointing only after the product needs recoverable multi-turn
  iteration state beyond local SQLite build artifacts.
- Split optimizer internals into separate node-level tools when budget
  allocation grows beyond the current greedy heuristic.

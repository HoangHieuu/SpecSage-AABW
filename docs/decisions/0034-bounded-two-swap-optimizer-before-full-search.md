# 0034 Bounded Two-Swap Optimizer Before Full Search

Date: 2026-06-28

## Status

Accepted

## Context

`US-029` proved that one deterministic, ranked, budget-safe optimizer swap can
improve creator, AI, and streaming builds without changing the API contract.
The next useful improvement is a small sequence of swaps, but a full optimizer
search would add more complexity than the current 14-SKU demo catalog needs.

## Decision

Allow generation to apply up to two eligible ranked alternatives. After each
swap, rebuild the artifact through the existing compatibility, budget,
performance, warning, explanation, and mock cart path before considering the
next swap.

Non-gaming use cases still require `recommended` alternatives. Gaming uses the
stricter benchmark-preserving guard from decision `0032`.

## Alternatives Considered

1. Keep the one-swap optimizer.
2. Implement a full combinatorial optimizer or OR-Tools model.
3. Let an LLM choose a sequence of SKU swaps.

## Consequences

Positive:

- Creator builds can now improve both RAM and storage when budget allows.
- AI/local LLM builds can apply both NVIDIA GPU and RAM upgrades.
- The search remains bounded, explainable, and fast.

Tradeoffs:

- Greedy two-pass search may miss a better global combination.
- More sophisticated Pareto search remains future work.

## Follow-Up

- Add benchmark-aware score deltas before expanding gaming search.
- Consider Pareto alternatives only after catalog variety and benchmark
  coverage are broader.

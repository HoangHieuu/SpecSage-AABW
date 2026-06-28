# 0037 Natural-Language Iteration Before Pareto Variants

Date: 2026-06-29

## Status

Accepted

## Context

`US-035` made the Phase 5 optimizer loop inspectable, and `US-036` proved the
Cyberpunk demo flow in the running app. The next Phase 5 capability in
`SPEC.md` is iterative refinement: customers should ask for changes such as
cheaper, quieter, more SSD, more RAM, or more GPU without starting over.

Full Pareto variants would add another broad comparison surface before the
current optimizer can respond to direct customer refinement. That would make
demo validation larger and duplicate some of the existing alternatives/apply
path.

## Decision

Add a deterministic natural-language iteration endpoint before full Pareto
variant generation. The endpoint parses a bounded Vietnamese command set,
selects a validated alternative from the existing ranking/gate path, creates a
new build version, and appends the accepted/rejected command decision to
`optimizer_trace`.

The command parser is code, not LLM-driven. It recognizes only supported
adjustment intents and rejects unsupported commands instead of guessing.

## Alternatives Considered

1. Jump directly to Best Value/Balanced/Best Performance Pareto variants.
2. Let the LLM choose arbitrary SKU swaps from a free-text instruction.
3. Keep only one-click alternatives and defer natural-language iteration.

## Consequences

Positive:

- Phase 5 becomes interactive while preserving SKU, budget, compatibility, and
  benchmark gates.
- New build versions can be produced from user phrasing without adding auth,
  checkout, or staff/admin scope.
- Future Pareto variants can reuse the same parse, selection, diff, and trace
  model.

Tradeoffs:

- The command set is intentionally narrow.
- Unsupported commands return a deterministic error until a story broadens the
  parser or catalog coverage.

## Follow-Up

- Add side-by-side Pareto variants after iteration commands are stable.
- Add monitor/peripheral iteration only after monitor SKU curation exists.
- Consider an LLM advisory layer for command paraphrase suggestions without
  letting it choose SKUs.

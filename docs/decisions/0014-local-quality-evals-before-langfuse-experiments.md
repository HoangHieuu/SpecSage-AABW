# 0014 Local Quality Evals Before Langfuse Experiments

Date: 2026-06-28

## Status

Accepted

## Context

`SPEC.md` Phase 11 calls for a quality evaluation suite with canonical intents,
automated compatibility and budget checks, hallucinated-SKU detection,
explanation scoring, and a CI release gate. `techstack.md` recommends Langfuse
Datasets and Experiments for production-grade evals, but the local tool registry
does not currently provide a present quality-evaluation or observability
provider.

The project already has deterministic parser, catalog, compatibility,
performance, LangGraph orchestration, and trace replay slices. A local
regression suite can provide immediate hackathon proof without new credentials.

## Decision

Add a checked-in local evaluation suite before Langfuse/GitHub Actions
integration:

- `evals/canonical_build_scenarios.json` with at least 30 canonical scenarios.
- `pc_build_copilot.evaluation` for typed loading, execution, checks, and
  explanation rubric scoring.
- `pnpm eval:run` as a local release gate alongside `pnpm check`.

The runner uses the current local catalog snapshot and deterministic
LangGraph-wrapped generator. It fails on critical regressions such as missing
required slots, budget mismatch, compatibility mismatch, hallucinated SKUs,
wrong use case, numeric FPS claims, or insufficient explanation rubric score.

## Alternatives Considered

1. Wait for Langfuse credentials and build datasets directly there.
2. Add only more pytest examples without a named eval command.
3. Run live LLM eval judges for explanation quality.

## Consequences

Positive:

- Future changes have a fast local quality gate tied to product scenarios.
- The suite is credential-free and works in the hackathon demo environment.
- Scenario failures are deterministic and easy to attribute.

Tradeoffs:

- Rubric scoring is a deterministic proxy, not a human review workflow.
- CI integration and Langfuse experiment tracking remain future work.
- The scenario set is anchored to the current curated catalog snapshot and must
  evolve when catalog coverage expands.

## Follow-Up

- Promote `pnpm eval:run` into CI once repository CI exists.
- Export these scenarios into Langfuse Datasets after credentials/tooling are
  available.
- Add benchmark-backed performance scenarios only after a maintained benchmark
  source exists.

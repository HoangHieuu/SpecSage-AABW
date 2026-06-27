# 0008 PC Build Copilot Source Hierarchy

Date: 2026-06-27

## Status

Accepted

## Context

The repository began as a generic Harness shell. The user supplied the first
real project sources: `SPEC.md`, `Data.md`, `techstack.md`, and `tools.md`.

Harness policy treats supplied specs as input material. Long-term product truth
should live in smaller product docs, stories, validation records, and decision
records.

## Decision

Keep the supplied files as source snapshots and derive the living project
contract into:

- `docs/product/*`
- `docs/stories/*`
- `docs/TEST_MATRIX.md`
- `docs/decisions/*`
- durable Harness rows in `harness.db`

Agents should read the source snapshots before product work, but they should
update the smaller living docs when behavior changes.

## Consequences

Positive:

- Future stories can read bounded contract files instead of the whole spec.
- The original product thinking remains available for audit.
- Harness records can track proof and decisions story by story.

Tradeoffs:

- Agents must keep source snapshots and living docs conceptually separate.
- If the source snapshots are edited later, affected living docs must be
  refreshed explicitly.

# US-000 Product Contract Wiring

## Status

implemented

## Lane

high-risk

## Product Contract

The generic Harness repository must recognize PC Build Copilot as the active
project and expose the supplied `SPEC.md`, `Data.md`, `techstack.md`, and
`tools.md` through smaller living harness artifacts.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/product/coding-agent-tooling.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- `README.md` names the project, source snapshots, living docs, first slices,
  and core Harness commands.
- `AGENTS.md` contains PC Build Copilot guardrails while preserving the Harness
  block.
- Product docs decompose the source snapshots into bounded contracts.
- Initial stories and matrix rows exist for the first vertical slices.
- Tooling docs and `.cursor/mcp.json` prepare the no-secret MCP defaults.
- Durable Harness intake, stories, decisions, and tool records are created.

## Design Notes

- Keep the full source snapshots intact as historical input material.
- Do not scaffold app code in this story.
- Treat cart, staff, admin, auth, and production provider integration as later
  high-risk stories.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Not applicable; docs-only wiring |
| Integration | `scripts/bin/harness-cli query matrix` and `query tools --summary` |
| E2E | Not applicable; no app UI exists |
| Platform | Not applicable |
| Release | `git diff --check` |

## Harness Delta

This story creates the first project-specific living harness state from the
generic repository shell.

## Evidence

`git diff --check` passed via `scripts/bin/harness-cli story verify US-000`.

Durable Harness rows were created for intake, stories, decisions, and registered
tools.

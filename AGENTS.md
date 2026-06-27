# Agent Instructions

## Project

This repository is the Harness-backed workspace for **PC Build Copilot for
Phong Vu** in Agentic AI Build Week.

Before product work, read:

- `SPEC.md`
- `Data.md`
- `techstack.md`
- `tools.md` when selecting coding-agent tools, MCPs, plugins, or validation
  helpers
- the relevant `docs/product/*` files
- the selected `docs/stories/*` packet when implementing a story

Treat `SPEC.md`, `Data.md`, `techstack.md`, and `tools.md` as source snapshots.
The living contract is `docs/product/*`, `docs/stories/*`,
`docs/TEST_MATRIX.md`, and `docs/decisions/*`.

Product guardrails:

- Vietnamese-first customer experience; keep technical SKU labels accurate.
- Recommend only real Phong Vu SKUs from the local catalog snapshot.
- Compatibility, PSU, RAM, clearance, stock, and budget gates are deterministic
  code/rule checks, not LLM guesses.
- LLMs may parse intent and explain trade-offs, but numeric claims must come
  from catalog, benchmark, rule, or build artifact fields.
- Build narrow vertical slices for the hackathon. Do not start with staff,
  admin, auth, checkout, or broad enterprise operations unless a story selects
  that scope.
- Before using an external tool, run
  `scripts/bin/harness-cli query tools --capability <name> --status present`.

<!-- HARNESS:BEGIN -->
## Harness

This repo uses Harness. Before work, read:

- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTEXT_RULES.md`
- `docs/TOOL_REGISTRY.md`
- `scripts/bin/harness-cli query matrix` on macOS/Linux, or `.\scripts\bin\harness-cli.exe query matrix` on Windows

Use the Rust Harness CLI at `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows as the main operational tool. Before a
step that could use an external tool, run `scripts/bin/harness-cli query tools
--capability <name> --status present` to see what is equipped; an absent
capability is a clean skip.
<!-- HARNESS:END -->

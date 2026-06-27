# SpecSage-AABW

Agentic AI Build Week workspace for **PC Build Copilot for Phong Vu**.

The repository started as a generic `repository-harness` install. It is now
wired with the first real product sources:

- `SPEC.md` - source product specification snapshot.
- `Data.md` - source data strategy snapshot.
- `techstack.md` - source technology stack snapshot.
- `tools.md` - source coding-agent tool and plugin plan.

The source snapshots are historical input material. The living project contract
is now split across `docs/product/`, `docs/stories/`, `docs/TEST_MATRIX.md`, and
`docs/decisions/`.

## Current State

`US-001` through `US-005` are implemented: the repo has a minimal FastAPI agent
API and Next.js customer web shell for session creation, Vietnamese intent
parsing, clarification, confirmation, deterministic local catalog snapshot
ingestion, read-only catalog API access, deterministic compatibility validation,
first build generation, and a mock cart-ready approval handoff.

Accepted product direction:

- Vietnamese-first PC build copilot for Phong Vu retail customers and staff.
- Real SKU grounding through a local catalog mirror built from public Phong Vu
  product data.
- Deterministic compatibility and safety checks in code, not in LLM prompts.
- Multi-agent orchestration for intent, catalog retrieval, compatibility,
  performance, optimization, explanation, commerce, and final validation.
- Hackathon path starts with a narrow, demoable slice rather than the full
  enterprise roadmap.

## Read First

Before product work, read:

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,220p' SPEC.md
sed -n '1,220p' Data.md
sed -n '1,220p' techstack.md
scripts/bin/harness-cli query matrix
```

For implementation stories, also read the relevant files under
`docs/product/` and the selected story packet under `docs/stories/`.

## Living Product Docs

- `docs/product/overview.md` - product vision, users, phase map, non-goals.
- `docs/product/data-strategy.md` - catalog mirror, enrichment, trust contract.
- `docs/product/technical-architecture.md` - stack, agents, state, boundaries.
- `docs/product/validation-strategy.md` - proof ladder and canonical scenarios.
- `docs/product/coding-agent-tooling.md` - MCP/plugin plan and live tool notes.

## First Build Slices

The initial implementation backlog is intentionally small:

1. `US-001` - session and Vietnamese intent foundation. Implemented.
2. `US-002` - local catalog snapshot ingestion. Implemented.
3. `US-003` - deterministic compatibility rule engine. Implemented.
4. `US-004` - build generation and explanation vertical slice. Implemented.
5. `US-005` - review approval and mock cart-ready handoff. Implemented.

Use Harness to keep each slice bounded:

```bash
scripts/bin/harness-cli query matrix
scripts/bin/harness-cli query tools --summary
scripts/bin/harness-cli story verify US-001
```

## Local Development

Install dependencies:

```bash
pnpm install
python3 -m venv .venv
.venv/bin/python -m pip install -e 'services/agent-api[dev]'
```

Run the API and web app in separate terminals:

```bash
pnpm dev:api
pnpm dev:web
```

Open:

- Web: `http://127.0.0.1:3000`
- API health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

Validate the current slice:

```bash
pnpm catalog:sync
pnpm check
scripts/bin/harness-cli story verify US-001
scripts/bin/harness-cli story verify US-002
scripts/bin/harness-cli story verify US-003
scripts/bin/harness-cli story verify US-004
scripts/bin/harness-cli story verify US-005
```

Catalog endpoints after `pnpm catalog:sync`:

- API catalog health: `http://127.0.0.1:8000/catalog/health`
- API SKU query: `http://127.0.0.1:8000/catalog/skus?category=vga&in_stock=true`
- API build validation: `POST http://127.0.0.1:8000/builds/demo/validate`
- API build generation: `POST http://127.0.0.1:8000/sessions/{build_session_id}/generate`
- API mock cart handoff: `POST http://127.0.0.1:8000/builds/{build_id}/approve`

## Tool Setup

Cursor MCP defaults live in `.cursor/mcp.json`:

- Context7 for current framework documentation.
- Playwright for UI and demo-flow verification.
- shadcn MCP for UI component work.

Optional keyed tools such as Firecrawl, Langfuse, GitHub, PostgreSQL MCP, AWS,
and Vercel should be added only when the required credentials or target project
exist.

## Harness Commands

```bash
scripts/bin/harness-cli init
scripts/bin/harness-cli intake --type "Spec slice" --summary "..." --lane normal
scripts/bin/harness-cli story add --id US-001 --title "..." --lane normal
scripts/bin/harness-cli tool check
scripts/bin/harness-cli query matrix
scripts/bin/harness-cli trace --summary "..." --outcome completed
```

See `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, and
`docs/TOOL_REGISTRY.md` for the full operating model.

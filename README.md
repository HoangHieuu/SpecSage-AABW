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

`US-001` through `US-045` are implemented: the repo has a minimal FastAPI agent
API and Next.js customer web shell for session creation, Vietnamese intent
parsing, clarification, confirmation, deterministic local catalog snapshot
ingestion, read-only catalog API access, deterministic compatibility validation,
first build generation, a mock cart-ready approval handoff, and an advisory
OpenRouter LLM intent analysis layer. Generated builds now also include a
deterministic workload fit profile grounded in catalog facts, with FPS evidence
only from exact-match source-backed benchmark matrix rows, plus deterministic
catalog-grounded alternatives with slot deltas and compatibility proof. A
selected alternative can be applied as a new active build version, then approved
through the existing handoff gate.
Sessions, intent revisions, build artifacts, applied build versions, and mock
cart handoffs persist in a local SQLite store for restart-safe demos.
Build generation now runs through a bounded LangGraph orchestration layer with
catalog, optimizer, compatibility, performance, explainer, and validator steps
recorded on each build artifact. Agent trace replay is now exposed through
build/session trace endpoints and a web `Chi tiết hỗ trợ` disclosure with
redacted event payloads and support-export text. A local quality eval suite now runs 30
canonical scenarios as a release gate for catalog-grounding, budget,
compatibility, required slots, SKU hallucination, and explanation-rubric
regressions.
Catalog health now also reports demo-readiness category coverage for the local
snapshot before build generation or evals run, plus non-blocking variety
warnings when required demo categories have too little fallback choice.
Catalog sync now reads an auditable source manifest so the local mirror can grow
across multiple saved Phong Vu public payloads while preserving deterministic
validation. A local capture command now validates public category payloads
before writing fixtures and upserting manifest entries. Captured public
category pages can now be staged and counted without becoming
recommendation-eligible until compatibility overrides are verified. Committed
catalog fixtures now store sanitized `__NEXT_DATA__` payloads instead of full
page HTML so page-shell environment keys are not checked in.
Curated manifest entries can now promote reviewed SKUs from staged captures
with `include_skus`, so the active catalog has three choices in every required
full-build category while full category pages remain staged. Catalog health now
also separates `demo_ready`, `pilot_ready`, and `production_ready`, reports
snapshot freshness against a 7-day window, counts verified/partial/inferred
spec confidence, and keeps production target gaps visible without pretending
the local mirror is a full Phong Vu catalog. The active catalog now also
includes curated cooler and monitor rows, giving optional CPU cooling and
display categories three validated choices each while preserving the existing
full-build required-slot behavior.
Gaming benchmark evidence now comes from
`services/agent-api/benchmarks/gaming_benchmark_matrix.json`; unsupported FPS
claims remain blocked by the local eval gate. Monitor-targeted gaming requests
now warn with `PERF_MONITOR_OVERSPEC` when matched benchmark FPS is below the
requested display refresh target. Curated monitor SKUs exist in the catalog,
and generated builds can now attach optional monitor recommendations when the
need mentions a monitor or includes a resolution plus refresh target. Generated
builds also include optional cooler recommendations for quiet/cooler requests,
after deterministic socket, TDP, and case-clearance checks. These add-ons stay
outside the PC total and approval gate. Customers can now explicitly include
selected add-ons in the mock shopping list, which reports PC total, add-on
total, and combined shopping-list total separately. Upgrade buyers can also
enter an existing PC description, confirm the parsed current-PC summary, and
receive a first GPU upgrade plan grounded in the active catalog, with
deterministic PSU and case checks. Generated builds also include a deterministic
CPU/GPU/RAM/storage balance score and `PERF_IMBALANCE` warning for severe
mismatch. Creator, streaming, and local LLM requests now show deterministic
app-fit rows for RAM, VRAM, CPU threads, storage, and CUDA preference. Office
and student requests now explain iGPU/discrete GPU suitability, quiet/power
guidance, and multi-monitor validation gaps without inventing output-port
support.
Alternatives now include deterministic ranking metadata so the most
workload-relevant variant appears first. Creator, AI, streaming, and guarded
gaming builds now run a bounded budget-aware improvement pass before the build
is returned.
Benchmark coverage now includes RTX 4060 Cyberpunk 2077 1440p Ultra evidence so
gaming GPU swaps can preserve below-target warning provenance, plus RX 7600
Cyberpunk 2077 1080p Ultra evidence for exact 1080p requests. The optimizer can
apply up to two eligible swaps, and gaming GPU swaps require exact benchmark
evidence before auto-apply. Gaming alternatives now rank GPU swaps by exact
source-backed benchmark delta when both the base and candidate have comparable
benchmark evidence. Generated builds now expose a config-driven optimizer loop
trace with use-case budget allocation, priority overrides, and accepted or
rejected candidate decisions. The web demo starts on a Cyberpunk 2077 1440p
Ultra 144Hz prompt and renders the optimizer loop, benchmark-backed warning,
alternatives, mock cart handoff, and feedback path. Generated builds can also
accept bounded Vietnamese iteration commands such as "Tăng SSD nhưng giữ dưới
20 triệu" or "Giảm xuống dưới 18 triệu", producing a new validated build
version through the existing alternatives, budget, compatibility, performance,
and trace gates. The customer web flow now keeps the default path focused on
buyer decisions with a compact price/fit/budget/next-action summary, while
technical optimizer and trace proof stays behind the advanced details path.

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
6. `US-006` - OpenRouter LLM intent advisor. Implemented.
7. `US-007` - deterministic performance fit profile. Implemented.
8. `US-008` - build alternatives and iteration controls. Implemented.
9. `US-009` - apply alternative as active build. Implemented.
10. `US-010` - persistent session and build store. Implemented.
11. `US-011` - LangGraph build orchestration foundation. Implemented.
12. `US-012` - agent trace session replay foundation. Implemented.
13. `US-013` - quality evaluation suite foundation. Implemented.
14. `US-014` - CI quality gate foundation. Implemented.
15. `US-015` - user feedback loop foundation. Implemented.
16. `US-016` - catalog demo readiness health. Implemented.
17. `US-017` - catalog demo variety health. Implemented.
18. `US-018` - multi-source catalog ingestion foundation. Implemented.
19. `US-019` - public catalog payload capture CLI. Implemented.
20. `US-020` - staged catalog source coverage report. Implemented.
21. `US-021` - sanitized catalog fixtures. Implemented.
22. `US-022` - curated catalog subset promotion. Implemented.
23. `US-023` - benchmark-backed gaming performance foundation. Implemented.
24. `US-024` - monitor overspec warning foundation. Implemented.
25. `US-025` - balance score foundation. Implemented.
26. `US-026` - creator and productivity workload fit. Implemented.
27. `US-027` - office and general-use adequacy. Implemented.
28. `US-028` - performance-aware alternative ranking. Implemented.
29. `US-029` - budget-aware optimizer improvement pass. Implemented.
30. `US-030` - benchmark coverage for optimizer-safe gaming swaps. Implemented.
31. `US-031` - benchmark-preserving gaming GPU optimizer guard. Implemented.
32. `US-032` - broader gaming benchmark coverage. Implemented.
33. `US-033` - bounded multi-swap optimizer search. Implemented.
34. `US-034` - benchmark-delta gaming alternative ranking. Implemented.
35. `US-035` - Phase 5 multi-agent optimizer loop foundation. Implemented.
36. `US-036` - polished end-to-end demo proof. Implemented.
37. `US-037` - natural-language build iteration commands. Implemented.
38. `US-038` - customer-facing demo polish. Implemented.
39. `US-039` - production catalog breadth and freshness foundation. Implemented.
40. `US-040` - optional cooler and monitor catalog curation. Implemented.
41. `US-041` - monitor add-on recommendation foundation. Implemented.
42. `US-042` - cooler add-on recommendation foundation. Implemented.
43. `US-043` - optional add-on shopping-list selection. Implemented.
44. `US-044` - GPU upgrade planning foundation. Implemented.
45. `US-045` - existing system confirmation before upgrade planning. Implemented.

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

Optional LLM advisor configuration for the API:

```bash
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
LLM_AGENT_ENABLED=true
PC_BUILD_COPILOT_DB_PATH=.local/pc-build-copilot.sqlite3
```

The API reads these from local environment or `.env`. The key stays server-side;
the browser receives only the model name, provider status, and advisory text.
`PC_BUILD_COPILOT_DB_PATH` is optional; when omitted, the API uses
`.local/pc-build-copilot.sqlite3`.

Validate the current slice:

```bash
pnpm catalog:sync
pnpm catalog:capture -- --input services/agent-api/fixtures/phongvu-category-components.html --output /tmp/pc-build-copilot-capture-smoke.html --manifest /tmp/pc-build-copilot-catalog-sources.json --source test_capture_smoke --category-hint vga --source-url https://phongvu.vn/c/vga-card-man-hinh
pnpm catalog:source-report
pnpm check
scripts/bin/harness-cli story verify US-001
scripts/bin/harness-cli story verify US-002
scripts/bin/harness-cli story verify US-003
scripts/bin/harness-cli story verify US-004
scripts/bin/harness-cli story verify US-005
scripts/bin/harness-cli story verify US-006
scripts/bin/harness-cli story verify US-007
scripts/bin/harness-cli story verify US-008
scripts/bin/harness-cli story verify US-009
scripts/bin/harness-cli story verify US-010
scripts/bin/harness-cli story verify US-011
scripts/bin/harness-cli story verify US-012
scripts/bin/harness-cli story verify US-013
scripts/bin/harness-cli story verify US-014
scripts/bin/harness-cli story verify US-015
scripts/bin/harness-cli story verify US-016
scripts/bin/harness-cli story verify US-017
scripts/bin/harness-cli story verify US-018
scripts/bin/harness-cli story verify US-019
scripts/bin/harness-cli story verify US-020
scripts/bin/harness-cli story verify US-021
scripts/bin/harness-cli story verify US-022
scripts/bin/harness-cli story verify US-023
scripts/bin/harness-cli story verify US-024
scripts/bin/harness-cli story verify US-025
scripts/bin/harness-cli story verify US-026
scripts/bin/harness-cli story verify US-027
scripts/bin/harness-cli story verify US-028
scripts/bin/harness-cli story verify US-029
scripts/bin/harness-cli story verify US-030
scripts/bin/harness-cli story verify US-031
scripts/bin/harness-cli story verify US-032
scripts/bin/harness-cli story verify US-033
scripts/bin/harness-cli story verify US-034
scripts/bin/harness-cli story verify US-035
scripts/bin/harness-cli story verify US-036
scripts/bin/harness-cli story verify US-037
scripts/bin/harness-cli story verify US-038
scripts/bin/harness-cli story verify US-039
scripts/bin/harness-cli story verify US-040
scripts/bin/harness-cli story verify US-041
scripts/bin/harness-cli story verify US-042
scripts/bin/harness-cli story verify US-043
scripts/bin/harness-cli story verify US-044
scripts/bin/harness-cli story verify US-045
pnpm eval:run
```

To add future catalog sources from public Phong Vu category pages, capture the
page first. The capture command writes a sanitized `__NEXT_DATA__` fixture, not
the full HTML page, so public page environment keys are not committed. Review
the fixture and manifest diff, then run `pnpm catalog:sync`:

```bash
pnpm catalog:capture -- --url https://phongvu.vn/c/vga-card-man-hinh --output services/agent-api/fixtures/phongvu-vga-card-man-hinh.html --manifest services/agent-api/catalog/catalog_sources.json --category-hint vga --source phongvu_public_category_vga
pnpm catalog:sync
```

Use `--staged` for broad captures that should be counted but skipped by
`catalog:sync` until overrides are verified:

```bash
pnpm catalog:capture -- --url https://phongvu.vn/c/cpu --output services/agent-api/fixtures/phongvu-category-cpu-2026-06-28.html --manifest services/agent-api/catalog/catalog_sources.json --category-hint cpu --source phongvu_public_category_cpu_2026_06_28 --staged
pnpm catalog:source-report
```

Catalog endpoints after `pnpm catalog:sync`:

- API catalog health: `http://127.0.0.1:8000/catalog/health`
- API SKU query: `http://127.0.0.1:8000/catalog/skus?category=vga&in_stock=true`
- API build validation: `POST http://127.0.0.1:8000/builds/demo/validate`
- API build generation: `POST http://127.0.0.1:8000/sessions/{build_session_id}/generate`
- API build alternatives: `GET http://127.0.0.1:8000/builds/{build_id}/alternatives`
- API apply alternative: `POST http://127.0.0.1:8000/builds/{build_id}/alternatives/{variant_id}/apply`
- API build trace replay: `GET http://127.0.0.1:8000/builds/{build_id}/trace`
- API session trace replay: `GET http://127.0.0.1:8000/sessions/{build_session_id}/trace`
- API build feedback: `POST http://127.0.0.1:8000/builds/{build_id}/feedback`
- API build feedback history: `GET http://127.0.0.1:8000/builds/{build_id}/feedback`
- API feedback review queue: `GET http://127.0.0.1:8000/feedback/review-queue`
- API mock cart handoff: `POST http://127.0.0.1:8000/builds/{build_id}/approve`
- API existing-system parse: `POST http://127.0.0.1:8000/upgrade-plans/existing-system/parse`
- API GPU upgrade plan: `POST http://127.0.0.1:8000/upgrade-plans/gpu`
- Local quality evals: `pnpm eval:run`
- CI quality gate: `.github/workflows/ci.yml` runs `pnpm check` and
  `pnpm eval:run`

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

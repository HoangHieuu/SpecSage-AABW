# Technical Architecture

## Stack

| Layer | Default choice |
| --- | --- |
| Monorepo | Turborepo + pnpm |
| Customer UI | Next.js 15 App Router + React 19 |
| UI system | Tailwind CSS 4 + shadcn/ui |
| Agent API | Python 3.12 + FastAPI |
| Agent orchestration | LangGraph state graph |
| Typed agent IO | Pydantic AI and Pydantic v2 models |
| LLM routing | LiteLLM with Kimi/Qwen/Claude/OpenAI fallbacks |
| Primary database | PostgreSQL 16 |
| Vector search | pgvector |
| Facet search | Typesense |
| Cache/session TTL | Redis 7 |
| Jobs | ARQ or BullMQ, chosen per service boundary |
| Observability | Langfuse, OpenTelemetry, Sentry |
| Deployment | AWS for backend services, Vercel optional for web |

## Repository Shape

Create these folders only when the selected story needs implementation:

```text
apps/
  web/
services/
  agent-api/
  catalog-sync/
  commerce-adapter/
packages/
  shared-types/
  ui/
infra/
evals/
```

Do not scaffold all future services just to match the full spec. The first
vertical slice should introduce only the paths it exercises.

## Agent Responsibilities

| Agent | Responsibility | Hard boundary |
| --- | --- | --- |
| Intent Agent | Parse Vietnamese input into `BuildIntent` | Must output schema-valid intent |
| Catalog Agent | Retrieve candidate SKUs | May only return catalog snapshot SKUs |
| Compatibility Agent | Run deterministic rules | No LLM compatibility guesses |
| Performance Agent | Estimate workload fit | Numeric claims require benchmark source |
| Optimizer Agent | Assemble/refine builds | Bounded iterations, budget-aware |
| Explainer Agent | Vietnamese rationale and trade-offs | Receives validated facts only |
| Commerce Agent | Promo, stock, cart payload | Mock until real Teko API exists |
| Validator Agent | Final approval gate | Only agent allowed to approve a build |

## Session State

```text
created -> intent_draft -> intent_confirmed -> generating -> generated
  -> reviewing -> approved -> cart_ready -> completed
                    -> rejected
```

The optimizer may not run until intent is confirmed. The explainer may not run
while block-level compatibility issues remain. Any catalog or rules version
change triggers revalidation before save, share, cart, or quote actions.

## Data And Boundary Rules

Unknown data is parsed at the boundary:

- HTTP request body, params, query strings.
- Environment variables.
- Catalog scrape payloads.
- LLM structured output.
- Provider payloads and future webhooks.
- Local catalog rows before entering rule logic.

Inner application and domain code should operate on typed objects such as
`BuildSessionId`, `BuildIntent`, `Sku`, `BuildConfiguration`,
`CompatibilityReport`, and `CatalogVersion`, not raw dictionaries or prompt
strings.

## Compatibility Rule Principle

Safety rules are pure, versioned code or rule-pack evaluations. Required first
rule families:

- CPU/mainboard socket match.
- Chipset and BIOS generation support.
- RAM type/capacity/module count.
- GPU case clearance.
- PSU wattage and power connectors.
- Cooler socket/height/TDP.
- Storage M.2/SATA port limits.

LLMs can explain a failed rule after the report exists. They cannot decide if a
build passes.

Current implementation:

- Rule manifest:
  `services/agent-api/rules/compatibility_rules_v2026_06_27.json`
- Runtime rules:
  `services/agent-api/src/pc_build_copilot/compatibility_rules.py`
- Report schema:
  `services/agent-api/src/pc_build_copilot/compatibility_models.py`
- API:
  `POST /builds/{build_id}/validate`

The first rule set covers CPU/mainboard socket, RAM type, PSU wattage, GPU power
connectors, GPU/case clearance, and cooler/case clearance. Future rule changes
must update the manifest and tests together.

## API Boundary

First public endpoints should be introduced with OpenAPI contracts:

- `POST /sessions`
- `POST /sessions/{id}/intent`
- `GET /catalog/health`
- `GET /catalog/skus`
- `POST /sessions/{id}/generate`
- `POST /builds/{id}/approve`
- `POST /builds/{id}/validate`
- `GET /builds/{id}/alternatives`
- `POST /builds/{id}/cart-payload`

Do not expose checkout, staff auth, webhooks, or admin mutation APIs until their
stories create the required authorization and validation packets.

## Current Build Generation Slice

`US-004` adds a deterministic generation path without introducing LangGraph,
LLM calls, PostgreSQL, or checkout:

- `POST /sessions/{build_session_id}/generate`
- `GET /builds/{build_id}`
- `services/agent-api/src/pc_build_copilot/build_generator.py`
- `services/agent-api/src/pc_build_copilot/build_models.py`

The first generator chooses in-stock local catalog SKUs for required slots,
runs the compatibility report, computes total price and budget gap, and returns
grounded Vietnamese explanations. It does not invent FPS, prices, specs, or
parts outside the snapshot.

## Current Commerce Handoff Slice

`US-005` adds mock approval and cart-ready handoff without introducing checkout,
auth, payment, Teko provider APIs, or persistent storage:

- `POST /builds/{build_id}/approve`
- `services/agent-api/src/pc_build_copilot/build_store.py`
- `apps/web/components/build-copilot-client.tsx`

Approval is allowed only when the generated build has `can_approve=true` and
status `generated`. The handoff contains real SKU links from the existing build
artifact and remains labeled as a mock cart payload.

## Current LLM Advisor Slice

`US-006` adds a narrow OpenRouter adapter for intent-time explanation:

- `OPENROUTER_API_KEY` stays server-side in local environment or `.env`.
- `OPENROUTER_MODEL` defaults to `deepseek/deepseek-v4-flash`.
- `IntentRequest.use_llm=true` opts into one non-streaming chat completion for
  draft intent analysis.
- `IntentResponse.agent_analysis` returns provider status, model name,
  Vietnamese summary, optional clarification wording, confidence notes, and
  safety notes.

This is not the full LangGraph/Pydantic AI orchestration layer yet. It is a
boundary-safe provider adapter that parses structured LLM JSON before it reaches
the UI. Provider failures degrade to deterministic parser output instead of
blocking the session.

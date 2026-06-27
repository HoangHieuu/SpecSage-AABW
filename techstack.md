# PC Build Copilot — Technology Stack Guide

**Companion to:** [PC-Build-Copilot-SPEC.md](./PC-Build-Copilot-SPEC.md)  
**Version:** 1.0  
**Last updated:** 2026-06-26

This document recommends a **modern, production-oriented technology stack** for each product phase defined in the specification. Choices prioritize:

- Compatibility with **Phong Vũ / Teko** retail patterns
- Fit for **multi-agent, tool-using** systems (not chatbot wrappers)
- **AABW 2026 partner ecosystem** (AWS, Langfuse, ClickHouse, Kimi, Tencent Cloud, NVIDIA, etc.)
- **Vietnamese-first** UX and strong structured-output reliability
- Clear separation: **LLM for language**, **code for safety**

---

## 1. Stack at a Glance

| Layer | Primary Choice | Why |
|-------|----------------|-----|
| **Monorepo** | Turborepo + pnpm | Fast builds, shared types, matches modern JS workspaces |
| **Customer UI** | Next.js 15 (App Router) + React 19 | SSR, SEO, streaming, embeddable widget |
| **Staff / Admin UI** | Next.js route groups + Refine | Same codebase, RBAC-separated surfaces |
| **Agent API** | Python 3.12 + FastAPI | Best AI ecosystem, typed agents, fast iteration |
| **Orchestration** | LangGraph + Pydantic AI | Stateful multi-agent loops + type-safe tool I/O |
| **LLM Gateway** | LiteLLM → Kimi / Qwen / Claude | One interface, provider failover, AABW perk-friendly |
| **Primary Database** | PostgreSQL 16 | Sessions, builds, rules, benchmarks, audit |
| **Vector Search** | pgvector (in Postgres) | Semantic SKU retrieval without extra infra early |
| **Facet Search** | Typesense | E-commerce filters (price, socket, brand, stock) |
| **Cache / Sessions** | Redis 7 | Hot catalog, rate limits, session TTL |
| **Job Queue** | ARQ (Python) or BullMQ (Node) | Catalog sync, reindex, nightly evals |
| **Observability** | Langfuse + OpenTelemetry + Sentry | Agent traces (AABW workshop partner) |
| **Analytics Warehouse** | ClickHouse | Funnel & business metrics (AABW partner) |
| **Auth** | Better Auth | Modern session/OAuth/RBAC for web + staff |
| **Deploy (prod)** | AWS (ECS + RDS + ElastiCache) + Vercel | Built with AWS track synergy + fast frontend |
| **Local dev** | Docker Compose | One-command full stack |

---

## 2. Architecture Decision Record (ADR Summary)

### ADR-001: Hybrid Python + TypeScript (not single-language)

**Decision:** Python for agents/rules/ML-adjacent logic; TypeScript for all user-facing apps.

**Rationale:** 2026 market consensus ([Langfuse agent framework comparison](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)) shows Python leads for agent orchestration (LangGraph, Pydantic AI, tool ecosystems). Teko/Phong Vũ consumer surfaces are React/Next.js ([Teko engineering blog](https://engineering.teko.vn/front-end-engineer-myths-and-facts/)). Splitting by strength avoids forcing agents into Node or UI into Python.

**Contract:** OpenAPI 3.1 generated types (`openapi-typescript`) consumed by Next.js.

---

### ADR-002: LangGraph for orchestration, Pydantic AI for agents

**Decision:** LangGraph owns session state machine and iteration loops; each agent is a Pydantic AI agent with typed tools.

**Rationale:**

- **LangGraph** — graph-based control flow, branching, retries, human-in-the-loop; industry default for complex multi-step agents in 2026 ([Towards AI enterprise comparison](https://pub.towardsai.net/langgraph-vs-crewai-vs-autogen-which-ai-agent-framework-should-your-enterprise-use-in-2026-3a9ebb407b09)).
- **Pydantic AI** — FastAPI-style DX, validated `BuildIntent` / `BuildConfiguration` outputs, native OpenTelemetry ([Pydantic AI docs](https://ai.pydantic.dev/)).
- **Not CrewAI** — better for role theatre; your flow is deterministic pipeline + optimizer loop, not open-ended crew debate.
- **Not AutoGen** — conversation-first; overkill for commerce workflows with hard validation gates.

---

### ADR-003: Compatibility rules are code, never LLM

**Decision:** Pure Python rules engine with Pydantic models and versioned rule packs.

**Rationale:** PSU/socket/RAM errors are safety-critical. LLMs hallucinate specs. Market best practice for agentic commerce: **LLM plans, code validates**.

---

### ADR-004: Hybrid search (Typesense + pgvector)

**Decision:** Typesense for structured catalog filters; pgvector for semantic fallback ("card tầm trung cho 1080p").

**Rationale:** Vector-only search misses exact commerce filters (price range, socket, stock). Facet engines (Typesense, Meilisearch) are standard in modern e-commerce search. pgvector keeps ops simple vs running Qdrant/Pinecone early.

**Alternative at scale:** Typesense + built-in vector (Typesense 26.x vector features) to collapse to one search engine.

---

### ADR-005: LiteLLM as model router

**Decision:** Route all LLM calls through LiteLLM with fallbacks.

**Rationale:** AABW perks span Kimi, Qwen, OpenAI, Azure, AWS Bedrock. LiteLLM provides one API, cost tracking, and failover — critical for demo day reliability.

**Recommended model order (Vietnamese retail advisory):**

| Priority | Model | Provider | Notes |
|----------|-------|----------|-------|
| 1 | Kimi K2 / K2.5 | Moonshot ([platform.kimi.ai](https://platform.kimi.ai/)) | AABW partner; strong multilingual |
| 2 | Qwen3 / Qwen2.5 | Alibaba / Tencent Cloud | AABW partner; excellent VN Chinese-Vietnamese tech text |
| 3 | Claude Sonnet | Anthropic via Bedrock or API | Best reasoning for trade-off narratives |
| 4 | GPT-4.1 / o4-mini | OpenAI | Fallback, structured tool calling |

Use **small/fast models** for intent parsing; **larger models** only for explainer and complex upgrade planning.

---

### ADR-006: AWS-primary deployment

**Decision:** Production on AWS; optional Vercel for Next.js edge.

**Rationale:** Aligns with **Built with AWS** track and AABW Day 2 Integrate workshops. [Strands Agents SDK](https://strandsagents.com) offers Bedrock-native agents with OpenTelemetry if you later migrate orchestration.

---

## 3. Repository Structure (Turborepo)

```
pc-build-copilot/
├── apps/
│   ├── web/                 # Next.js 15 — customer copilot + embed widget
│   ├── staff/               # Next.js — showroom console (or web route group)
│   └── admin/               # Refine admin (or web/admin route group)
├── services/
│   ├── agent-api/           # FastAPI + LangGraph + Pydantic AI
│   ├── catalog-sync/        # Scrape/index jobs
│   └── commerce-adapter/    # Teko cart/promo integration (mock → real)
├── packages/
│   ├── shared-types/        # OpenAPI-generated TS types + JSON schemas
│   ├── rules-engine/        # Compatibility rules (Python package)
│   ├── ui/                  # shadcn components, Phong Vũ theme tokens
│   └── config/              # ESLint, TS, Python tooling
├── infra/
│   ├── docker/              # Compose, Dockerfiles
│   └── terraform/           # AWS modules (optional)
└── evals/                   # Langfuse datasets + regression scenarios
```

---

## 4. Phase-by-Phase Technology Map

Each section maps to **PC-Build-Copilot-SPEC.md** phases.

---

## Phase 1 — Session Foundation & Intent Capture

**Goal:** Start sessions, parse Vietnamese intent, clarify, confirm.

| Concern | Technology | Role |
|---------|------------|------|
| Web app shell | **Next.js 15** + **React 19** | App Router, RSC for fast first paint |
| UI components | **shadcn/ui** + **Tailwind CSS 4** | Accessible chat + build summary panels |
| i18n / VND formatting | **next-intl** + **Intl.NumberFormat('vi-VN')** | Vietnamese UI, "25 triệu" parsing helpers |
| Client state | **Zustand** | Lightweight session UI state |
| Server state | **TanStack Query v5** | API caching, optimistic slot swaps |
| Streaming UX | **SSE** via FastAPI `EventSourceResponse` | Token streaming for explainer agent |
| Session persistence | **PostgreSQL** (`build_sessions`, `intent_revisions`) | Durable sessions |
| Session cache | **Redis** | TTL, rate limiting, idempotency keys |
| Intent Agent | **Pydantic AI** | `BuildIntent` structured output with validation |
| NL budget parsing | Custom parser + LLM fallback | Regex for `triệu`, `tr`, `k` before LLM |
| Presets | JSON config in `packages/shared-types` | Gaming, Creator, Office, AI presets |
| API | **FastAPI** + **Pydantic v2** | REST endpoints, auto OpenAPI |
| Real-time (staff) | **PartyKit** or **Socket.io** (optional) | Co-browse staff/customer (Phase 9) |

**Avoid:** Raw `localStorage` as sole session store; unstructured prompt strings without schema.

**AABW alignment:** Use **TRAE** / **Cursor** for DX; intent schema as `.md` brief for AI coding tools.

---

## Phase 2 — Catalog Intelligence & Product Grounding

**Goal:** Real SKUs, specs, prices, promos, stock signals.

| Concern | Technology | Role |
|---------|------------|------|
| Primary datastore | **PostgreSQL** (`skus`, `sku_specs`, `catalog_versions`) | Versioned catalog snapshots |
| Faceted product search | **Typesense** | Filter by socket, price, brand, category, stock |
| Semantic retrieval | **pgvector** + **OpenAI text-embedding-3-small** or **BGE-M3** (open) | "GPU tầm trung 1080p" queries |
| Embedding jobs | **ARQ** + Python | Nightly re-embed on catalog change |
| Catalog ingestion | **Playwright** or **httpx** + parser | Scrape phongvu.vn categories (hackathon) |
| Normalized specs | **Pydantic models** per category | CPU, GPU, board… per SPEC §8 |
| Future Teko integration | **commerce-adapter** service | Swap scraper for Teko Product API |
| Object storage | **AWS S3** | Raw HTML snapshots, CSV imports, images |
| Admin review | **Refine** + **Ant Design** | Flag incomplete specs (Phase 10) |
| Search SDK | `typesense-python` / HTTP API | Catalog Agent tool |

**Recommended search flow (Catalog Agent tool):**

```
1. Typesense facet query (hard filters: category, price, socket, in_stock)
2. If < N results → pgvector semantic widen
3. Rank by: in_stock > promo > margin tier (configurable) > price fit
```

**Avoid:** Embedding-only search without commerce filters; storing catalog only in vector DB.

**Teko compatibility:** Mirror Teko tracker patterns — use event hooks compatible with [tracker-js](https://guide.stag.teko.vn/tracking/js/) for later integration.

---

## Phase 3 — Compatibility & Safety Engine

**Goal:** Deterministic validation — socket, PSU, RAM, clearance, ports.

| Concern | Technology | Role |
|---------|------------|------|
| Rules engine | **Python package** `rules-engine` | Pure functions, no LLM |
| Schema validation | **Pydantic v2** | `CompatibilityReport`, `CheckResult` |
| Rule definitions | **YAML or JSON** versioned packs | `rules/v2026.07.json` |
| Rule evaluation | Custom evaluator + **simpleeval** (safe math) | PSU wattage formulas |
| Unit tests | **pytest** + **hypothesis** | Property-based compatibility tests |
| Shared contracts | **JSON Schema** exported to TypeScript | Frontend displays same error codes |
| Performance | In-memory rule index | Sub-50ms per full build check |

**Rule pack structure:**

```yaml
version: "2026.07.1"
rules:
  - id: COMPAT_SOCKET_MISMATCH
    type: hard_block
    expr: cpu.socket == mainboard.socket
```

**Avoid:** Asking LLM "is this compatible?"; brittle `if` chains without versioned rule packs.

**Market note:** Production agent systems in 2026 consistently separate **neural planning** from **symbolic validation** (LangGraph + code tools pattern).

---

## Phase 4 — Performance Modeling & Workload Fit

**Goal:** FPS estimates, bottleneck analysis, workload profiles.

| Concern | Technology | Role |
|---------|------------|------|
| Benchmark tables | **PostgreSQL** (`benchmark_matrix`) | Game/app × GPU tier × resolution → FPS range |
| Lookup engine | **Python** + **Polars** (optional) | Fast matrix joins for Performance Agent |
| Balance scoring | Deterministic formula in Python | CPU/GPU balance score 0–100 |
| AI/LLM PC profiles | Config-driven thresholds | VRAM tiers for 7B/13B/70B qualitative labels |
| Caching | **Redis** | Memoize `(gpu_tier, game, res)` lookups |
| Admin CSV import | **pandas** + validation | Merchandising updates benchmarks (Phase 10) |
| Optional enrichment | **NVIDIA NIM** APIs | AABW NVIDIA partner — future real benchmark feeds |

**Avoid:** LLM-invented FPS numbers; unversioned benchmark data.

**Data source strategy:** Seed from public benchmarks (Hardware Unboxed, TechPowerUp class data) + Phong Vũ blog configs as calibration anchors.

---

## Phase 5 — Build Optimization & Iteration

**Goal:** Generate builds, iterate, alternatives, Pareto variants.

| Concern | Technology | Role |
|---------|------------|------|
| Orchestration | **LangGraph** `StateGraph` | `generate → validate → optimize → explain` loop |
| Optimizer Agent | Python + **OR-Tools** (CP-SAT) or greedy heuristic | Budget allocation + slot filling |
| Iteration state | LangGraph checkpointing | **PostgreSQL** or **Redis** checkpointer |
| Diff engine | Python structural diff on `BuildConfiguration` | `build_v1` → `build_v2` highlights |
| Alternatives | Catalog Agent re-query per slot | Top 3 in-stock substitutes |
| Pareto variants | Parallel LangGraph branches | Best Value / Balanced / Max Performance |
| API pattern | `POST /sessions/{id}/iterate` | Idempotent iteration commands |

**LangGraph state shape (minimal):**

```python
class BuildState(TypedDict):
    intent: BuildIntent
    build: BuildConfiguration | None
    compatibility: CompatibilityReport | None
    performance: PerformanceProfile | None
    iteration: int
    status: Literal["generating", "approved", "rejected"]
```

**Avoid:** Single-shot LLM "here's a parts list"; unconstrained optimizer loops without max iterations.

---

## Phase 6 — Explanation & Customer Education

**Goal:** Vietnamese rationales, trade-offs, glossary, anti-hallucination.

| Concern | Technology | Role |
|---------|------------|------|
| Explainer Agent | **Pydantic AI** + **Jinja2** templates | Grounded numeric fields injected before LLM |
| Narrative LLM | **Kimi K2** or **Qwen** via LiteLLM | Natural Vietnamese explanations |
| Glossary | PostgreSQL `glossary_terms` + Redis cache | Tooltip content |
| Template variables | `{gpu_name}`, `{fps_estimate}`, `{price_delta}` | Prevent fabricated numbers |
| Output validation | **Pydantic** post-check | Ensure cited SKUs exist in build |
| Share cards | **@vercel/og** (Satori) | OG image share summaries |
| Markdown export | **react-markdown** renderer | Shareable build summary page |

**Guardrail pattern:**

```
1. Build facts object from validated agents (no LLM)
2. Template fills all numbers and SKU names
3. LLM only polishes prose around frozen facts
4. Validator rejects output if SKU/price not in facts object
```

**Avoid:** Free-form LLM explanations; ChatGPT-style generic component descriptions.

---

## Phase 7 — Upgrade Planning & Existing Systems

**Goal:** Parse existing PCs, bottleneck priority, phased roadmaps.

| Concern | Technology | Role |
|---------|------------|------|
| Existing system parser | **Pydantic AI** tool | NL + form → `ExistingSystem` schema |
| Upgrade planner | LangGraph subgraph | Reuses Compatibility + Performance agents |
| Cascade detection | Rules engine extensions | CPU change → board → RAM chain warnings |
| Roadmap export | **WeasyPrint** or **Playwright PDF** | Phased upgrade PDF quotes |
| Order import (future) | Teko Order API via commerce-adapter | Authenticated upgrade intake |

**Avoid:** Treating upgrades as greenfield builds; ignoring PSU/case reuse validation.

---

## Phase 8 — Commerce Actions & Checkout Handoff

**Goal:** Cart payload, promos, saved builds, B2B quotes.

| Concern | Technology | Role |
|---------|------------|------|
| Cart adapter | **commerce-adapter** (FastAPI) | Mock cart → Teko Cart API |
| Promo engine | **json-rules-engine** (Node) or Python rule tables | Combo PC+monitor, bundle discounts |
| Saved builds | PostgreSQL `saved_builds` | User-linked configurations |
| Revalidation on load | Catalog + rules version check | Stale price/stock warnings |
| B2B PDF quotes | **WeasyPrint** + HTML templates | Formal quotes with VAT notes |
| Analytics events | **Teko tracker-js** pattern / **Segment** | `cart.added`, `build.approved` |
| Webhooks | **Svix** or native signed webhooks | CRM / Zalo OA follow-up |

**Hackathon:** Ship with `MockCommerceAdapter` implementing Teko-shaped interfaces documented in OpenAPI.

**Avoid:** Hard-coded promo logic in LLM prompts; fake "add to cart" without SKU IDs.

---

## Phase 9 — Staff Copilot & Showroom Operations

**Goal:** Staff console, co-browse, QR handoff, objection cards.

| Concern | Technology | Role |
|---------|------------|------|
| Staff UI | **Next.js** route group `/staff` | Dual-pane: chat + build table |
| RBAC | **Better Auth** roles (`staff`, `lead`, `admin`) | Route protection |
| QR handoff | **qrcode** lib + short session codes | Online → showroom continuity |
| Co-browse | **Liveblocks** or **PartyKit** | Shared session state |
| Staff shortcuts | **cmdk** (Command Palette) | Fast slot swap, apply promo |
| Objection cards | PostgreSQL + MDX content | Contextual sales enablement |
| Lead capture | PostgreSQL + consent flags | PDPA-aware opt-in |
| CRM webhook | **Zalo OA API** / generic HTTPS | Follow-up automation |

**Teko alignment:** Staff back-office patterns mirror Teko `staff-interface` monorepo — table-heavy UI, design system consistency.

---

## Phase 10 — Administration, Rules & Content Management

**Goal:** Rules, weights, benchmarks, glossary, feature flags.

| Concern | Technology | Role |
|---------|------------|------|
| Admin framework | **Refine v4** + **Ant Design** | CRUD for rules, benchmarks, glossary |
| Feature flags | **GrowthBook** or **Flagsmith** (open-source) | Per-channel rollout |
| Rules dry-run | FastAPI `POST /admin/rules/dry-run` | Test against canonical builds |
| Audit log | PostgreSQL `audit_events` | Who changed weights/rules |
| Config storage | **AWS S3** + version IDs | Rule pack artifacts |
| Approval workflow | Simple status field (`draft` → `published`) | No need for heavy BPM early |

**Avoid:** Requiring code deploys for every new CPU socket; admin UI without dry-run.

---

## Phase 11 — Observability, Quality & Governance

**Goal:** Traces, evals, feedback, safety, business metrics.

| Concern | Technology | Role |
|---------|------------|------|
| LLM/agent tracing | **Langfuse** (self-host or cloud) | AABW Day 3 Design workshop partner |
| OTEL | **OpenTelemetry** Python SDK | Unified traces across FastAPI + agents |
| Error tracking | **Sentry** | Frontend + backend exceptions |
| Product analytics | **PostHog** (self-host) or **Mixpanel** | Funnels, feature usage |
| Business warehouse | **ClickHouse** | AABW partner — high-volume event analytics |
| Event pipeline | **ClickHouse** ← **Kafka** or **Redpanda** (optional) | `build.generated`, `cart.added` |
| Eval suite | **Langfuse Datasets + Experiments** | SPEC §11 canonical scenarios (T-01…T-10) |
| CI eval gate | **GitHub Actions** + `pytest` + Langfuse API | Block deploy on regression |
| Safety filters | **Llama Guard** / **Azure Content Safety** / regex policy layer | Block out-of-scope requests |
| User feedback | PostgreSQL `build_feedback` | Thumbs + admin review queue |
| Dashboards | **Grafana** or **Metabase** | Ops + business KPIs |

**Demo day tip:** Show one **Langfuse trace** with Intent → Catalog → Compatibility → Optimizer → Explainer spans. Judges weight production readiness heavily at AABW.

**Avoid:** Console.log debugging only; no eval set for compatibility regressions.

---

## Phase 12 — API & Embeddable Integration

**Goal:** Public API, embed widget, webhooks for Teko ecosystem.

| Concern | Technology | Role |
|---------|------------|------|
| API framework | **FastAPI** | OpenAPI 3.1, automatic docs |
| API docs UI | **Scalar** or **Swagger UI** | Developer-friendly reference |
| Auth | **API keys** + **OAuth 2.1** (Better Auth) | Partner integrations |
| Rate limiting | **Redis** + **slowapi** | Per-key quotas |
| Type generation | **openapi-typescript** | `packages/shared-types` for Next.js |
| Embed widget | **Vite** IIFE bundle or **Next.js** `embed.js` | Drop-in on phongvu.vn/buildpc |
| Webhooks | Signed HMAC payloads (**Svix** pattern) | `build.approved`, `cart.added` |
| SDK (future) | Auto-generated from OpenAPI | `teko-pc-copilot-client` |

**Embed integration target:**

```html
<script src="https://copilot.phongvu.vn/embed.js" data-context="gaming"></script>
```

**Avoid:** Undocumented internal APIs; breaking changes without OpenAPI version bumps.

---

## 5. Cross-Cutting Concerns

### 5.1 Security

| Item | Technology |
|------|------------|
| Secrets | **AWS Secrets Manager** or **Doppler** |
| Transport | TLS 1.3 everywhere |
| Headers | **helmet** (via Next.js config) + CORS allowlist |
| Input sanitization | Pydantic + **bleach** for user markdown |
| PII | Encrypt phone/Zalo fields at rest (PostgreSQL `pgcrypto` or app-level) |
| Dependency scanning | **GitHub Dependabot** + **pip-audit** + **npm audit** |

### 5.2 Testing Strategy

| Layer | Tool |
|-------|------|
| Rules engine unit | **pytest** + **hypothesis** |
| Agent tools unit | **pytest** with mocked catalog |
| API integration | **pytest** + **Testcontainers** (Postgres, Redis, Typesense) |
| Frontend unit | **Vitest** + **Testing Library** |
| E2E | **Playwright** — 3 demo flows (first-time, upgrade, staff) |
| Agent regression | **Langfuse Experiments** on T-01…T-10 |
| Load | **k6** — 100 concurrent build generations |

### 5.3 CI/CD

| Stage | Tool |
|-------|------|
| CI | **GitHub Actions** |
| Lint (PY) | **Ruff** + **mypy** |
| Lint (TS) | **ESLint** + **Prettier** |
| Monorepo | **Turborepo** remote cache |
| Containers | **Docker** multi-stage builds |
| Deploy | **AWS ECS Fargate** (agent-api) + **Vercel** (web) |
| IaC | **Terraform** or **AWS CDK** (optional) |

### 5.4 Local Development

```yaml
# docker-compose.yml services
services:
  postgres:     # pgvector enabled
  redis:
  typesense:
  agent-api:    # FastAPI hot reload
  web:          # Next.js dev
  langfuse:     # optional self-host for traces
```

**DX commands:**

```bash
pnpm dev              # Turborepo starts web + agent-api
pnpm db:migrate       # Alembic migrations
pnpm catalog:sync     # Scrape + index Typesense + pgvector
pnpm eval:run         # Langfuse regression suite
```

---

## 6. AABW 2026 Partner → Stack Mapping

Use these perks deliberately in your build week story:

| Partner | Use in PC Build Copilot |
|---------|-------------------------|
| **AWS** | ECS Fargate, RDS Postgres, ElastiCache, S3, Bedrock (Claude/Llama), CloudFront |
| **Langfuse** | Agent tracing, eval datasets, demo trace visualization |
| **ClickHouse** | Analytics pipeline for build → cart funnel |
| **Kimi (Moonshot)** | Primary Vietnamese explainer + intent LLM |
| **Tencent Cloud** | Qwen inference, optional hosting |
| **NVIDIA** | NIM APIs for future benchmark enrichment; Inception story |
| **BytePlus** | Alternative embeddings / inference |
| **Microsoft for Startups** | Azure OpenAI fallback |
| **Google for Developers** | Gemini Flash for cheap intent parsing |
| **Notion** | Spec, rule docs, glossary CMS (team workflow) |
| **TRAE / Cursor** | Accelerate implementation |
| **TinyFish** | Web agent for catalog scraping automation |
| **Bright Data / ZenRows** | Managed scrape if blocked |
| **Daytona** | Sandboxed agent dev environments |
| **Featherless** | Open-model hosting fallback |

---

## 7. Teko / Phong Vũ Integration Roadmap

| Stage | Integration | Stack touchpoint |
|-------|-------------|------------------|
| **Hackathon** | Mock Teko cart + scraped catalog | `commerce-adapter` mock |
| **Pilot** | Read-only Teko Product API | `catalog-sync` service |
| **Production** | Cart, promo, stock APIs | `commerce-adapter` real |
| **Full** | tracker-js events, SSO, showroom inventory | `web` analytics + auth |

Phong Vũ runs on **Teko Shopfront** (`shopfront-cdn.tekoapis.com`). Plan adapter interfaces to match Teko IDs even when mocking.

---

## 8. What NOT to Use (and Why)

| Technology | Why avoid for this project |
|------------|----------------------------|
| **Bubble / no-code** | Cannot implement deterministic compatibility engine |
| **Pure ChatGPT Custom GPT** | No cart integration, no versioned rules, not deployment-grade |
| **CrewAI as primary orchestrator** | Wrong fit for validation-gated commerce pipeline |
| **Single monolithic LLM prompt** | Hallucinated specs, no audit trail |
| **MongoDB as primary** | Relational builds/rules/benchmarks fit Postgres better |
| **Elasticsearch self-hosted** | Ops-heavy vs Typesense for facet catalog search |
| **Kubernetes for hackathon** | ECS Fargate or single Compose is enough |
| **Blockchain / Web3** | No product value for PC retail advisory |

---

## 9. Recommended Phase → Stack Checklist

Use this as an implementation order reference (not a timeline):

- [ ] **Phase 1:** Next.js + FastAPI + Postgres + Redis + Pydantic AI intent
- [ ] **Phase 2:** Typesense + pgvector + catalog-sync pipeline
- [ ] **Phase 3:** Python rules-engine package + pytest hypothesis tests
- [ ] **Phase 4:** Benchmark tables + Performance Agent lookups
- [ ] **Phase 5:** LangGraph orchestration + optimizer loop
- [ ] **Phase 6:** Template-grounded Explainer + Kimi/Qwen via LiteLLM
- [ ] **Phase 7:** Upgrade subgraph + PDF export
- [ ] **Phase 8:** Mock commerce-adapter + promo rules + saved builds
- [ ] **Phase 9:** Staff RBAC UI + QR handoff
- [ ] **Phase 10:** Refine admin + feature flags + rule dry-run
- [ ] **Phase 11:** Langfuse + ClickHouse + eval CI gate
- [ ] **Phase 12:** OpenAPI public API + embed widget + webhooks

---

## 10. Decision Matrix: When to Deviate

| If your team is… | Consider swapping… |
|------------------|-------------------|
| **TypeScript-only** | Mastra instead of LangGraph+Pydantic AI; Hono instead of FastAPI |
| **All-in AWS** | Strands Agents + Bedrock instead of LiteLLM multi-cloud |
| **No Python appetite** | LangGraph.js + Zod + Mastra (TS-native agents) |
| **Need fastest search setup** | Meilisearch instead of Typesense (similar capabilities) |
| **Heavy ML team** | Replace greedy optimizer with OR-Tools CP-SAT full time |

**Default recommendation remains Python agents + Next.js UI** for best AABW partner coverage and spec fit.

---

## 11. References

- [PC Build Copilot SPEC](./PC-Build-Copilot-SPEC.md)
- [Langfuse — AI Agent Framework Comparison (2025)](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)
- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Next.js 15 Release](https://nextjs.org/blog/next-15)
- [Kimi Developer Platform](https://platform.kimi.ai/)
- [Teko Engineering Blog](https://engineering.teko.vn/front-end-engineer-myths-and-facts/)
- [Phong Vũ Build PC](https://phongvu.vn/buildpc)
- [Agentic AI Build Week 2026](https://aabw.genaifund.ai/)

---

*PC Build Copilot — Technology Stack Guide — Phong Vũ Retail Track*
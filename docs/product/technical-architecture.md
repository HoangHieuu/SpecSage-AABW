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

## Current Catalog Health Slice

`US-016`, `US-017`, and `US-039` make catalog readiness, variety, freshness,
and production gaps explicit in the local validation report:

- `CatalogValidationReport.category_counts`
- `CatalogValidationReport.specs_confidence_counts`
- `CatalogValidationReport.recommended_demo_category_counts`
- `CatalogValidationReport.pilot_recommended_category_counts`
- `CatalogValidationReport.production_target_category_counts`
- `CatalogValidationReport.required_demo_categories`
- `CatalogValidationReport.missing_required_demo_categories`
- `CatalogValidationReport.thin_demo_categories`
- `CatalogValidationReport.thin_pilot_categories`
- `CatalogValidationReport.production_gap_categories`
- `CatalogValidationReport.stale_after_days`
- `CatalogValidationReport.freshness_checked_at`
- `CatalogValidationReport.snapshot_fresh_until`
- `CatalogValidationReport.snapshot_age_days`
- `CatalogValidationReport.freshness_status`
- `CatalogValidationReport.demo_ready`
- `CatalogValidationReport.pilot_ready`
- `CatalogValidationReport.production_ready`

`GET /catalog/health` returns those fields from validation over the current
snapshot. Missing CPU, mainboard, RAM, storage, VGA, PSU, or case coverage is a
blocking catalog validation issue because those categories are required for the
current full-build demo flow. Present-but-thin demo categories are warning
issues, not blockers; the demo recommended minimum remains two SKUs for each
required category. The pilot recommended minimum is three SKUs for each
required category, plus a fresh snapshot inside the 7-day window. Production
readiness requires the broader target counts from `Data.md`, including cooler
and monitor coverage. This does not add live scraping, external catalog APIs,
Typesense, Postgres, or admin catalog editing.

## Current Catalog Ingestion Slice

`US-018` makes the local mirror expandable through a source manifest:

- `services/agent-api/catalog/catalog_sources.json`
- `services/agent-api/src/pc_build_copilot/catalog_cli.py`
- `services/agent-api/src/pc_build_copilot/catalog_capture_cli.py`
- `services/agent-api/src/pc_build_copilot/catalog_source_report_cli.py`
- `services/agent-api/catalog/catalog_snapshot.json`

The manifest lists saved public Phong Vu payloads in deterministic order. The
sync command merges all products, deduplicates by SKU before applying curated
overrides, records source provenance, validates the final snapshot, and leaves
the existing single-input CLI mode available for focused debugging. This keeps
Phase 2 moving toward broader coverage without requiring live scraping or
private APIs.

`US-019` adds `pnpm catalog:capture` as the preceding capture step. It validates
public Phong Vu category HTML before writing a sanitized `__NEXT_DATA__`-only
fixture or upserting a manifest entry. Tests use local input files so the
normal quality gate does not depend on live Phong Vu availability.

`US-020` adds staged manifest entries with `enabled=false`. Staged sources are
excluded from `catalog:sync` and active recommendations, but
`pnpm catalog:source-report` parses them to report candidate counts, duplicate
counts, invalid rows, and category coverage. This keeps broad public captures
auditable while preserving the deterministic active catalog gate.

`US-022` adds `include_skus` to manifest entries. When present, sync and source
reporting normalize the referenced fixture but keep only those listed SKUs.
This lets the local mirror promote reviewed products from staged captures while
leaving the broad category pages non-eligible. The active snapshot now contains
14 SKUs with two CPU, mainboard, RAM, storage, VGA, PSU, and case choices and
zero catalog validation issues.

`US-039` keeps the same curated promotion mechanism and adds one more reviewed
SKU per required full-build category. The active snapshot now contains 21 SKUs
with three CPU, mainboard, RAM, storage, VGA, PSU, and case choices, 14
verified rows, 7 partial rows, zero blocking validation issues, `pilot_ready =
true`, and `production_ready = false` because full production target counts are
not met yet.

`US-040` adds curated cooler and monitor entries through the same
`include_skus` gate. The active snapshot now contains 27 SKUs with three
optional cooler choices and three optional monitor choices in addition to the
required full-build categories. Cooler rows must include `socket_support`,
`tdp_rating_w`, and `height_mm`; monitor rows must include `resolution` and
`refresh_rate_hz`. These rows reduce catalog health gaps and prepare optional
slot work, but they do not change `REQUIRED_FULL_BUILD_SLOTS` or make the
generator select cooler or monitor parts by default.

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
- `POST /builds/{id}/alternatives/{variant_id}/apply`
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

`US-029` adds a bounded budget-aware improvement pass to generation for creator,
AI, and streaming use cases. `US-031` enables gaming GPU auto-swaps only when
the candidate preserves exact benchmark evidence, and `US-033` expands the pass
to at most two eligible swaps. The generator still starts from the cheapest
compatible build, then reuses ranked alternatives from the same catalog
snapshot. Each selected variant must be:

- within budget
- compatibility-approved
- ranked `recommended` for non-gaming use cases
- benchmark-preserving and GPU-kind for gaming use cases

The optimized build is rebuilt after each swap through the same compatibility,
budget, performance, warnings, explanations, and mock cart payload path. Office
and student builds remain unchanged in this slice so office efficiency guidance
is not hidden by under-proven swaps.

`US-034` adds benchmark-delta scoring to ranked gaming alternatives. The scorer
compares only benchmark evidence already emitted by `PerformanceProfile` for
the same exact target. A source-backed GPU lift can move the GPU variant above
generic capacity/headroom alternatives, while generated build explanations still
avoid raw numeric FPS text outside benchmark evidence.

`US-035` adds `BuildArtifact.optimizer_trace` as the first inspectable Phase 5
optimizer loop contract:

- `services/agent-api/src/pc_build_copilot/optimizer_policy.py`
- `OptimizerBudgetAllocation`
- `OptimizerIterationDecision`
- `OptimizerTrace`
- `apps/web/components/build-copilot-client.tsx`

The loop computes use-case allocation weights, applies priority overrides for
GPU/VGA, quiet operation, and RGB/aesthetic intent, then records candidate
decisions as accepted, rejected, or skipped. The existing safety gates still
own final behavior: catalog-only SKUs, compatibility rules, budget status, and
benchmark-preserving gaming auto-swaps. The browser keeps this trace behind
`Chi tiết hỗ trợ` so customers see the recommendation first while demo/support
users can still inspect the agent decisions. `US-036` uses this support
disclosure in the browser demo; it does not add a new endpoint, storage table,
checkout adapter, or staff/admin surface.

`US-037` adds the first natural-language iteration endpoint:

- `POST /builds/{build_id}/iterate`
- `services/agent-api/src/pc_build_copilot/build_iteration.py`
- `BuildIterationRequest`
- `BuildIterationResponse`
- `ParsedBuildIterationCommand`

The endpoint parses a bounded Vietnamese command set for cheaper/under-budget,
quieter, more FPS/NVIDIA, more SSD/storage, and more RAM. It reuses ranked
alternatives, compatibility checks, budget checks, performance profile
generation, and the versioned apply path. Budget-saver downgrade variants are
only generated for the iterate endpoint, so the public alternatives panel keeps
its existing upgrade-oriented surface by default. The applied build appends the
accepted and rejected command decisions to `optimizer_trace` and stores a
single optimizer trace event for replay.

## Current Commerce Handoff Slice

`US-005` adds mock approval and cart-ready handoff without introducing checkout,
auth, payment, Teko provider APIs, or persistent storage:

- `POST /builds/{build_id}/approve`
- `services/agent-api/src/pc_build_copilot/build_store.py`
- `apps/web/components/build-copilot-client.tsx`

Approval is allowed only when the generated build has `can_approve=true` and
status `generated`. The handoff contains real SKU links from the existing build
artifact and remains labeled as a mock cart payload.

`US-010` persists the same handoff payload in the local SQLite product store for
restart-safe demos; real checkout, auth, payment, and Teko provider APIs remain
out of scope.

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

## Current Performance Fit Slice

`US-007` adds a deterministic qualitative profile to generated builds:

- `services/agent-api/src/pc_build_copilot/performance_profile.py`
- `BuildArtifact.performance_profile`
- `apps/web/components/build-copilot-client.tsx`

The profile is generated from selected SKU facts plus the confirmed
`BuildIntent`. It labels workload fit, confidence, evidence, bottlenecks, and
warnings for gaming, creator, AI/local LLM, office, and student use cases. It
may mention facts such as RAM capacity, CPU core/thread counts, storage type,
and GPU VRAM, but it must not invent FPS, benchmark deltas, or game-specific
numeric outcomes.

`US-023` adds the first maintained benchmark source:

- `services/agent-api/benchmarks/gaming_benchmark_matrix.json`
- `services/agent-api/src/pc_build_copilot/performance_benchmarks.py`
- Optional `source_label` and `source_url` on `PerformanceEvidence`

Gaming FPS evidence is emitted only when the selected GPU chipset, target game,
resolution, and preset match a matrix row exactly. The profile raises
`PERF_BELOW_TARGET` when a matched benchmark row is below the declared
high-refresh target. If no row matches, the build stays qualitative and shows a
no-benchmark warning for demanding requests rather than interpolating or asking
an LLM to estimate performance.

`US-030` adds an exact RTX 4060 Cyberpunk 2077 1440p Ultra native row to the
same matrix. This keeps future gaming optimizer work from swapping to the
second active GPU SKU and losing warning provenance for that target. `US-031`
then enables gaming GPU auto-swaps only when candidate GPUs can preserve exact
benchmark evidence for the requested game, resolution, and preset.

`US-032` adds an exact RX 7600 Cyberpunk 2077 1080p Ultra native row. This
extends benchmark-backed evidence for a common lower-resolution target while
preserving the exact-match rule. Unsupported resolutions still return no
benchmark evidence rather than falling back to nearby rows.

`US-024` adds monitor overspec warning logic without monitor SKU
recommendations. The intent parser records monitor/display mentions in
`BuildIntent.mentioned_components`. If the user mentions a monitor target and a
matched benchmark estimate is below the requested refresh rate, the performance
profile raises `PERF_MONITOR_OVERSPEC`. `US-040` adds curated monitor rows to
the active catalog, but this deliberately still does not add monitor items to
builds until a dedicated recommendation story defines ranking and UX behavior.

`US-025` adds deterministic balance scoring to the same profile. The scorer
uses selected SKU facts only: CPU cores/threads, GPU chipset/VRAM, RAM
capacity, and storage interface/capacity. `PerformanceProfile.balance` carries a
0-100 score, Vietnamese interpretation, first limiting component, factor values,
and upgrade suggestions. Severe imbalance adds `PERF_IMBALANCE` to warnings.
The field is explanatory in this slice and does not change optimizer decisions,
alternatives ranking, or approval gates.

`US-026` adds app-level workload profiles to `PerformanceProfile`:

- `PerformanceProfile.workload_profiles`
- Parser support for OBS/streaming apps and local LLM model classes such as
  `7B`, `13B`, and `70B`
- UI `App fit` rows in the existing workload fit panel

Profiles are deterministic threshold checks for Premiere, After Effects,
Photoshop, Blender, OBS/streaming, and local LLM. They report fit level,
bottleneck labels, requirement summary, and recommendation text from selected
SKU facts. They do not claim app benchmark throughput, render time, or tokens
per second.

`US-027` adds office/general-use adequacy to the same profile surface:

- `BuildIntent.monitor_count`
- office/student iGPU versus discrete GPU suitability notes
- qualitative quiet/power guidance for office requests
- `OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN` when the user asks for two or more
  monitors but output-port specs are absent

This remains a deterministic profile rule. It does not add monitor SKUs to
builds and does not infer HDMI/DisplayPort support from product names.

## Current Build Alternatives Slice

`US-008` adds the first Phase 5 iteration surface without introducing
LangGraph checkpointing, PostgreSQL, OR-Tools, or persisted variant history:

- `GET /builds/{build_id}/alternatives`
- `services/agent-api/src/pc_build_copilot/build_alternatives.py`
- `BuildAlternativesResponse`
- `apps/web/components/build-copilot-client.tsx`

The alternatives service starts from a stored generated build, reuses the local
catalog snapshot, swaps one supported slot at a time, reruns deterministic
compatibility rules, recomputes budget status, and regenerates the qualitative
performance profile. Current curated variants cover RAM upgrade, larger SSD,
NVIDIA GPU, and PSU headroom when matching SKUs exist in the snapshot.

`US-028` adds ranking metadata to each returned alternative:

- `rank`
- `score`
- `priority`
- `reasons_vi`

The ranking score is computed from existing deterministic facts: compatibility
and budget eligibility, performance fit deltas, balance score deltas, app
workload fit deltas, warning deltas, and use-case relevance. The API returns
alternatives sorted by score. Ranking does not add SKUs, skip validation, or
auto-apply variants.

This follows the `techstack.md` Phase 5 recommendation for alternatives and
slot-level diffs, but keeps the hackathon implementation narrow: no autonomous
optimizer loop, no long-running orchestration, no external provider calls, and
no persisted variant history.

## Current Alternative Apply Slice

`US-009` adds the second Phase 5 iteration surface without introducing
LangGraph checkpointing, PostgreSQL, OR-Tools, or persisted history:

- `POST /builds/{build_id}/alternatives/{variant_id}/apply`
- `services/agent-api/src/pc_build_copilot/build_alternatives.py`
- `apps/web/components/build-copilot-client.tsx`

Applying an alternative re-derives the selected variant from the stored base
build and the current local catalog snapshot, then creates a new `BuildArtifact`
with a fresh `build_id` and `build_version = base + 1`. Compatibility rules and
the qualitative performance profile are rerun against the applied SKU set using
the new build ID. The original build remains retrievable and unchanged.

Applying a variant does not approve it. The existing `POST /builds/{build_id}/approve`
gate still decides whether the active build is compatible, within budget, and
ready for mock cart handoff.

## Current Local Persistence Slice

`US-010` adds a local durable store without introducing Postgres credentials,
Redis, auth, account history, or production migrations:

- `services/agent-api/src/pc_build_copilot/sqlite_store.py`
- Default DB path: `.local/pc-build-copilot.sqlite3`
- Override env var: `PC_BUILD_COPILOT_DB_PATH`
- Tables: `build_sessions`, `intent_revisions`, `build_artifacts`,
  `cart_handoffs`

The SQLite store persists full Pydantic payload JSON for each domain object and
keeps the existing API contracts unchanged. Tests can still inject the
in-memory `SessionStore` and `BuildStore` for isolated proof.

SQLite is a local hackathon bridge. PostgreSQL remains the production target for
LangGraph checkpointing, account-linked saved builds, catalog/search expansion,
analytics, and multi-user history.

## Current LangGraph Orchestration Slice

`US-011` introduces the first real LangGraph runtime without replacing the
deterministic build path:

- `services/agent-api/src/pc_build_copilot/build_orchestrator.py`
- `BuildArtifact.orchestration_trace`
- `apps/web/components/build-copilot-client.tsx`

The graph is a sequential `StateGraph` with catalog, optimizer, compatibility,
performance, explainer, and validator steps. The optimizer node currently calls
the existing deterministic build generator, and later nodes record facts from
the generated artifact. This keeps SKU selection, prices, budget status,
compatibility reports, performance fit, approval gates, alternatives, and mock
cart handoff behavior unchanged.

This is a foundation slice, not the full Phase 5 optimizer loop. LangGraph
checkpointing, PostgreSQL/Redis checkpointers, OR-Tools, Pydantic AI build
agents, parallel Pareto variants, and external provider calls remain future
story work.

## Current Trace Replay Slice

`US-012` exposes local agent trace replay without adding external observability
credentials:

- `services/agent-api/src/pc_build_copilot/trace_replay.py`
- `GET /builds/{build_id}/trace`
- `GET /sessions/{build_session_id}/trace`
- `apps/web/components/build-copilot-client.tsx`

Replay is derived from persisted `BuildArtifact.orchestration_trace` payloads
and grouped by `build_session_id` plus build version. Each event includes agent
name, status, redacted inputs, tool-call labels, redacted outputs, local
latency, and deterministic model/runtime version metadata. The session response
also returns a support-export text block.

No new trace table is added yet. Langfuse, OpenTelemetry, Sentry, ClickHouse,
and cross-service production telemetry remain future Phase 11 work.

## Current Quality Evaluation Slice

`US-013` adds a local quality evaluation foundation:

- `evals/canonical_build_scenarios.json`
- `services/agent-api/src/pc_build_copilot/evaluation.py`
- `services/agent-api/src/pc_build_copilot/evaluation_cli.py`
- `pnpm eval:run`

The runner loads canonical scenarios, parses intent, generates a build through
the LangGraph-wrapped deterministic path, and checks expected use case, budget
status, build status, approval gate, compatibility expectation, required slots,
catalog SKU grounding, absence of numeric FPS claims, and explanation rubric
score.

This is the local release gate before Langfuse Datasets/Experiments, GitHub
Actions, or LLM-as-judge review. The rubric score is a deterministic proxy
until a human review workflow exists.

## Current Feedback Loop Slice

`US-015` adds customer feedback capture on generated build artifacts:

- `BuildFeedbackRequest`, `BuildFeedback`, and `PartFeedback`
- `POST /builds/{build_id}/feedback`
- `GET /builds/{build_id}/feedback`
- `GET /feedback/review-queue`
- `build_feedback` in the local SQLite store
- `BuildFeedbackPanel` in the web client

Feedback is tied to the immutable build id, build session id, build version,
catalog version, and rules version. Part-level feedback must reference a SKU in
the generated build artifact; the API rejects mismatched SKUs instead of
accepting free-form part claims.

Low overall ratings or low part ratings mark the record as `queued` for the
local review queue. This is not a staff/admin console, RBAC system, analytics
warehouse, or production moderation workflow.

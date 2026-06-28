# PC Build Copilot Overview

## Product

**PC Build Copilot for Phong Vu** is a Vietnamese-first agentic retail advisor
that converts customer intent into compatible, budget-aware, purchase-ready PC
configurations grounded in real Phong Vu SKUs.

The product is not a generic chatbot. It is a tool-using workflow:

```text
intent -> catalog retrieval -> compatibility checks -> performance fit
  -> optimization -> explanation -> validation -> commerce handoff
```

## Product Principles

- Agentic, not conversational: the system plans, calls tools, iterates,
  validates, and returns actionable builds.
- Deterministic where safety matters: compatibility and PSU rules are enforced
  by code and versioned rule packs.
- Grounded commerce: recommendations use Phong Vu catalog snapshots, real SKU
  IDs, prices, stock signals, and product links.
- Explain trade-offs: each part choice should connect to the user's use case,
  budget, and constraints.
- Vietnamese-first: UI, explanations, warnings, and help text are Vietnamese;
  technical component names and SKU labels remain precise.
- Staff-augmenting: future staff tools reuse the same product intelligence.

## Users

| Persona | Core need |
| --- | --- |
| First-time builder | Safe defaults, simple explanations, full build guidance |
| Gaming enthusiast | FPS fit, GPU-heavy budget allocation, upgrade headroom |
| Creator / pro user | VRAM, RAM, storage, and stability guidance |
| Upgrade buyer | Reuse-vs-replace and bottleneck-aware recommendations |
| Parent / gift buyer | Confidence, value, warranty clarity |
| Showroom staff | Fast build generation, objection handling, promos |
| Ops / merchandising admin | Catalog health, rules, benchmarks, analytics |

## Current Hackathon Scope

The first demo should prove a narrow vertical slice:

1. A Vietnamese user describes a target PC build.
2. The system parses a structured intent.
3. A local catalog snapshot returns real candidate SKUs.
4. Deterministic rules block invalid hardware combinations.
5. The optimizer produces one compatible build under or near budget.
6. The UI shows parts, total, compatibility status, and grounded explanations.
7. The generated build shows a workload fit profile grounded in catalog facts,
   with FPS evidence only when a local benchmark matrix row matches exactly.
8. The user can inspect validated alternative variants with slot-level deltas
   and price trade-offs.
9. The user can apply a selected alternative as the active build version.
10. The user approves a safe generated build and receives a mock cart-ready
   handoff with real SKU links.
11. The generated build carries an agent orchestration trace showing the
    LangGraph catalog, optimizer, compatibility, performance, explainer, and
    validator steps.
12. Engineers can replay generated build traces by session/build version and
    copy a redacted support trace export.
13. Product owners can run canonical local quality evals before changing build
    logic.
14. Catalog health reports whether the local snapshot is demo-ready for the
    required full-build categories before generation or evals run.
15. Catalog health reports thin required categories as non-blocking variety
    warnings before broader SKU expansion.
16. Engineers can capture saved public Phong Vu category payloads into fixtures
    and manifest entries before broadening the local catalog snapshot.
17. Engineers can stage captured category payloads and report candidate
    coverage without making unverified SKUs recommendation-eligible.
18. Engineers can promote a reviewed subset from staged category captures into
    the active catalog without enabling the full unverified source.
19. Gaming customers who mention a monitor target get a warning when benchmark
    evidence shows the PC is unlikely to sustain the requested refresh rate.
20. Generated builds include a deterministic balance score so customers can see
    the first limiting component before approving or upgrading.
21. Creator, streaming, and local LLM requests show app-level fit rows with RAM,
    VRAM, CPU, storage, and CUDA guidance.
22. Office and student requests explain iGPU/discrete GPU suitability,
    quiet/power guidance, and multi-monitor validation gaps.
23. Alternatives are ranked by deterministic performance, budget,
    compatibility, and workload signals before the user applies one.
24. Creator, AI, and streaming generated builds can apply a recommended
    budget-safe optimizer improvement before returning the base recommendation.
25. Gaming generated builds can auto-apply a GPU swap only when the candidate
    preserves exact benchmark evidence and warning provenance.
26. The benchmark matrix can grow with source-backed exact rows for active GPU
    and target combinations without interpolation.
27. Generated builds can apply up to two eligible budget-safe optimizer swaps
    before returning, while rebuilding the artifact after each swap.
28. Gaming alternatives can rank GPU swaps by exact source-backed benchmark
    delta when base and candidate evidence match the same target.

Current first-slice implementation reaches step 28 with a deterministic
fixture-backed generator, performance fit profile, alternatives panel, mock
cart handoff, replayable agent traces, local quality gates, feedback capture,
and curated catalog subset promotion. It produces one build from the local
catalog snapshot, validates it through the compatibility rule engine, reports
explicit budget gaps when the current snapshot cannot satisfy a low budget,
summarizes workload fit from CPU/GPU/RAM/storage facts, adds benchmark-backed
FPS evidence only for exact matrix matches, warns when a requested monitor
refresh target exceeds matched benchmark FPS, explains CPU/GPU/RAM/storage
balance with a 0-100 score, shows app-level workload fit for creator,
streaming, and local LLM workflows, explains office iGPU/discrete GPU
suitability and multi-monitor validation gaps, returns ranked deterministic
upgrade alternatives from the same catalog snapshot, applies one recommended
budget-safe optimizer swap for streaming builds, applies up to two eligible
budget-safe optimizer swaps for creator and local LLM builds, allows gaming GPU
auto-swaps only when exact benchmark evidence is preserved, ranks gaming GPU
alternatives by exact benchmark delta when comparable evidence exists, applies a
selected alternative as a new active build version, and creates a mock cart-ready
handoff only after approval gates pass. `US-006` adds an advisory OpenRouter LLM
layer to the intent step.
That layer summarizes customer needs and suggests clarifying questions in
Vietnamese, but it does not choose SKUs, prices, compatibility outcomes, budget
gates, approval, alternatives, applied builds, performance claims, or cart
handoff payloads.

`US-010` adds local SQLite persistence for sessions, intent revisions, build
artifacts, applied build versions, and mock cart handoffs so the demo can
survive an Agent API process restart without requiring Postgres credentials.
`US-011` routes build generation through a bounded LangGraph state graph and
surfaces a schema-valid orchestration trace while preserving deterministic SKU,
price, compatibility, workload fit, approval, and handoff behavior.
`US-012` adds local trace replay endpoints and a web replay panel derived from
persisted build artifacts. It is a hackathon observability bridge before
Langfuse/OpenTelemetry integration, not production telemetry.
`US-013` adds 30 local canonical evaluation scenarios and a `pnpm eval:run`
release gate before Langfuse datasets or hosted CI are available.
`US-014` promotes `pnpm check` and `pnpm eval:run` into a GitHub Actions quality
gate for pull requests and pushes to `main`.
`US-015` captures overall and part-level build feedback tied to build,
catalog, and rules versions, with low ratings marked for local review.
`US-016` adds demo-readiness category coverage to catalog health so missing
required full-build categories are caught as catalog validation failures.
`US-017` adds non-blocking variety warnings so present-but-thin required
categories remain visible without blocking the current demo flow.
`US-018` adds a multi-source catalog manifest so broader saved Phong Vu payload
coverage can be added without changing parser code for each category.
`US-019` adds a local capture command for public category payloads so fixture
creation and manifest updates are repeatable before any scheduled scraping or
private catalog API integration.
`US-020` adds staged source entries and a source coverage report so broad public
category captures can be measured before verified overrides make any new SKU
eligible for recommendation.
`US-021` sanitizes committed catalog fixtures so public page-shell environment
blocks are removed while the parseable `__NEXT_DATA__` product payload remains
available to local catalog tooling.
`US-022` promotes three reviewed SKUs from staged CPU, mainboard, and case
captures via `include_skus`, so the active local snapshot has two choices in
every required full-build category without enabling full category pages.
`US-023` through `US-030` add benchmark-backed gaming evidence, monitor
overspec warnings, balance scoring, creator/AI/streaming app-fit rows, office
adequacy guidance, deterministic alternative ranking, a first one-swap
optimizer pass, and benchmark coverage needed for safe RTX 4060 Cyberpunk
1440p swaps.
`US-031` enables gaming GPU auto-swaps only when the candidate preserves exact
benchmark evidence and warning provenance.
`US-032` adds RX 7600 Cyberpunk 2077 1080p Ultra evidence while keeping
unsupported targets unsupported.
`US-033` expands generation from one eligible optimizer swap to a bounded
two-swap pass, rebuilding the artifact after each swap.
`US-034` adds benchmark-delta scoring so source-backed GPU improvements outrank
generic gaming alternatives when both builds have exact evidence for the same
target.

Out of first-slice scope unless a later story selects it:

- Customer auth and saved account history.
- Real Teko cart checkout.
- Staff RBAC and showroom console.
- Admin CRUD for rules, benchmarks, and glossary.
- Production analytics warehouse.
- Full Phong Vu/Teko private API integration.

## Phase Map

| Phase | Product area | Harness posture |
| --- | --- | --- |
| 1 | Session foundation and intent capture | First build slice |
| 2 | Catalog intelligence and product grounding | First build slice |
| 3 | Compatibility and safety engine | First build slice |
| 4 | Performance modeling and workload fit | Qualitative by default; source-backed benchmark seed, monitor warnings, balance scoring, app-fit thresholds, and office adequacy guidance |
| 5 | Build optimization and iteration | Deterministic alternatives, apply flow, performance-aware ranking, benchmark-gated gaming optimization, and bounded two-swap generation |
| 6 | Explanation and education | First vertical slice |
| 7 | Upgrade planning | Later |
| 8 | Commerce actions and checkout handoff | Mock first, real adapter later |
| 9 | Staff copilot and showroom operations | Later high-risk |
| 10 | Administration and rules CMS | Later high-risk |
| 11 | Observability, quality, governance | Start with Langfuse traces and evals |
| 12 | API and embeddable integration | Later public contract |

## Source Hierarchy

`SPEC.md`, `Data.md`, `techstack.md`, and `tools.md` are input snapshots.
Current product truth lives here and in story packets, validation records, and
decision records.

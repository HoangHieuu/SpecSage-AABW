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
7. The generated build shows a qualitative workload fit profile grounded in
   catalog facts, without FPS or benchmark claims.
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

Current first-slice implementation reaches step 10 with a deterministic
fixture-backed generator, performance fit profile, alternatives panel, and mock
cart handoff. It produces one build from the local catalog snapshot, validates
it through the compatibility rule engine, reports explicit budget gaps when the
current snapshot cannot satisfy a low budget, summarizes qualitative workload
fit from CPU/GPU/RAM/storage facts, returns deterministic upgrade alternatives
from the same catalog snapshot, applies a selected alternative as a new active
build version, and creates a mock cart-ready handoff only after approval gates
pass. `US-006` adds an advisory OpenRouter LLM layer to the intent step.
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
| 4 | Performance modeling and workload fit | Qualitative profile first; benchmark table later |
| 5 | Build optimization and iteration | First vertical slice |
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

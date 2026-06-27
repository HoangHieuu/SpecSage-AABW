# Architecture

This repository now has an accepted product and stack direction derived from
`SPEC.md`, `Data.md`, and `techstack.md`.

## Product Surfaces

Initial surface:

- Customer web app for Vietnamese PC build guidance.
- FastAPI agent API for sessions, intent parsing, build generation, validation,
  alternatives, and mock cart payloads.

Later surfaces:

- Staff console.
- Admin/rules console.
- Embeddable widget.
- Public API and webhooks.

## Runtime Stack

| Concern | Decision |
| --- | --- |
| Frontend | Next.js 15 App Router, React 19, Tailwind CSS 4, shadcn/ui |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Agent orchestration | LangGraph plus Pydantic AI |
| LLM routing | LiteLLM with Kimi/Qwen/Claude/OpenAI fallbacks |
| Data | PostgreSQL 16, pgvector, Redis, Typesense |
| Jobs | ARQ or BullMQ depending on service boundary |
| Observability | Langfuse, OpenTelemetry, Sentry |
| Deploy | AWS backend, Vercel optional frontend |

## Core Domains

- Build sessions.
- Build intent.
- Catalog SKUs and enriched specs.
- Compatibility rules and reports.
- Performance profiles.
- Build configurations and variants.
- Explanations and glossary.
- Commerce handoff payloads.
- Observability/evaluation records.

## Layering

```text
domain
  <- application
      <- infrastructure
          <- interface
              <- app surfaces
```

Inner layers must not depend on framework, database, UI, provider SDKs, or
process environment. Boundary parsers translate unknown data into typed
commands, DTOs, and domain objects before rules or optimization logic sees it.

## First Implementation Shape

Create folders only as stories require them:

```text
apps/web
services/agent-api
services/catalog-sync
services/commerce-adapter
packages/shared-types
packages/ui
evals
infra
```

The first vertical slice should not scaffold staff, admin, auth, checkout, or
warehouse analytics unless the selected story explicitly includes them.

## Hard Boundaries

- Compatibility checks are code/rule-pack outputs, never LLM judgments.
- Catalog recommendations must reference local snapshot SKUs.
- Numeric claims must trace to catalog, rules, benchmarks, or build artifacts.
- Mock cart payloads must be labeled as mock until a real Teko adapter exists.
- Staff/admin/auth work is high-risk and needs a dedicated story packet before
  implementation.

## Observability Contract

Backend requests should eventually emit structured JSON logs with:

- timestamp
- level
- request_id
- build_session_id when known
- user_id or staff_id when known
- action
- duration_ms
- status_code
- message

Agent traces should include agent name, input schema, tool calls, output schema,
latency, model version, catalog version, and rules version. PII must be
redacted from traces.

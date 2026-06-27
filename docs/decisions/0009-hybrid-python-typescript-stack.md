# 0009 Hybrid Python And TypeScript Stack

Date: 2026-06-27

## Status

Accepted

## Context

PC Build Copilot needs a production-grade web surface, typed API contracts,
multi-agent orchestration, deterministic hardware rules, catalog/search jobs,
and Vietnamese explanation generation.

The source stack guide recommends TypeScript for user-facing apps and Python
for agent, rule, and catalog logic.

## Decision

Use a hybrid stack:

- TypeScript/React/Next.js for web, staff/admin surfaces, shared UI, and
  OpenAPI-generated frontend types.
- Python/FastAPI/LangGraph/Pydantic AI for agent orchestration, catalog sync,
  compatibility rules, performance lookup, and optimization.
- PostgreSQL, pgvector, Typesense, and Redis for durable catalog/session/search
  needs.
- LiteLLM for model routing, with Kimi/Qwen/Claude/OpenAI as provider options.

Compatibility rules remain pure code/rule-pack logic and are not delegated to
LLM judgment.

## Consequences

Positive:

- Each language is used where its ecosystem is strongest.
- OpenAPI can define the frontend/backend boundary.
- Agent traces and evals fit Langfuse/OpenTelemetry patterns.

Tradeoffs:

- Two toolchains must be maintained.
- Shared contracts need generation or schema discipline to avoid drift.

# Test Matrix

This file maps product behavior to proof. Durable proof status also lives in
`harness.db`; prefer `scripts/bin/harness-cli query matrix` before work.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-000 | Harness product contract is wired from source snapshots into living docs, stories, decisions, and tool registry | no | no | no | no | implemented | `git diff --check`; Harness rows created |
| US-001 | User can start a session and express/confirm Vietnamese build intent | yes | yes | yes | no | implemented | `pnpm check`; Browser desktop flow |
| US-002 | Catalog snapshot contains real Phong Vu SKUs with enriched compatibility fields | yes | yes | no | no | implemented | `pnpm catalog:sync`; `.venv/bin/python -m pytest services/agent-api/tests`; 7-SKU snapshot with 0 blocking validation issues |
| US-003 | Deterministic compatibility rules block invalid builds and report remediation | yes | yes | no | no | implemented | `pnpm check`; `scripts/bin/harness-cli story verify US-003`; rule tests cover socket, RAM, PSU, GPU connector, GPU/case clearance, cooler/case clearance |
| US-004 | System generates an explained compatible build from confirmed intent and catalog snapshot | yes | yes | yes | no | implemented | `pnpm check`; browser E2E happy path and over-budget path; generated 7-row SKU build with catalog/rules versions and Phong Vu links |
| US-005 | User approves a safe generated build and receives mock cart-ready handoff | yes | yes | yes | no | implemented | `pnpm check`; Browser happy path to cart-ready handoff with 7 SKU links; over-budget path kept approval blocked and rendered no cart panel |
| US-006 | OpenRouter LLM adds advisory Vietnamese intent analysis without replacing deterministic parser/rules | yes | yes | yes | yes | implemented | `pnpm check`; Playwright browser flow showed `LLM Agent` available with `deepseek/deepseek-v4-flash`, then confirmed intent and generated valid 7-SKU build; direct OpenRouter diagnostic returned HTTP 200 |
| US-007 | Generated builds include deterministic qualitative workload fit profile without FPS or benchmark claims | yes | yes | yes | no | implemented | `pnpm check`; API tests cover gaming, creator, AI, and office profile thresholds plus generate endpoint shape; browser E2E displays `Workload fit` profile after build generation |
| US-008 | Generated builds expose deterministic catalog-grounded alternatives with slot deltas and compatibility proof | yes | yes | yes | no | implemented | `pnpm check`; API tests cover grounded variants, changed slots, generate endpoint storage, and missing-build 404; browser E2E displays `Alternatives` after build generation |
| US-009 | User can apply a selected alternative as a new active build version before approval handoff | yes | yes | yes | no | implemented | `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py`; API tests cover versioned apply helper, apply endpoint storage, original-build preservation, missing-variant 404, and approval after apply; browser E2E applies RAM upgrade and approves applied build |
| US-010 | Sessions, intent revisions, build artifacts, applied variants, and mock cart handoffs survive Agent API restart | yes | yes | yes | no | implemented | `.venv/bin/python -m pytest services/agent-api/tests/test_sqlite_persistence.py`; restart-survival tests cover sessions, revisions, build artifacts, applied variants, idempotent handoffs, and default env DB path; browser E2E uses default persistent API flow |
| US-011 | Build generation runs through a bounded LangGraph multi-agent orchestration trace without weakening deterministic gates | yes | yes | yes | no | implemented | `.venv/bin/python -m pytest services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_sqlite_persistence.py`; API responses include ordered catalog/optimizer/compatibility/performance/explainer/validator trace; browser E2E renders Agent orchestration panel |
| US-012 | Engineers can replay redacted agent trace events by session/build version and export support text | yes | yes | yes | no | implemented | Focused trace/API/persistence pytest passed; `pnpm check` passed with Next.js build and 61 API tests; harness story verify passed; Browser E2E rendered Trace replay with 6 events, copied support trace, no console issues, and no desktop/mobile horizontal overflow |
| US-013 | Product owner can run canonical local quality evals before changing core build behavior | yes | yes | no | no | implemented | `pnpm eval:run` passed 30/30 canonical scenarios; focused eval pytest passed; `pnpm check` passed with Next.js build and 65 API tests; harness story verify passed with `pnpm check && pnpm eval:run` |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.

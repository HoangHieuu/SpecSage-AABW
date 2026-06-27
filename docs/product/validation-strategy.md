# Validation Strategy

## Proof Ladder

| Layer | What it proves |
| --- | --- |
| Unit | Parsers, rules, scoring, optimizer helpers, DTO validation |
| Integration | FastAPI endpoints, database constraints, catalog sync, search, adapters |
| E2E | Browser path from Vietnamese intent to visible validated build |
| Platform | Deployment health, environment config, real provider connectivity |

Use the smallest proof that actually exercises the contract. Do not mark a
story implemented until its expected proof is recorded in Harness.

## First Canonical Scenarios

| ID | Persona | Input | Expected outcome |
| --- | --- | --- | --- |
| T-01 | First-time | Gaming 20M, Valorant + League at 1080p | Valid GPU-weighted build under budget |
| T-02 | Parent | Office/study 12M, quiet | iGPU or entry GPU, SSD 512GB+, approved |
| T-03 | Creator | Premiere/After Effects 35M | 32GB+ RAM, VRAM-aware GPU, NVMe storage |
| T-04 | Enthusiast | Cyberpunk 1440p High, 30M | Warns if FPS target is unlikely |
| T-05 | Upgrader | Existing i5-12400F/B660/RTX 3060, GPU budget 10M | Compatible upgrade options and PSU check |
| T-06 | Edge | Gaming 8M | Honest over-budget or nearest viable option |
| T-07 | Edge | Incompatible CPU/mainboard swap | Hard block with remediation |
| T-08 | Staff | T-01 through staff console | QR/share handoff when staff scope exists |
| T-09 | Commerce | Build with active combo promo | Promo savings shown when promo data exists |
| T-10 | AI use case | Local LLM 13B, 40M | VRAM guidance and 32GB+ RAM |

The first demo does not need all ten scenarios automated. It should automate at
least T-01, T-02, T-06, and T-07 before claiming the vertical slice is stable.

## Story Verification Commands

Early docs-only stories may verify with Harness queries. Implementation stories
should replace those with real checks, for example:

```bash
pnpm catalog:sync
pnpm check
pytest services/agent-api packages/rules-engine
pnpm test:e2e
scripts/bin/harness-cli story verify US-003
```

`US-003` is currently verified by `pnpm test:api`, which covers the pure rule
engine and `POST /builds/{build_id}/validate` integration contract.

`US-004` is currently verified by `pnpm check` plus Browser E2E against local
dev servers. Required rendered flows are one happy path from Vietnamese intent
to visible generated build and one over-budget path with an explicit gap.

`US-005` is verified by `pnpm check` plus Browser E2E against local dev
servers. Required rendered flows are one happy path from Vietnamese intent to a
visible cart-ready handoff and one over-budget path proving approval remains
blocked or the API returns 409.

`US-006` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit and integration proof must mock OpenRouter transport so normal validation
does not spend tokens. Browser proof should make one live intent analysis call
when `OPENROUTER_API_KEY` is configured, then confirm/generate to prove the
deterministic flow still works if the LLM panel is available or degraded.

`US-007` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers deterministic fit thresholds for gaming, creator, AI/local
LLM, and office builds. Integration proof checks the generate endpoint returns
`performance_profile`. Browser proof must show the generated build view renders
the `Workload fit` panel and must not rely on numeric FPS or benchmark claims.

`US-008` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers deterministic alternative generation from catalog SKUs,
changed slot deltas, compatibility revalidation, and absence of FPS claims.
Integration proof checks `GET /builds/{build_id}/alternatives` returns variants
for stored builds and 404s missing build IDs. Browser proof must show the
generated build view renders the `Alternatives` panel with concrete SKU deltas.

`US-009` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers converting a deterministic variant into a new versioned build
artifact. Integration proof checks
`POST /builds/{build_id}/alternatives/{variant_id}/apply` stores a new build,
preserves the original build, rejects missing variants, and allows approval when
the applied build remains eligible. Browser proof must apply a visible variant,
show the main build table updated, and approve the applied build through the
existing handoff gate.

`US-010` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit and integration proof cover SQLite round-trips for sessions, intent
revisions, builds, applied build versions, and idempotent cart handoffs by
re-instantiating FastAPI apps over the same DB file. Browser proof must show the
default persistent API still supports the generate -> alternatives -> apply ->
approve flow.

`US-011` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers the LangGraph orchestration service, expected agent sequence,
and deterministic build output preservation. Integration proof checks the
generate endpoint returns `orchestration_trace` and existing alternatives,
apply, approval, and SQLite persistence paths remain compatible. Browser proof
must show the generated build view renders the `Agent orchestration` panel.

`US-012` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers trace replay conversion and PII-sensitive payload redaction.
Integration proof checks build/session trace endpoints, build-version grouping,
support-export text, and SQLite restart survival. Browser proof must show the
generated build view renders `Trace replay` with six events and a support-export
copy action.

`US-013` is verified by `pnpm check`, `pnpm eval:run`, and Harness story
verification. Unit proof covers canonical scenario loading, minimum scenario
count, persona/budget coverage, and hallucinated-SKU failure detection.
Integration proof runs 30 scenarios through the deterministic parser and
LangGraph-wrapped generator against the local catalog snapshot. Browser proof is
not required because this story adds a local release gate, not a UI surface.

`US-014` is verified locally by `pnpm check`, `pnpm eval:run`, and Harness story
verification, and structurally by the checked-in GitHub Actions workflow. The
workflow installs pnpm, Node.js, Python, and Agent API dev dependencies before
running the same local gate. Browser proof is not required because the story has
no user-visible surface. Hosted CI pass evidence should be added after the
workflow runs on GitHub.

`US-015` is verified by focused feedback API tests, SQLite restart-survival
tests, `pnpm check`, `pnpm eval:run`, Harness story verification, and Browser
E2E. Integration proof must show that feedback links to the generated build,
catalog version, rules version, and review queue status, and that part-level
feedback rejects SKUs not present in the build. Browser proof must show the
post-generation feedback panel can submit and render saved feedback.

`US-016` is verified by `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`,
and Harness story verification. Unit proof covers category coverage counts and
blocking issues for missing required demo categories. Integration proof checks
`GET /catalog/health` exposes `demo_ready`, required categories, missing
categories, and per-category counts.

`US-017` is verified by `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`,
and Harness story verification. Unit proof covers recommended category counts,
thin-category warning issues, and missing categories remaining blocking.
Integration proof checks `GET /catalog/health` exposes recommended demo counts,
thin demo categories, and warning issues without making the current snapshot
not demo-ready.

## Never Claim Without Proof

- Do not claim real Phong Vu cart integration without a real Teko cart adapter.
- Do not claim full catalog coverage when using a curated snapshot.
- Do not claim compatibility correctness without rule tests.
- Do not claim production readiness without deployment and observability proof.
- Do not claim LLM output is authoritative for SKU, price, budget, stock,
  compatibility, approval, or cart readiness.
- Do not claim FPS, benchmark deltas, or game-specific performance numbers
  without a maintained benchmark source.

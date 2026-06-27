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

## Never Claim Without Proof

- Do not claim real Phong Vu cart integration without a real Teko cart adapter.
- Do not claim full catalog coverage when using a curated snapshot.
- Do not claim compatibility correctness without rule tests.
- Do not claim production readiness without deployment and observability proof.

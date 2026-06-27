# US-008 Build Alternatives and Iteration Controls

## Status

implemented

## Lane

normal

## Product Contract

After a build is generated, the user can inspect deterministic alternative
variants derived from the same local catalog snapshot and compatibility rules.
Alternatives must be grounded in real SKU IDs, show the exact slot-level deltas,
preserve catalog/rules versioning, and avoid LLM-invented parts, prices, or FPS
claims.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `techstack.md`

## Acceptance Criteria

- API exposes `GET /builds/{build_id}/alternatives`.
- Response contains deterministic variants for available catalog options, such
  as cheaper, balanced, max performance, RAM upgrade, or NVIDIA/AI-oriented
  alternatives when the snapshot supports them.
- Each variant includes total price, budget status, compatibility report,
  performance profile, explanation, warnings, and changed slots versus the base
  build.
- No alternative references a SKU absent from the local catalog snapshot.
- Frontend renders alternatives after build generation with price delta,
  compatibility status, changed parts, and rationale.
- Unit, integration, and browser proof cover the alternatives endpoint and UI.

## Design Notes

- Commands: no new runtime command.
- Queries: read existing stored build by `build_id`; derive variants from the
  current local catalog snapshot.
- API: `GET /builds/{build_id}/alternatives`.
- Tables: none; PostgreSQL/LangGraph checkpointing remains future Phase 5.
- Domain rules: deterministic candidate substitutions only; validate every
  variant with compatibility rules before returning it.
- UI surfaces: generated build panel adds an "Alternatives" section below the
  main parts table.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-008 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Alternative generation tests for SKU grounding, changed slots, and no FPS claims |
| Integration | `GET /builds/{build_id}/alternatives` returns validated variants and 404s missing builds |
| E2E | Browser flow displays alternatives after build generation |
| Platform | Not required; no external platform or provider added |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-008` |

## Harness Delta

No harness behavior change expected.

## Evidence

- `pnpm catalog:sync` regenerated `catalog_v2026_06_27_fixture` with 11 SKUs
  and 0 blocking validation issues.
- `pnpm check` passed with Next.js production build and 49 API tests.
- `scripts/bin/harness-cli story verify US-008` passed.
- Playwright browser flow opened the local app, analyzed intent through the
  OpenRouter advisor, confirmed intent, generated a valid build, and rendered
  `Alternatives` with four validated variants: RAM upgrade, larger SSD, NVIDIA
  GPU, and PSU headroom.
- Browser network proof showed `GET /builds/{build_id}/alternatives` returned
  HTTP 200 after generation.
- Direct Playwright extraction confirmed the alternatives panel contains no
  `fps` text.
- Mobile viewport check at 390px showed no page-wide horizontal overflow.
- Console had one non-blocking 404 for `/favicon.ico`.

# US-004 Build Generation Vertical Slice

## Status

implemented

## Lane

normal

## Product Contract

From a confirmed intent and local catalog snapshot, the system generates one
compatible PC build with a total price, compatibility report, grounded
Vietnamese explanations, and SKU links.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- Generation fills required slots for the selected use case.
- The optimizer respects `budget_max` or returns an explicit over-budget gap.
- Compatibility blocks prevent approval.
- Explanations reference frozen build facts and do not invent prices, specs, or
  FPS claims.
- Output includes build version, timestamp, intent snapshot, catalog version,
  rules version, total price, and SKU links.
- Browser E2E covers at least one happy path and one incompatible/over-budget
  path before demo-ready claims.

## Design Notes

- Commands: generate build, regenerate variant, approve build.
- Queries: read build artifact, read alternatives.
- API: `POST /sessions/{id}/generate`, `GET /builds/{id}`.
- Tables/files: first slice uses in-memory `BuildStore`, `BuildArtifact` schema,
  local catalog snapshot, and compatibility report schema.
- Domain rules: bounded iterations, default max 5.
- UI surfaces: customer web split view with conversation and build table.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | optimizer helper tests and explanation fact validation |
| Integration | generate endpoint with seeded catalog and rule fixtures |
| E2E | Vietnamese intent to visible validated build in browser |
| Platform | none until deployed |
| Release | story verify command once implemented |

## Harness Delta

Browser E2E proof is now required for demo-ready claims on this vertical slice.
The story verify command remains `pnpm check`; Browser proof is recorded as
manual rendered evidence because it depends on local dev servers.

## Evidence

- Added deterministic generator in
  `services/agent-api/src/pc_build_copilot/build_generator.py`.
- Added build artifact schema and in-memory build store in
  `services/agent-api/src/pc_build_copilot/build_models.py` and
  `services/agent-api/src/pc_build_copilot/build_store.py`.
- Added `POST /sessions/{build_session_id}/generate` and `GET /builds/{build_id}`.
- Web UI now renders build table, total price, budget status, catalog/rules
  versions, warnings, explanations, and Phong Vu SKU links.
- `.venv/bin/python -m pytest services/agent-api/tests` passed with 32 tests.
- `pnpm check` passed with Next.js production build and 32 API tests.
- Browser E2E passed:
  - Happy path: `PC gaming 25 triệu chơi Valorant và LMHT 144Hz` generated a
    valid 7-row build at 17.190.000 VND with 7 Phong Vu links.
  - Over-budget path: `PC gaming 8 triệu chơi Valorant` showed `Vượt ngân sách`
    and the explicit 9.190.000 VND budget gap.
  - Mobile viewport 390x844 rendered the generated build with no page-wide
    horizontal overflow; the SKU table scrolls inside its container.

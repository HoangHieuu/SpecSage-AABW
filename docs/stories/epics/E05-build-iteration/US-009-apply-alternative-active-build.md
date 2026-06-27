# US-009 Apply Alternative as Active Build

## Status

implemented

## Lane

normal

## Product Contract

After a user inspects deterministic alternatives for a generated build, the user
can apply one selected alternative as the active build. Applying a variant must
create a new generated build artifact version grounded in catalog SKUs, rerun
compatibility and performance fit checks, keep approval as a separate explicit
step, and preserve the original build artifact.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `techstack.md`

## Acceptance Criteria

- API exposes `POST /builds/{build_id}/alternatives/{variant_id}/apply`.
- Applying a known variant returns a new `BuildArtifact` with a new `build_id`
  and `build_version = base_build_version + 1`.
- The applied build uses only SKUs from the local catalog snapshot and reruns
  compatibility rules using the new build ID.
- The original build remains retrievable and unchanged.
- Applied builds are not auto-approved; existing approval and mock cart handoff
  gates still decide whether the new build can become cart-ready.
- Frontend renders an apply control for alternatives, updates the main build
  table after apply, clears any previous handoff, and reloads alternatives for
  the new active build.
- Unit, integration, and browser proof cover applying a variant and approving
  the applied build.

## Design Notes

- Commands: no new runtime command.
- Queries: read stored build by `build_id`, derive alternatives from the
  current local catalog snapshot, find the selected `variant_id`.
- API: `POST /builds/{build_id}/alternatives/{variant_id}/apply`.
- Tables: none; persisted iteration history, LangGraph checkpointing,
  PostgreSQL, and Redis remain future Phase 5 work.
- Domain rules: deterministic variant application only; every applied build is
  revalidated before it is returned or approved.
- UI surfaces: generated build panel adds an "Áp dụng biến thể" action on each
  alternative card and a version note after successful apply.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-009 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Apply helper creates a versioned artifact from a deterministic variant |
| Integration | Apply endpoint stores the new build, preserves the original build, rejects missing variants, and allows approval when eligible |
| E2E | Browser flow applies a visible variant, updates the build table, then approves the applied build |
| Platform | Not required; no external platform or provider added |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-009` |

## Harness Delta

No harness behavior change expected.

## Evidence

- `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py`
  passed with 19 tests covering apply helper, apply endpoint, missing variant,
  and approval after applying a variant.
- `pnpm check` passed with Next.js production build and 52 API tests.
- `scripts/bin/harness-cli story verify US-009` passed.
- Playwright browser flow opened the local app, parsed and confirmed a gaming
  intent, generated a valid build, applied the `Nâng RAM` alternative through
  `POST /builds/{build_id}/alternatives/{variant_id}/apply`, updated the active
  build to version 2 with total `17.890.000 ₫` and RAM SKU `240601032`, then
  approved that applied build through the existing mock cart handoff gate.
- Browser network proof showed apply, alternatives reload for the new build,
  and approval all returned HTTP 200.
- Mobile viewport check at 390px passed with document scroll width equal to
  client width after wrapping long generated IDs in build notes.
- Console had one non-blocking 404 for `/favicon.ico`.

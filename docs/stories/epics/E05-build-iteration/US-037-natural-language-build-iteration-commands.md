# US-037 Natural-Language Build Iteration Commands

## Status

implemented

## Lane

normal

## Product Contract

After a build is generated, a customer can submit a bounded Vietnamese
adjustment command and receive a new validated build version without restarting
the session. The command parser must be deterministic, reuse the existing
alternatives and approval gates, and record the command decision in the
optimizer trace.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0037-natural-language-iteration-before-pareto-variants.md`
- `docs/stories/epics/E05-build-iteration/US-008-build-alternatives-iteration-controls.md`
- `docs/stories/epics/E05-build-iteration/US-009-apply-alternative-active-build.md`
- `docs/stories/epics/E05-build-iteration/US-035-phase-5-multi-agent-optimizer-loop-foundation.md`

## Acceptance Criteria

- `POST /builds/{build_id}/iterate` accepts a Vietnamese command and returns a
  new active build version when a compatible in-budget variant matches.
- Supported commands include cheaper/under-budget, quieter, more FPS/NVIDIA,
  more SSD/storage, and more RAM.
- Unsupported commands fail deterministically instead of guessing a SKU.
- Commands reuse existing alternatives, ranking, compatibility, budget, and
  performance gates.
- A budget-saver command can consider downgrade variants without adding them to
  the public alternatives panel by default.
- The response includes parsed command metadata, selected alternative, applied
  build, and rejected candidate decisions.
- The applied build appends the command decision to `optimizer_trace` and adds
  an optimizer trace event for session replay.
- The web UI exposes a compact build-adjustment control after alternatives and
  clears cart/feedback state when a new iterated build is produced.

## Design Notes

- Commands: no new CLI command.
- Queries: existing catalog snapshot plus existing build alternatives query.
- API: adds `POST /builds/{build_id}/iterate`.
- Tables: no schema change; applied build artifacts are persisted as existing
  JSON payloads.
- Domain rules: deterministic parser only; no LLM SKU selection, no bypass of
  catalog, budget, compatibility, or benchmark gates.
- UI surfaces: generated build view adds `Điều chỉnh build` command controls.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-037 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Parser and iteration selector handle supported/unsupported commands and budget caps |
| Integration | API creates versioned iterated builds, persists traceable artifacts, and rejects impossible commands |
| E2E | Browser flow generates a Cyberpunk build, applies an SSD iteration command, and shows build v2 result |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-037` |

## Harness Delta

Adds `US-037` and decision `0037` to the Phase 5 build iteration contract.

## Evidence

- Focused parser/API/trace regression: `.venv/bin/python -m pytest services/agent-api/tests/test_build_iteration.py services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_trace_replay.py` passed with 44 tests.
- Release gate: `pnpm check` passed with the Next.js production build and 113 API tests.
- Eval gate: `pnpm eval:run` passed 30/30 canonical scenarios.
- Harness gate: `scripts/bin/harness-cli story verify US-037` passed.
- Browser proof: generated the Cyberpunk 2077 1440p Ultra build, applied `Tăng SSD nhưng giữ dưới 20 triệu`, rendered `Build v2`, selected `SSD rộng hơn`, updated total price to `19.790.000 ₫`, showed the 1TB Samsung SSD SKU, and kept the v2 optimizer event available behind support details; mobile-width iteration panel remained usable with no console errors.

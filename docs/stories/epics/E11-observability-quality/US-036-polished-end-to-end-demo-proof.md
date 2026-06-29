# US-036 Polished End-to-End Demo Proof

## Status

implemented

## Lane

normal

## Product Contract

The current hackathon demo should prove the core customer flow end to end in the
running app after `US-035`: Vietnamese intent, generated build, support-details
optimizer trace, benchmark-backed gaming warning, ranked alternative, applied build,
mock cart handoff, and feedback capture.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/stories/epics/E05-build-iteration/US-035-phase-5-multi-agent-optimizer-loop-foundation.md`
- `docs/stories/epics/E11-observability-quality/US-012-agent-trace-session-replay-foundation.md`
- `docs/stories/epics/E11-observability-quality/US-015-user-feedback-loop-foundation.md`

## Acceptance Criteria

- Browser flow starts from a Vietnamese Cyberpunk 2077 1440p Ultra 144Hz prompt.
- The generated build keeps optimizer loop trace available behind `Chi tiết hỗ trợ`.
- The generated build shows benchmark-backed warning provenance without adding
  unsupported numeric FPS claims to explanations.
- The optimizer loop shows the RTX 4060 GPU swap accepted for the matching
  benchmark target before the user sees the final generated build.
- The alternatives panel remains usable after generation, and the user can
  apply a valid remaining alternative, approve the resulting build, and see mock
  cart-ready handoff.
- Feedback can be submitted after the build is generated and saved with review
  queue state when negative.
- Desktop and mobile browser checks show no page-wide horizontal overflow.

## Design Notes

- Commands: no new runtime command.
- Queries: existing session/build/alternative/approval/feedback APIs.
- API: no new endpoint.
- Tables: no schema change.
- Domain rules: proof story only; no relaxation of SKU, budget,
  compatibility, benchmark, or approval gates.
- UI surfaces: generated build view must keep the customer path clean while
  making the optimizer loop reachable through support details for demo
  narration.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-036 --unit 0 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Not required; product behavior covered by underlying stories |
| Integration | Existing API flow still supports generate -> alternatives -> apply -> approve -> feedback |
| E2E | Browser desktop flow plus mobile overflow check |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-036` |

## Harness Delta

Adds an explicit demo-proof story after the Phase 5 optimizer-loop foundation.

## Evidence

- `.venv/bin/python -m pytest services/agent-api/tests/test_demo_e2e_flow.py` passed as API demo-flow proof.
- Playwright browser proof completed the Cyberpunk 2077 1440p Ultra 144Hz Vietnamese prompt, kept the optimizer loop trace behind support details, applied the SSD alternative, approved build v2, rendered mock cart handoff, and saved negative feedback with review queue state.
- Mobile Playwright viewport proof at 390x844 kept the page shell within the viewport; the existing parts table remains horizontally scrollable inside its container.
- `pnpm check` passed with Next.js build and 108 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-036` passed.

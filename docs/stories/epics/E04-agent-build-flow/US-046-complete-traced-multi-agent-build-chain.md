# US-046 Complete Traced Multi-Agent Build Chain

## Status

implemented

## Lane

normal

## Product Contract

The customer build path must expose the complete current multi-agent chain
described by the product architecture: intent, catalog, optimizer,
compatibility, performance, explainer, commerce, and validator. Each step is a
typed, deterministic LangGraph node that records traceable inputs, outputs,
tool-call labels, latency, and runtime version metadata without weakening SKU,
budget, compatibility, benchmark, approval, or mock-commerce gates.

This story completes the hackathon build-chain trace. It does not add real
checkout, autonomous payment, staff console workflows, external Langfuse
telemetry, Pydantic AI provider calls, or LangGraph checkpointing.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- Build generation orchestration starts with an explicit `intent` agent node
  that records schema-confirmed intent facts.
- The graph includes an explicit `commerce` agent node before the final
  validator.
- The commerce node reports mock-cart link-list readiness and explicitly marks
  real checkout as disabled.
- The generated `BuildArtifact.orchestration_trace` sequence is:
  `intent -> catalog -> optimizer -> compatibility -> performance -> explainer -> commerce -> validator`.
- Trace replay redacts the intent raw text and includes all eight events.
- The advanced web trace labels render the new intent and commerce agents.
- Existing deterministic build output, approval gates, alternatives,
  persistence, and eval scenarios remain unchanged.

## Design Notes

- Commands:
  - `.venv/bin/python -m pytest services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_trace_replay.py`
  - `pnpm check:web`
- API:
  - Existing `POST /sessions/{build_session_id}/generate`
  - Existing `GET /builds/{build_id}/trace`
  - Existing `GET /sessions/{build_session_id}/trace`
- Domain rules:
  - Intent node records already-confirmed intent; it does not reparse or call an
    LLM.
  - Commerce node reports mock handoff readiness only; real Teko checkout
    remains out of scope.
  - Validator remains the final approval gate.
- UI surfaces:
  - Advanced support trace labels for `Nhu cầu` and `Mua hàng`.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-046 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Orchestration tests prove eight-agent order, intent outputs, commerce outputs, and blocked validator behavior. |
| Integration | Trace replay tests prove eight replay events and raw intent redaction. |
| E2E | Not required for this foundation story; web trace labels are type/build checked. |
| Platform | Not required; no deployment, external observability, provider, auth, or real checkout change. |
| Release | `scripts/bin/harness-cli story verify US-046`. |

## Harness Delta

No Harness operating-model changes are required. This story adds a new
multi-agent-completion slice under the existing agent build flow epic.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_build_orchestrator.py services/agent-api/tests/test_trace_replay.py`
  passed with 8 focused orchestration/trace tests.
- `pnpm check:web` passed.

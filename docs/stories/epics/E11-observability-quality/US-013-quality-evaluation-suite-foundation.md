# US-013 Quality Evaluation Suite Foundation

## Status

implemented

## Lane

normal

## Product Contract

Product owners can run a local regression evaluation suite over canonical PC
build intents before changing parser, catalog, compatibility, performance, or
build-generation logic. The suite verifies that generated outputs remain
grounded in the local Phong Vu catalog snapshot and deterministic rule outputs.

This is a local foundation for SPEC `US-11.2`. It does not require Langfuse
credentials, GitHub Actions, production dashboards, or live Phong Vu/Teko APIs.

## Relevant Product Docs

- `SPEC.md` Phase 11 / `US-11.2 Quality Evaluation Suite`
- `techstack.md` Phase 11 eval-suite recommendation
- `docs/product/validation-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/decisions/0013-local-trace-replay-before-langfuse.md`

## Acceptance Criteria

- The repo contains at least 30 canonical evaluation scenarios across personas
  and budgets.
- A local command runs all scenarios and exits non-zero on critical regression.
- Automated checks cover compatibility pass/fail expectation, budget status,
  required slots, no hallucinated SKUs, no FPS claims, and expected use case.
- Each scenario produces explanation-quality rubric scores for clarity,
  grounding, and Vietnamese tone.
- `pnpm check` plus the eval command acts as the local release gate for this
  slice.

## Design Notes

- Commands:
  - `pnpm eval:run`
  - `.venv/bin/python -m pytest services/agent-api/tests/test_evaluation_suite.py`
- Queries:
  - `scripts/bin/harness-cli query tools --capability quality-evaluation --status present`
    returned no present external provider, so the foundation stays local.
- API:
  - None. This story adds local evaluation tooling, not a public endpoint.
- Tables:
  - None. Evaluation scenarios are checked-in JSON fixtures.
- Domain rules:
  - Evaluations run the deterministic parser and LangGraph-wrapped generator
    against the local catalog snapshot.
  - Numeric pass/fail criteria use artifact fields, not LLM judgment.
- UI surfaces:
  - None for this story.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-013 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Scenario loader validates 30+ scenarios and rubric scoring catches weak explanations |
| Integration | Eval runner generates builds from catalog snapshot and checks compatibility, budget, slots, and SKU grounding |
| E2E | Not required; no user-visible browser surface |
| Platform | Not required; CI provider and Langfuse datasets remain future work |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-013` |

## Harness Delta

Add `pnpm eval:run` as a local release-gate command for future behavior changes
that could affect core build quality.

## Evidence

- `scripts/bin/harness-cli query tools --capability quality-evaluation --status present`
  returned no present external quality-evaluation provider, so local checked-in
  evals were selected before Langfuse/GitHub Actions integration.
- `evals/canonical_build_scenarios.json` contains 30 canonical scenarios across
  first-time, parent, office, creator, AI, budget-edge, student, streamer,
  compact, brand-preference, and quiet-preference personas.
- `.venv/bin/python -m pytest services/agent-api/tests/test_evaluation_suite.py`
  passed with 4 tests.
- `pnpm eval:run` passed 30/30 scenarios against
  `catalog_v2026_06_27_fixture` and `compat_rules_v2026_06_27`.
- `pnpm check` passed with Next.js build and 65 API tests.
- `scripts/bin/harness-cli story verify US-013` passed with
  `pnpm check && pnpm eval:run`.

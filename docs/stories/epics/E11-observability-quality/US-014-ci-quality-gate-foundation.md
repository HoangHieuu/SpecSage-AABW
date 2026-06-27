# US-014 CI Quality Gate Foundation

## Status

implemented

## Lane

normal

## Product Contract

Repository changes to core PC Build Copilot behavior are checked by a hosted CI
quality gate that runs the same local release gate product owners use before
demo or release changes.

This is a foundation slice for SPEC `US-11.2`. It wires CI to the local
`pnpm check` and `pnpm eval:run` commands. It does not add production deployment,
Langfuse experiments, or external Phong Vu/Teko integration.

## Relevant Product Docs

- `SPEC.md` Phase 11 / `US-11.2 Quality Evaluation Suite`
- `techstack.md` Phase 11 local quality gate recommendation
- `tools.md` CI and validation helper guidance
- `docs/product/validation-strategy.md`
- `docs/decisions/0014-local-quality-evals-before-langfuse-experiments.md`
- `docs/decisions/0015-ci-quality-gate-for-local-evals.md`

## Acceptance Criteria

- GitHub Actions workflow exists for pull requests and pushes to `main`.
- CI installs the Node, pnpm, and Python runtimes needed by the monorepo.
- CI installs the Agent API in editable dev mode before running Python tests.
- CI runs `pnpm check`.
- CI runs `pnpm eval:run` so canonical regressions block the quality gate.
- No secrets are required for this workflow; OpenRouter and hosted observability
  integrations remain optional local/demo configuration.

## Design Notes

- Workflow:
  - `.github/workflows/ci.yml`
- Runtime pins:
  - Node.js 22, matching the local passing development runtime.
  - pnpm 11.7.0, matching `packageManager`.
  - Python 3.13, matching the current local `.venv` runtime and API support.
- The workflow creates `.venv` because root scripts intentionally call
  `.venv/bin/python`.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-014 --unit 0 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | Not required; this story wires existing commands |
| Integration | `pnpm check` and `pnpm eval:run` run successfully locally |
| E2E | Not required; no browser surface |
| Platform | GitHub Actions workflow is checked in with runtime setup and release gate steps |
| Release | `scripts/bin/harness-cli story verify US-014` |

## Harness Delta

Promote the local quality gate from `US-013` into repository CI while keeping
the same deterministic evaluation command.

## Evidence

- `pnpm check` passed with Next.js build and 70 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-014` passed with
  `pnpm check && pnpm eval:run`.

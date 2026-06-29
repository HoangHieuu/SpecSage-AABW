# US-028 Performance-Aware Alternative Ranking

## Status

implemented

## Lane

normal

## Product Contract

Generated alternatives are ranked with deterministic local scoring so users see
the most workload-relevant variant first. Ranking uses existing catalog,
budget, compatibility, performance profile, balance, workload, and warning
facts. It is advisory metadata only and does not replace approval gates or
autonomous optimization.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0029-deterministic-alternative-ranking-before-autonomous-optimization.md`
- `docs/stories/epics/E05-build-iteration/US-008-build-alternatives-iteration-controls.md`
- `docs/stories/epics/E05-build-iteration/US-009-apply-alternative-active-build.md`

## Acceptance Criteria

- Each alternative includes ranking metadata: `rank`, `score`, `priority`, and
  Vietnamese reasons.
- Alternatives are returned sorted by descending ranking score.
- Ranking reasons are grounded in deterministic facts such as budget,
  compatibility, balance, workload fit, warnings, and use case.
- AI/creator/streaming alternatives prioritize NVIDIA/CUDA variants when the
  profile indicates CUDA relevance.
- Ranking does not add new SKUs, skip compatibility checks, or auto-apply a
  variant.
- Frontend renders the rank/score and reasons in the existing alternatives
  panel.

## Design Notes

- Commands: no new runtime command.
- Queries: same `GET /builds/{build_id}/alternatives` path.
- API: `BuildAlternative.ranking`.
- Tables: no new persistence; ranking is recomputed from the current catalog
  snapshot and stored build.
- Domain rules: deterministic score only; no LLM ranking.
- UI surfaces: existing `Phương án thay thế` cards show priority rank and reasons.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-028 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Alternative generation returns sorted ranking metadata and AI CUDA ranking behavior |
| Integration | Alternatives endpoint returns rank/score/reasons for stored builds |
| E2E | Not required; UI type/build proof covers existing panel rendering |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-028` |

## Harness Delta

Adds `US-028` to E05 Build Iteration and decision `0029`.

## Evidence

- Focused build generation tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py`
- Frontend type/build check passed: `pnpm check:web`.
- `pnpm check` passed with Next.js production build and 98 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-028` passed.

# US-027 Office & General Use Adequacy

## Status

implemented

## Lane

normal

## Product Contract

Generated office and student builds explain general-use adequacy from catalog
facts, including iGPU versus discrete GPU suitability, quiet/power guidance, and
multi-monitor validation gaps. The system does not recommend monitor SKUs until
monitor catalog rows and output-port specs are curated.

Supersession note: `US-041` later adds optional monitor add-on recommendations
when a need mentions monitor/display or includes resolution plus refresh
targets. `US-027` still owns only office adequacy and output-port-gap warnings.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `docs/decisions/0028-office-monitor-guidance-before-monitor-sku-recommendations.md`

## Acceptance Criteria

- `BuildIntent` captures explicit monitor counts such as `2 màn hình`.
- Office/student profiles explain when a discrete GPU is required only because
  the selected CPU lacks iGPU.
- Office/student profiles explain when iGPU is suitable for general office use.
- Quiet office requests add qualitative power/noise guidance.
- Multi-monitor office requests warn with
  `OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN` until output-port specs are available.
- Generated builds do not add monitor SKUs in this slice.

## Design Notes

- Commands: no new runtime command.
- Queries: no external query; profile uses selected SKU facts and parsed
  intent only.
- API: `BuildIntent.monitor_count`; `BuildArtifact.performance_profile`.
- Tables: no new persisted table.
- Domain rules: deterministic office fit notes and warning codes, no LLM
  hardware claims.
- UI surfaces: existing workload fit panel shows the new notes, warnings, and
  evidence rows.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-027 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Parser captures monitor count; office profile covers iGPU/discrete GPU and quiet guidance |
| Integration | Build generation surfaces `OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN` in profile and artifact warnings |
| E2E | Not required; existing workload fit panel renders profile arrays generically |
| Platform | Not required |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-027` |

## Harness Delta

Adds `US-027` to E07 Performance Fit and decision `0028`.

## Evidence

- Focused parser/build tests passed:
  `.venv/bin/python -m pytest services/agent-api/tests/test_intent_parser.py services/agent-api/tests/test_build_generation.py`
- `pnpm check` passed with Next.js production build and 97 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-027` passed.

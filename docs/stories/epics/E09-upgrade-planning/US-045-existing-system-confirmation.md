# US-045 Existing System Confirmation Before Upgrade Planning

## Status

implemented

## Lane

normal

## Product Contract

Upgrade buyers must confirm the parsed existing-PC summary before the GPU
upgrade planner uses those facts for compatibility checks. The parser accepts
free-text current-PC descriptions, returns known CPU, mainboard, RAM, GPU, PSU,
case, and storage fields, marks missing fields as `unknown`, and lets the web
customer correct parsed values before requesting the catalog-grounded GPU plan.

This is a Phase 7.1 intake slice. It does not import prior Phong Vu orders,
authenticate customers, save upgrade profiles, or create multi-phase roadmaps.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- `POST /upgrade-plans/existing-system/parse` returns a typed parsed existing
  system summary from current-PC text.
- Parse responses include explicit `unknown_fields`, Vietnamese summary text,
  warnings, and next steps for confirmation.
- `POST /upgrade-plans/gpu` accepts confirmed existing-system field overrides
  and uses those values for deterministic PSU wattage, connector, and case
  clearance checks.
- The customer web app requires a parsed summary before planning a GPU upgrade.
- The web summary exposes editable CPU, mainboard, RAM, GPU, PSU wattage, PCIe
  8-pin count, case clearance, and storage fields.
- Editing the raw current-PC text clears stale parsed and planned results.

## Design Notes

- Commands:
  - `.venv/bin/python -m pytest services/agent-api/tests/test_upgrade_planner.py`
  - `pnpm check:web`
- API:
  - `POST /upgrade-plans/existing-system/parse`
  - `POST /upgrade-plans/gpu`
  - `ExistingSystemParseRequest`
  - `ExistingSystemParseResponse`
  - `ExistingSystemOverrides`
- Domain rules:
  - Confirmation overrides are still typed Pydantic fields.
  - Missing fields remain `unknown`; they are not guessed into pass/fail facts.
  - Confirmed numeric values feed the same deterministic PSU, connector, and
    clearance checks added in `US-044`.
- UI surfaces:
  - `Nâng cấp GPU` panel parse-and-confirm step.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-045 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Parser/planner tests prove confirmed fields override parsed free text and drive deterministic checks. |
| Integration | FastAPI endpoint test proves parse response shape and typed summary for the active API. |
| E2E | Not required for this foundation story; web confirmation panel is type/build checked. |
| Platform | Not required; no deployment, auth, external provider, or scheduler change. |
| Release | `scripts/bin/harness-cli story verify US-045`. |

## Harness Delta

No Harness operating-model changes are required. This story extends the Phase 7
upgrade-planning epic and validation matrix.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_upgrade_planner.py`
  passed with 8 focused parser/planner/API tests.
- `pnpm check:web` passed.
- `pnpm check` passed with Next.js build and 129 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-045` passed.

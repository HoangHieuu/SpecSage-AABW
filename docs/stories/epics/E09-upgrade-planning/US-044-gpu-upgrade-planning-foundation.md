# US-044 GPU Upgrade Planning Foundation

## Status

implemented

## Lane

normal

## Product Contract

Upgrade buyers can describe their current PC in Vietnamese and receive a first
GPU upgrade plan grounded in real active Phong Vu catalog SKUs. The plan parses
known existing specs, marks missing fields as `unknown`, recommends at most one
in-stock GPU within the stated upgrade budget, and deterministically checks
whether the current PSU wattage, PCIe power connectors, and case GPU clearance
are enough for that GPU.

This is a Phase 7 foundation slice. It does not import prior Phong Vu orders,
save upgrade roadmaps, authenticate users, integrate checkout, or generate
multi-phase upgrade plans.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- `POST /upgrade-plans/gpu` accepts current PC text and optional GPU upgrade
  budget.
- Existing system parsing extracts known CPU, GPU, RAM, PSU wattage, PSU PCIe
  8-pin count, case GPU clearance, and storage summary when present.
- Missing existing-system fields are returned in `unknown_fields`; they produce
  warnings instead of guessed compatibility facts.
- Recommended GPU SKUs must come from the active local catalog, be in stock,
  fit the provided upgrade budget, and rank above the parsed current GPU when
  the current GPU tier is known.
- The response includes deterministic PSU wattage, PCIe connector, and
  GPU/case clearance checks.
- Reuse decisions mark GPU as replace, PSU/case as reuse/replace/unknown based
  on checks, and RAM/storage as reuse or unknown within this foundation scope.
- The customer web app exposes a compact upgrade-planning panel without
  changing the existing full-build generation, approval, or mock shopping-list
  flow.

## Design Notes

- Commands:
  - `.venv/bin/python -m pytest services/agent-api/tests/test_upgrade_planner.py`
  - `pnpm check:web`
- API:
  - `POST /upgrade-plans/gpu`
  - `UpgradePlanRequest`
  - `UpgradePlanResponse`
- Domain rules:
  - GPU recommendations are catalog-only and in-stock.
  - PSU checks reuse the current deterministic headroom formula from the
    compatibility rule engine.
  - Case checks reuse the current GPU clearance warning threshold.
  - Unknown existing specs remain warnings, not inferred pass/fail outcomes.
- UI surfaces:
  - `Nâng cấp GPU` panel on the customer web app.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-044 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Parser and planner tests prove known existing specs, missing-field warnings, real catalog GPU selection, PSU pass/block checks, and case clearance checks. |
| Integration | FastAPI endpoint test proves `POST /upgrade-plans/gpu` returns the typed plan from the active catalog. |
| E2E | Not required for this foundation story; web panel is type/build checked. |
| Platform | Not required; no deployment, scheduler, auth, or external provider change. |
| Release | `scripts/bin/harness-cli story verify US-044`. |

## Harness Delta

No Harness operating-model changes are required. This story adds a new upgrade
planning epic and product/matrix documentation for Phase 7.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_upgrade_planner.py`
  passed with 6 focused parser/planner/API tests.
- `pnpm check:web` passed.
- `pnpm check` passed with Next.js build and 127 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-044` passed.

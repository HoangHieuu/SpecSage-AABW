# US-043 Optional Add-On Shopping-List Selection

## Status

implemented

## Lane

normal

## Product Contract

Customers can explicitly include recommended add-ons in the mock shopping list
after reviewing a generated build. Core PC approval remains unchanged:
`selected_skus`, compatibility approval, and PC total still cover only selected
PC parts, while chosen add-ons appear as optional shopping-list links with a
separate add-on total and combined shopping-list total.

## Relevant Product Docs

- `docs/product/technical-architecture.md`
- `docs/product/data-strategy.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E04-agent-build-flow/US-041-monitor-add-on-recommendation-foundation.md`
- `docs/stories/epics/E04-agent-build-flow/US-042-cooler-add-on-recommendation-foundation.md`

## Acceptance Criteria

- `POST /builds/{build_id}/approve` accepts optional
  `selected_addon_skus`.
- Selected add-on SKUs must reference `BuildArtifact.recommended_addons` for
  that build; duplicates or arbitrary SKUs are rejected.
- `BuildApproval.selected_skus` and `BuildApproval.total_price_vnd` remain core
  PC-only.
- `CartReadyHandoff` exposes add-on total, combined shopping-list total, and
  selected add-on records.
- The mock cart payload includes selected add-on links only when the user
  chooses them.
- The customer UI lets users select add-ons before creating the shopping list
  and shows the separated PC/add-on/list totals after handoff.

## Design Notes

- Commands:
  - `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  - `pnpm check:web`
- Domain rules:
  - Add-on selection is explicit and user-controlled.
  - Add-ons do not make a blocked or over-budget PC approvable.
  - Add-ons do not alter the compatibility report or approval SKU map.
- API:
  - `BuildApprovalRequest.selected_addon_skus`
  - `CartReadyHandoff.selected_addons`
  - `CartReadyHandoff.add_on_total_price_vnd`
  - `CartReadyHandoff.shopping_list_total_price_vnd`
- UI surfaces:
  - Add-on checkbox in `Gợi ý thêm`
  - Cart-ready totals and add-on summary

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-043 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Build/API tests prove add-on inclusion, invalid-SKU rejection, and approval core SKU exclusion. |
| Integration | Focused build/catalog/API tests and `pnpm check:web` pass with the new request and response shape. |
| E2E | Not required for this foundation story; browser smoke is optional. |
| Platform | Not required; no real checkout, deployment, scheduler, or external provider change. |
| Release | `scripts/bin/harness-cli story verify US-043`. |

## Harness Delta

No Harness operating-model changes are required. This story updates the
commerce handoff contract, product docs, and test matrix.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py`
  passed with 41 focused build/API tests.
- `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  passed with 63 focused build/catalog/API tests.
- `pnpm check:web` passed.

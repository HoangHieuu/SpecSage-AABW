# US-042 Cooler Add-On Recommendation Foundation

## Status

implemented

## Lane

normal

## Product Contract

Generated builds may include an optional CPU cooler recommendation when the
confirmed need asks for quiet operation or mentions a cooler. The
recommendation must be a real Phong Vu SKU from the active local catalog and
must pass deterministic CPU socket, TDP, and case-height fit checks before it
is shown.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-040-optional-cooler-monitor-catalog-curation.md`

## Acceptance Criteria

- Cooler recommendations use only in-stock `cooler` catalog rows.
- Cooler fit checks use CPU socket, CPU TDP, cooler TDP rating, cooler height,
  and selected case cooler-height clearance.
- Quiet office needs recommend a compatible cooler with additional TDP
  headroom.
- Recommended cooler SKUs are not included in `BuildArtifact.items`,
  `total_price_vnd`, `mock_cart_payload`, or approval selected SKUs.
- The customer UI shows cooler add-ons in the same compact optional section as
  monitor add-ons.
- Advanced UI mode can show deterministic fit notes for socket, TDP, and
  clearance.

## Design Notes

- Commands:
  - `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  - `pnpm check:web`
- Domain rules:
  - Cooler add-ons are optional buyer suggestions, not required build slots.
  - AIO requests prefer curated AIO rows when compatible.
  - Quiet requests prefer compatible air coolers with more TDP headroom before
    price.
- API:
  - `BuildArtifact.recommended_addons`
  - `BuildRecommendedAddOn.kind = cooler`
- UI surfaces:
  - `Gợi ý thêm` section after selected PC parts.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-042 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Build generation test proves cooler add-on selection, fit notes, and exclusion from items, total, and mock cart. |
| Integration | Focused build/catalog/API tests and `pnpm check:web` pass with the new artifact field and UI section. |
| E2E | Not required for this foundation story; UI is type/build checked. |
| Platform | Not required; no deployment, scheduler, or external provider change. |
| Release | `scripts/bin/harness-cli story verify US-042`. |

## Harness Delta

No Harness operating-model changes are required. This story updates the
generated artifact contract, product docs, and test matrix.

## Evidence

Validation passed:

- `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py`
  passed with 39 focused build tests.
- `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  passed with 61 focused build/catalog/API tests.
- `pnpm check:web` passed.

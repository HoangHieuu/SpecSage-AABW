# US-041 Monitor Add-On Recommendation Foundation

## Status

implemented

## Lane

normal

## Product Contract

Generated builds may include an optional monitor recommendation when the
confirmed need mentions a monitor or includes a display resolution plus refresh
target. The recommendation must be a real Phong Vu SKU from the active local
catalog and must not change the PC build total, approval gate, or primary mock
cart payload.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E02-catalog-grounding/US-040-optional-cooler-monitor-catalog-curation.md`

## Acceptance Criteria

- Monitor recommendations use only in-stock `monitor` catalog rows.
- A 1440p/144Hz gaming need recommends the curated 2K high-refresh monitor.
- Recommendations are returned under `BuildArtifact.recommended_addons`, not
  `BuildArtifact.items`.
- Recommended monitor SKUs are not included in `total_price_vnd`,
  `mock_cart_payload`, or approval selected SKUs.
- The customer UI shows monitor add-ons in a compact optional section.
- Advanced UI mode can show fit notes without exposing dev-only trace language.

## Design Notes

- Commands:
  - `.venv/bin/python -m pytest services/agent-api/tests/test_build_generation.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_catalog_api.py`
  - `pnpm check:web`
- Domain rules:
  - Monitor add-ons are conservative: explicit monitor request, monitor count,
    or resolution plus refresh target.
  - Ranking prefers matching resolution first, then meeting refresh target,
    then lower price.
  - Add-ons are optional buyer suggestions, not required build slots.
- API:
  - `BuildArtifact.recommended_addons`
  - `BuildRecommendedAddOn.kind = monitor`
- UI surfaces:
  - `Gợi ý thêm` section after selected PC parts.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-041 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Build generation test proves monitor add-on SKU selection and confirms it is excluded from items, total, and mock cart. |
| Integration | Focused build/catalog/API tests and `pnpm check:web` pass with the new artifact field and UI section. |
| E2E | Not required for this foundation story; UI is type/build checked. |
| Platform | Not required; no deployment, scheduler, or external provider change. |
| Release | `scripts/bin/harness-cli story verify US-041`. |

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

# US-051 Commerce Dashboard Product Media Polish

## Status

implemented

## Lane

normal

## Product Contract

The customer-facing commerce dashboard should look and behave like a retail
product surface while preserving the current mock-commerce boundary. Generated
build rows and optional add-ons should show product imagery and storefront
metadata when the grounded catalog snapshot provides it, with graceful fallbacks
for older curated rows that do not have image URLs.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`

## Acceptance Criteria

- Generated build items expose catalog `image_url`, `warranty_text`, and stock
  metadata through the existing build artifact API.
- Recommended monitor/cooler add-ons expose the same media and storefront
  metadata.
- The web build table renders product thumbnails when available and keeps a
  polished slot fallback when not available.
- Customer-visible copy remains Vietnamese-first and does not imply real
  checkout integration.
- Desktop and mobile browser QA show no page-wide horizontal overflow.

## Design Notes

- Commands: keep existing `pnpm check` release gate.
- Queries: no new query surface.
- API: additive fields only on existing response models.
- Tables: no schema changes.
- Domain rules: no change to compatibility, approval, cart, or checkout gates.
- UI surfaces: main build table, optional add-on cards, and storefront metadata
  tags.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-051 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused API/model assertions for media metadata in generated builds and add-ons. |
| Integration | `pnpm check` passes. |
| E2E | Browser flow generates a build and confirms thumbnails/fallbacks render without overflow. |
| Platform | Not required; no deploy-specific runtime behavior is introduced. |
| Release | Optional Vercel deploy after local proof. |

## Harness Delta

None expected.

## Evidence

- API model propagation adds `image_url`, `brand`, `warranty_text`,
  `stock_status`, and `stock_quantity` to generated build rows and optional
  monitor/cooler add-ons.
- Web table/add-on cards render catalog images when present and polished slot
  fallbacks when older curated rows have no `image_url`.
- `services/agent-api/tests/test_build_generation.py` asserts metadata
  propagation for core build rows and add-ons.
- `pnpm check` passed with the Next.js production build and 147 API tests.
- Browser QA generated a build locally, confirmed brand/warranty/stock tags in
  the build table and add-on panel, and inspected a temporary Playwright
  screenshot; core selected SKUs currently use fallback thumbnails because the
  committed catalog snapshot has `image_url: null` for those rows.

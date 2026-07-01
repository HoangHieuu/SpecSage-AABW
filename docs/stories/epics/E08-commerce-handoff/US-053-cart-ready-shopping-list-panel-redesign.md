# US-053 Cart-Ready Shopping-List Panel Redesign

## Status

implemented

## Lane

normal

## Product Contract

The cart-ready shopping-list handoff should remain a mock commerce handoff with
real Phong Vu product links, while the customer-facing panel renders as a
readable receipt-style surface on desktop and mobile. Totals, product links, and
warnings must not collapse into one-character columns in the narrow cart rail.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/stories/epics/E08-commerce-handoff/US-043-optional-add-on-shopping-list-selection.md`
- `docs/stories/epics/E08-commerce-handoff/US-051-commerce-dashboard-product-media-polish.md`

## Acceptance Criteria

- Cart-ready totals render as a readable receipt summary instead of four narrow
  metric tiles.
- Product links render as clean numbered rows with wrapped product names.
- Warnings remain visible but visually secondary to the product list.
- Customer-visible copy stays Vietnamese-first and does not imply real checkout
  integration.
- Desktop and mobile browser QA show no page-wide horizontal overflow.

## Design Notes

- Commands: `pnpm check:web`
- Queries: no new query surface.
- API: no response-shape changes.
- Tables: no schema changes.
- Domain rules: no changes to approval, add-on selection, or mock cart gates.
- UI surfaces: `CartReadyPanel` in the right cart rail.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-053 --unit 0 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Not required; presentational-only UI change. |
| Integration | `pnpm check:web` passes. |
| E2E | Browser or Playwright QA creates a cart-ready handoff and verifies the redesigned panel on desktop and mobile. |
| Platform | Not required; no deploy-specific runtime behavior is introduced. |
| Release | Optional Vercel deploy after local proof. |

## Harness Delta

None expected.

## Evidence

- Replaced the cart-ready metric tiles with a receipt-style summary so totals
  stay readable in the narrow cart rail.
- Rendered product links as numbered rows with normal wrapped product names
  instead of oversized red link text.
- Kept the Phong Vu link-list disclaimer and mock-cart warning visible without
  implying real checkout integration.
- `pnpm check:web` passed.
- Browser QA generated the Cyberpunk demo build, approved the mock cart handoff,
  and verified the redesigned panel on 1280px desktop and 390px mobile:
  4 receipt rows, 7 product rows, 3 warning rows, no old metric tile grid, no
  framework overlay, no console errors, and no horizontal overflow.

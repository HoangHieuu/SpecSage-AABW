# US-005 Review Approval And Mock Cart-Ready Handoff

## Status

implemented

## Lane

normal

## Product Contract

Users can review an approvable generated build, approve it, and receive a mock
cart-ready handoff with real Phong Vu SKU links. Builds that are blocked or
over budget cannot be approved.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- Session states include `reviewing`, `approved`, and `cart_ready`.
- Only generated builds with `can_approve=true` can produce a cart-ready
  handoff.
- Over-budget builds return a 409 approval error and do not produce cart
  payloads.
- Blocked compatibility builds return a 409 approval error and do not produce
  cart payloads.
- The cart-ready response includes approval id, handoff id, selected SKUs,
  total price, catalog version, rules version, and the mock Phong Vu link list.
- The customer UI exposes a review/approval action and a cart-ready panel with
  SKU links and a mock-cart disclaimer.

## Design Notes

- Commands: approve build.
- Queries: read generated build.
- API: `POST /builds/{id}/approve`.
- Tables/files: first slice extends in-memory `BuildStore`; no database,
  checkout, auth, or payment behavior.
- Domain rules: approval requires generated status, compatibility approval,
  and within-budget status.
- UI surfaces: customer web build panel adds review state and cart-ready
  handoff panel.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-005 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | approval helper rejects blocked and over-budget builds |
| Integration | FastAPI approve endpoint creates handoff and updates session state |
| E2E | browser flow from Vietnamese intent to cart-ready panel |
| Platform | none until deployed or real commerce adapter exists |
| Release | `pnpm check` |

## Harness Delta

This story creates the first commerce-handoff packet while keeping real checkout
and provider APIs explicitly out of scope.

## Evidence

- `.venv/bin/python -m pytest services/agent-api/tests` passed with 36 tests.
- `pnpm check:web` passed with TypeScript and Next.js production build.
- `pnpm check` passed with Next.js production build and 36 API tests.
- Browser E2E passed:
  - Happy path: `PC gaming 25 triệu chơi Valorant và LMHT 144Hz` generated a
    valid 7-row build, approved it, and rendered a cart-ready handoff with 7
    Phong Vu SKU links, approval id, handoff id, and mock-cart disclaimer.
  - Over-budget path: `PC gaming 8 triệu chơi Valorant` rendered `Vượt ngân sách`
    with a 9.190.000 VND gap, kept the approve button disabled, and did not
    render a cart-ready panel.
  - Browser console had no warning/error logs during the verified flows.

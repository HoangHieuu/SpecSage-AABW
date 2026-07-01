# US-052 Header Logo and Dead Navigation Cleanup

## Status

implemented

## Lane

normal

## Product Contract

The production header should only expose working controls. The brand mark must
render as a clean SpecSage logo, and the top navigation must not show redundant
anchors for sections that are not active product surfaces in the current
single-page copilot.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`

## Acceptance Criteria

- The SpecSage logo mark renders cleanly without clipped or distorted paths.
- The broken top navigation links are removed from the header.
- Header spacing remains stable on desktop and mobile.
- Status controls such as location, LLM state, notifications, and account remain
  visible and usable.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript and Next.js checks pass. |
| Integration | `pnpm check:web` passes. |
| E2E | Browser QA confirms the header no longer shows the removed nav items and the logo renders cleanly. |
| Platform | Production deploy smoke returns HTTP 200 after release. |

## Evidence

- Removed the non-functional top navigation anchors from the active copilot
  header.
- Replaced the distorted logo mark with an explicit SVG mark that renders at a
  stable 42px square in the header.
- Raised the desktop layout breakpoint so a 1280px viewport no longer creates a
  page-wide horizontal scrollbar.
- `pnpm check:web` passed.
- In-app Browser QA verified the desktop header; Playwright fallback verified
  1280px desktop and 390px mobile screenshots without the removed nav items.

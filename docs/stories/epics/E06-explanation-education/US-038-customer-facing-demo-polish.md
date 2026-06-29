# US-038 Customer-Facing Demo Polish

## Status

implemented

## Lane

normal

## Product Contract

The customer web flow should feel like a retail PC advisor by default, not an
engineering console. Customer-facing screens should emphasize budget, fit,
warnings, alternatives, and purchase readiness in Vietnamese. Technical proof
such as trace replay, optimizer decisions, orchestration steps, IDs, and
support exports must remain available only behind the advanced/support details
path.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/stories/epics/E05-build-iteration/US-035-phase-5-multi-agent-optimizer-loop-foundation.md`
- `docs/stories/epics/E11-observability-quality/US-036-polished-end-to-end-demo-proof.md`
- `docs/stories/epics/E05-build-iteration/US-037-natural-language-build-iteration-commands.md`

## Acceptance Criteria

- Default Basic mode uses buyer-facing copy for the main flow: no visible
  `Trace replay`, `optimizer`, `LangGraph`, `deterministic`, `mock cart`,
  `review queue`, or `LLM` terminology in the first customer decision path.
- Generated builds show a compact customer decision summary that answers:
  total price, workload fit, budget status, and the next action.
- Advanced/support details remain reachable and still expose orchestration,
  optimizer-loop, and trace replay proof for technical review.
- Feedback and cart/handoff copy are phrased as customer actions, not internal
  demo/review terminology.
- Desktop and mobile browser checks show the polished flow without framework
  overlays, relevant console errors, or page-wide horizontal overflow.

## Design Notes

- Commands: no API contract change expected.
- Queries: no data model change expected.
- API: existing build, alternatives, iteration, approval, feedback, and trace
  endpoints remain unchanged.
- Tables: none.
- Domain rules: unchanged; numeric claims still come only from build artifact
  fields.
- UI surfaces: `apps/web/components/build-copilot-client.tsx` and
  `apps/web/app/globals.css`.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-038 --unit 0 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | TypeScript typecheck through `pnpm check:web`. |
| Integration | Next.js production build through `pnpm check:web`. |
| E2E | Playwright browser check on the local web app proving Basic mode copy, advanced support details, and responsive layout. |
| Platform | Not required. |
| Release | `scripts/bin/harness-cli story verify US-038`. |

## Harness Delta

Adds a new normal story after the natural-language iteration slice so future UI
polish remains tracked as product behavior, not ad hoc styling.

## Evidence

- `pnpm check:web` passed.
- `scripts/bin/harness-cli story verify US-038` passed.
- Browser QA at `http://localhost:3000/` generated the default Cyberpunk build,
  confirmed Basic mode renders the customer decision summary, found no customer
  path instances of `Trace replay`, `LangGraph`, `deterministic`, `mock cart`,
  `review queue`, or `LLM`, opened advanced support details, and confirmed
  trace replay, orchestration steps, and optimizer proof are still reachable.
- Desktop viewport `1280x720`: `scrollWidth` 1265, `innerWidth` 1280, no
  relevant console warnings/errors, screenshot
  `/tmp/specsage-us038-desktop.png`.
- Mobile viewport `390x844`: `scrollWidth` 375, `innerWidth` 390, no
  horizontal overflow, screenshot `/tmp/specsage-us038-mobile.png`.

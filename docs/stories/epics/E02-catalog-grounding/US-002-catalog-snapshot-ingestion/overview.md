# Overview

## Current Behavior

Before `US-002`, the app could create build sessions and parse Vietnamese
intent, but it had no catalog source of truth. No API route could prove that a
recommended SKU existed in a local snapshot.

## Target Behavior

The repo can build a deterministic local catalog snapshot from a saved Phong Vu
public payload fixture, merge curated compatibility specs, validate the result,
and query the resulting SKUs through the agent API.

## Affected Users

- Customer: later recommendations can reference real SKU IDs and product links.
- Agent/API caller: can filter local catalog candidates before compatibility
  and optimization.
- Developer: can refresh the deterministic snapshot with `pnpm catalog:sync`.

## Affected Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Live public-site crawling.
- Private Phong Vu/Teko API access.
- Full catalog coverage.
- Checkout integration.
- Staff/admin override review UI.

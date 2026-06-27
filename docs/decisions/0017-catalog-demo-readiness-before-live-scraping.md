# 0017 Catalog Demo Readiness Before Live Scraping

## Status

Accepted

## Context

The local catalog snapshot is the source of truth for the hackathon demo. The
project already validates per-SKU compatibility specs, but a snapshot could
still pass those checks while missing an entire required full-build category.
That failure would show up later during build generation or evals instead of at
catalog health time.

## Decision

Extend the local catalog validation report with demo-readiness coverage fields:

- Per-category SKU counts
- Required demo categories
- Missing required demo categories
- `demo_ready`

The required demo categories for the first full-build flow are CPU, mainboard,
RAM, storage, VGA, PSU, and case. Missing any of those categories is a blocking
catalog validation issue.

This does not add live scraping, Firecrawl, Phong Vu/Teko private APIs,
Typesense, PostgreSQL, or admin catalog editing.

## Consequences

- `GET /catalog/health` can reveal category coverage problems before a build
  generation or evaluation run fails.
- `pnpm catalog:sync` embeds demo-readiness proof into
  `catalog_snapshot.json`.
- Cooler and monitor can remain absent for the first demo because they are not
  required by the current generator contract.

## Follow-Ups

- Expand from minimum category coverage to broader curated SKU coverage after
  the demo flow needs more price bands or compatibility variants.
- Add live category scraping only when API/tool credentials or a saved public
  payload for each category exists.

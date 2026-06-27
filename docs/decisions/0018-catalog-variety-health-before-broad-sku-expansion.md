# 0018 Catalog Variety Health Before Broad SKU Expansion

## Status

Accepted

## Context

`US-016` made missing required full-build categories blocking at catalog health
time. The current local snapshot is demo-ready, but it still has thin choice in
some required categories. Expanding to a larger catalog is useful, but broad
SKU ingestion should not be rushed without source coverage, enrichment, and
validation proof.

## Decision

Extend the local catalog validation report with non-blocking demo variety
health:

- Recommended demo SKU counts per required full-build category
- Thin demo categories
- Warning issues for present-but-thin categories

The first recommended minimum is two SKUs for each required full-build
category: CPU, mainboard, RAM, storage, VGA, PSU, and case. Missing categories
remain blocking, while categories with one SKU remain demo-ready but produce
warnings.

This does not add live scraping, Firecrawl, Phong Vu/Teko private APIs,
Typesense, PostgreSQL, or admin catalog editing.

## Consequences

- `GET /catalog/health` can show whether the demo is runnable and whether the
  local catalog has enough fallback choice.
- `pnpm catalog:sync` embeds thin-coverage warnings into
  `catalog_snapshot.json`.
- Future SKU expansion can target the thinnest required categories first.

## Follow-Ups

- Curate additional CPU, mainboard, and case SKUs from saved public Phong Vu
  payloads before claiming broader catalog coverage.
- Add live category scraping only when tool credentials or saved payloads exist
  for each targeted category.

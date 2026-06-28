# 0023 Curated Catalog Subsets Before Source Enablement

## Status

Accepted

## Context

`US-020` made broad public Phong Vu category captures visible as staged
sources, but enabling an entire staged page would add many SKUs whose
compatibility-critical fields have not been reviewed. `US-017` also showed that
the active demo catalog was still thin in CPU, mainboard, and case coverage.

## Decision

Add an `include_skus` field to catalog source manifest entries. An enabled
source may point at an existing staged public category fixture but promote only
the listed, reviewed SKUs into `catalog:sync`.

The full category fixtures remain staged with `enabled=false` for coverage
reporting. Promoted SKUs must have required compatibility specs in
`sku_specs_overrides.json` before they are recommendation-eligible.

The first promoted subset is:

- CPU `251204776` from the staged CPU category page.
- Mainboard `241105117` from the staged mainboard category page.
- Case `260302526` from the staged case category page.

## Consequences

- The active catalog can grow from staged public captures without weakening the
  deterministic compatibility contract.
- `pnpm catalog:source-report` counts curated enabled candidates separately
  from broad staged candidates.
- `pnpm catalog:sync` fails if an `include_skus` value is missing from its
  referenced source, preventing stale or mistyped promotions.
- The active snapshot reaches two SKUs in every required full-build category
  while the broader 370-candidate staged corpus remains non-eligible.

## Follow-Ups

- Continue promoting small reviewed subsets by category instead of enabling
  full staged sources.
- Add product-detail capture when listing pages do not expose enough evidence
  for compatibility-critical overrides.
- Keep source URLs with curated overrides so future audits can re-check facts.

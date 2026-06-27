# 0010 Local Catalog Mirror Before Private API

Date: 2026-06-27

## Status

Accepted

## Context

The project needs real Phong Vu SKUs, prices, stock signals, and product links,
but the team does not have internal Phong Vu/Teko database or API access yet.

`Data.md` shows that public pages expose enough product data for a credible
hackathon catalog snapshot, while private cart, inventory, and promotion APIs
remain future integration work.

## Decision

Use a local catalog mirror as the initial source of truth:

```text
public Phong Vu pages -> catalog sync -> local snapshot -> agents
```

The hackathon build may use product links and mock cart payloads. It must not
claim live checkout integration until a real Teko cart adapter exists.

## Consequences

Positive:

- The first demo is self-contained and reproducible.
- Recommendations can still point to real products.
- A future `CatalogAdapter` or `CommerceAdapter` can swap in approved APIs.

Tradeoffs:

- Snapshot prices and stock may drift.
- Compatibility-critical specs require enrichment and confidence labeling.
- Live promo and showroom inventory behavior remains out of scope until real
  feeds are available.

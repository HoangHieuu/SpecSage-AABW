# Data Strategy

## Source Of Truth

The hackathon build does not depend on Phong Vu internal database access.

Use a local catalog mirror:

```text
Phong Vu public pages -> catalog sync -> local catalog snapshot -> agents
```

The Catalog Agent queries the local snapshot, not live Phong Vu production
systems. This keeps demos reproducible, avoids brittle live dependencies, and
still grounds recommendations in real public products.

## Public Data Available

Phong Vu product/category pages expose public commerce data through their
frontend payloads, including SKU IDs, names, pricing, stock quantity signals,
brand/category fields, product URLs, highlight specs, and product descriptions.

Harder fields such as socket, TDP, GPU length, PSU connectors, and showroom
stock need enrichment before they can power hard compatibility rules.

## Four-Layer Catalog Plan

| Layer | Purpose | First implementation target |
| --- | --- | --- |
| Category scrape | Bulk SKU discovery from public category pages | CPU, mainboard, RAM, VGA, SSD, PSU, case, cooler, monitor |
| Product detail pass | Richer descriptions, warranty, promo context | Top N products per category |
| Spec enrichment | Convert names/highlights/descriptions into structured fields | Regex plus curated override JSON |
| Seed builds | Reference builds from Phong Vu articles | 10-20 demo-calibration builds |

For the first demo, curate approximately 120-150 SKUs across 15M-40M VND build
bands instead of trying to mirror the full catalog.

## Minimal SKU Contract

```json
{
  "sku": "260508255",
  "name": "VGA ASUS RX 7600 8GB",
  "category": "vga",
  "price_vnd": 6990000,
  "stock_quantity": 1000,
  "url": "https://phongvu.vn/example--s260508255",
  "brand": "asus",
  "specs": {
    "vram_gb": 8,
    "memory_type": "GDDR6",
    "pcie": "4.0",
    "tdp_w": 165,
    "length_mm": null
  },
  "specs_confidence": "partial",
  "catalog_snapshot_at": "2026-06-27T00:00:00Z"
}
```

`specs_confidence` must be one of `verified`, `partial`, or `inferred`. UI and
explanations must disclose partial/inferred fields when the value affects a
recommendation or warning.

## Trust Contract

Customer-facing output must include:

- Catalog snapshot date.
- Product link for each SKU.
- Price-change disclaimer.
- Compatibility warnings when data is incomplete.
- Fallback path to human consultation.

The system may say data is missing. It must not invent prices, stock, specs, or
FPS numbers.

## Current Implementation

`US-002` implements the first deterministic catalog path:

- Saved public-payload fixture:
  `services/agent-api/fixtures/phongvu-category-components.html`
- Auditable curated compatibility specs:
  `services/agent-api/catalog/sku_specs_overrides.json`
- Generated local snapshot:
  `services/agent-api/catalog/catalog_snapshot.json`
- Sync command:
  `pnpm catalog:sync`
- Read-only API:
  `GET /catalog/health` and `GET /catalog/skus`

The current snapshot is intentionally small: CPU, mainboard, RAM, SSD, GPU, PSU,
and case SKUs for the next compatibility slice. It is not full catalog coverage
and does not claim live price or stock freshness.

## Commerce Adapter Boundary

Hackathon:

- Mock cart payload with real SKU IDs and product links.
- No autonomous checkout.
- No claim that Phong Vu cart integration is live unless a real Teko API is
  integrated.

Current implementation:

- `US-005` approves only generated builds that are compatible and within budget.
- `POST /builds/{build_id}/approve` returns a mock cart-ready handoff with the
  selected SKU map, approval id, handoff id, total snapshot price, and Phong Vu
  product links.
- Over-budget and blocked builds return 409 instead of creating a cart payload.
- `US-010` persists sessions, intent revisions, build artifacts, applied build
  versions, and mock cart handoffs in local SQLite so the demo survives an Agent
  API process restart.

Pilot and production:

- Swap the scraper/local mirror behind a `CommerceAdapter` and `CatalogAdapter`
  interface.
- Preserve build reproducibility through catalog and rules versions.
- Replace local SQLite with PostgreSQL/Redis when multi-user account history,
  LangGraph checkpointing, analytics, or production deployment becomes the
  selected story.

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
FPS numbers. Numeric FPS may appear only from a maintained benchmark row with a
source label and URL.

## Current Implementation

`US-002` implements the first deterministic catalog path:

- Saved public-payload fixture:
  `services/agent-api/fixtures/phongvu-category-components.html`
- Auditable curated compatibility specs:
  `services/agent-api/catalog/sku_specs_overrides.json`
- Generated local snapshot:
  `services/agent-api/catalog/catalog_snapshot.json`
- Source manifest:
  `services/agent-api/catalog/catalog_sources.json`
- Capture command:
  `pnpm catalog:capture`
- Source coverage report:
  `pnpm catalog:source-report`
- Sync command:
  `pnpm catalog:sync`
- Read-only API:
  `GET /catalog/health` and `GET /catalog/skus`

The current snapshot is intentionally small: CPU, mainboard, RAM, SSD, GPU, PSU,
and case SKUs for the next compatibility slice. It is not full catalog coverage
and does not claim live price or stock freshness. Freshness health is measured
against the local snapshot timestamp so stale fixtures are visible before
recommendations or evals run.

`US-016` extends the embedded validation report with demo-readiness coverage:
per-category SKU counts, required full-build demo categories, missing required
categories, and a `demo_ready` flag. The current fixture is demo-ready for the
first full-build flow because it includes CPU, mainboard, RAM, storage, VGA,
PSU, and case categories. Cooler and monitor remain optional for this slice.

`US-017` extends catalog health with demo variety warnings. The current
recommended minimum is two SKUs for each required full-build category. A
category with at least one SKU but fewer than the recommended count remains
demo-ready, but the report marks it as thin coverage so future SKU curation can
target the weakest slots first.

`US-018` moves snapshot generation from a hard-coded single fixture to a
multi-source manifest. Future catalog expansion should add saved public Phong
Vu payloads to `services/agent-api/fixtures/`, list them in
`catalog_sources.json`, enrich compatibility-critical fields in
`sku_specs_overrides.json`, then run `pnpm catalog:sync` and the quality gate.

`US-019` adds `pnpm catalog:capture` as the local source acquisition command.
It can fetch a public category URL or copy a saved HTML file, validates that the
payload contains parseable `__NEXT_DATA__` products, writes a sanitized fixture
containing only the Next.js data payload, and upserts a manifest entry with
relative path, source label, optional source URL, and optional category hint. It
does not make the snapshot live or complete: captured SKUs still need
compatibility-critical overrides before they should be used in recommendations.

`US-020` adds staged catalog sources and `pnpm catalog:source-report`. Manifest
entries default to enabled; entries with `enabled=false` are skipped by
`pnpm catalog:sync` but included in the source report. The current staged
captures cover CPU, mainboard, RAM, VGA, storage, PSU, case, cooler, and
monitor public category pages from 2026-06-28. They provide broad candidate
coverage for future curation, not recommendation-eligible SKUs yet.

`US-022` adds curated subset promotion through `include_skus` in
`catalog_sources.json`. Enabled curated entries can point at staged public
category fixtures but admit only reviewed SKUs into the active snapshot. The
first promoted subset adds one CPU, one mainboard, and one case SKU with
compatibility overrides, bringing every required full-build demo category to at
least two active SKUs while keeping the full category pages staged.

`US-039` extends the curated subset to one additional reviewed CPU, mainboard,
RAM, storage, VGA, PSU, and case SKU. The active snapshot now contains 21 SKUs:
three choices for every required full-build category, 14 verified spec rows,
and 7 partial spec rows with deterministic compatibility fields. Catalog health
now distinguishes:

- `demo_ready`: required categories are present with no blocking validation
  issues.
- `pilot_ready`: each required full-build category has at least three active
  SKUs and the snapshot is inside the 7-day freshness window.
- `production_ready`: all production target counts are met with no blocking
  issues and a fresh snapshot.

The current snapshot is pilot-ready for the core full-build categories but not
production-ready. Production target gaps remain for CPU, mainboard, RAM,
storage, VGA, PSU, case, cooler, and monitor until broader verified catalog
curation is selected.

`US-040` adds curated optional-category coverage for CPU coolers and monitors.
The active snapshot now contains 27 SKUs: three choices for every required
full-build category, three cooler choices, and three monitor choices. The
promoted cooler rows include `socket_support`, `tdp_rating_w`, and `height_mm`;
the promoted monitor rows include `resolution` and `refresh_rate_hz`. These
fields are enough for deterministic validation and future optional-slot work,
but the rows remain `partial` confidence until a richer detail-source pass is
implemented. Production target gaps remain because cooler target coverage is 8
SKUs and monitor target coverage is 10 SKUs.

`US-023` adds the first local gaming benchmark matrix:
`services/agent-api/benchmarks/gaming_benchmark_matrix.json`. Rows are curated
from public benchmark sources and include game/GPU aliases, resolution, preset,
render mode, FPS value or range, source label, source URL, matrix version, and
Vietnamese disclaimer. Benchmark rows are not catalog SKUs and do not affect
selection; they only allow the performance profile to display FPS evidence when
the generated build and user target match exactly.

`US-024` uses that benchmark evidence to warn about monitor overspec requests.
The system may warn that a requested 144Hz/240Hz display target exceeds the
source-backed FPS estimate. `US-040` adds curated monitor rows with
`resolution` and `refresh_rate_hz`. `US-041` uses those rows for optional
monitor add-on recommendations when the need explicitly mentions a monitor or
includes a resolution plus refresh target. These recommendations stay outside
selected PC parts, total price, approval, and the primary mock cart payload.

`US-042` uses curated cooler rows for optional CPU cooler recommendations when
the need asks for quiet operation or mentions a cooler. Cooler add-ons must pass
socket, TDP, and case-clearance checks against the selected CPU and case before
they are shown, and they remain outside the build total and primary mock cart.
`US-043` lets the user explicitly include those recommended add-ons in the mock
shopping list. The approved PC total and selected PC SKU map remain unchanged;
the handoff exposes separate add-on and combined shopping-list totals.

`US-030` expands the same matrix with RTX 4060 coverage for Cyberpunk 2077
1440p Ultra native. `US-031` uses that coverage to allow only
benchmark-preserving gaming GPU optimizer swaps, and `US-032` adds RX 7600
Cyberpunk 2077 1080p Ultra native evidence while keeping unsupported targets
unsupported.

`US-027` extends monitor handling for office and student requests by parsing
explicit monitor counts. Because the active catalog still lacks verified
GPU/mainboard output-port fields, multi-monitor office builds warn with
`OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN` instead of inventing HDMI/DisplayPort
support or recommending monitor bundles.

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
- `US-043` allows selected recommended add-on SKUs in that handoff, but keeps
  approval totals and selected PC SKUs separate from optional extras.
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

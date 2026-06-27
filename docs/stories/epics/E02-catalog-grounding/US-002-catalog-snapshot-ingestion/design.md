# Design

## Domain Model

Catalog entities live in `pc_build_copilot.catalog_models`:

- `CatalogSku`: normalized Phong Vu SKU, price, stock, URL, brand, warranty,
  highlights, structured specs, confidence, and snapshot timestamp.
- `CatalogSnapshot`: versioned generated JSON bundle with source path and
  validation report.
- `CatalogValidationReport`: blocking and warning issues for snapshot health.

Critical fields are explicit per component category. Missing fields such as CPU
socket, GPU TDP/length/connectors, PSU wattage/connectors, RAM type/capacity, or
case clearance block affected SKUs from safe compatibility use.

## Application Flow

1. `catalog_cli` reads a saved Phong Vu `__NEXT_DATA__` fixture.
2. `catalog_parser` extracts `serverProducts`, normalizes product fields, and
   infers lightweight specs from names/highlight chips.
3. `sku_specs_overrides.json` merges audited compatibility fields and marks
   confidence.
4. `catalog_validation` creates a blocking/warning report.
5. `catalog_snapshot.json` stores SKUs plus embedded validation for reproducible
   local reads.
6. `CatalogRepository` loads the snapshot and supports structured filters.

## Interface Contract

CLI:

```bash
pnpm catalog:sync
```

API:

- `GET /catalog/health` returns `CatalogValidationReport`.
- `GET /catalog/skus` supports filters for category, brand, price range, stock,
  socket, memory type, wattage, capacity, and VRAM.

The catalog API is read-only. It does not mutate Phong Vu systems or local
state.

## Data Model

Current storage is JSON:

- Fixture input: `services/agent-api/fixtures/phongvu-category-components.html`
- Overrides: `services/agent-api/catalog/sku_specs_overrides.json`
- Generated snapshot: `services/agent-api/catalog/catalog_snapshot.json`

No database schema or migration is introduced in this slice. Later PostgreSQL
and Typesense work can ingest the same snapshot contract.

## UI / Platform Impact

No browser UI changes are included. The web app can keep using the existing
session flow until `US-004` consumes catalog candidates.

## Observability

The generated snapshot embeds validation counts and issue details. Harness
trace records the skipped `catalog-ingestion` external-tool capability and the
verification commands.

## Alternatives Considered

1. Live scrape Phong Vu categories now. Rejected for this slice because no
   `catalog-ingestion` tool is registered and story verification must be
   network-independent.
2. Start with PostgreSQL/Typesense. Rejected for hackathon speed; JSON keeps the
   contract small while preserving a migration path.
3. Let the LLM infer missing compatibility specs. Rejected because compatibility
   fields must be deterministic and auditable.

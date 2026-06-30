# Design

## Domain Model

This story moves the existing catalog snapshot contract into Postgres without
changing SKU selection behavior:

- `CatalogSnapshot`
- `CatalogSku`
- `CatalogValidationReport`
- `CatalogIssue`

The Catalog Agent may still recommend only active catalog SKUs. Compatibility
spec fields remain deterministic data from parser output plus curated
overrides, not LLM guesses.

## Application Flow

1. `pnpm catalog:sync` keeps producing the validated JSON snapshot from saved
   Phong Vu payloads and curated overrides.
2. `pnpm catalog:load-postgres` loads that snapshot into Postgres, revalidates
   it, and marks the loaded snapshot version active.
3. The default API catalog repository chooses Postgres when a Postgres URL is
   configured and `PC_BUILD_COPILOT_CATALOG_STORE` is not `json`.
4. If Postgres has no active catalog version, the repository falls back to the
   local JSON snapshot so first deploys and local dev remain usable.

## Interface Contract

No HTTP route shape changes.

The existing routes keep their response models:

- `GET /catalog/health`
- `GET /catalog/skus`
- all build generation, alternatives, add-on, and upgrade flows that call
  `CatalogRepository.snapshot()`

## Data Model

Postgres tables:

- `catalog_versions`
  - Primary key: `snapshot_version`.
  - Metadata: `generated_at`, `source`, `sku_count`, `ingested_at`,
    `activated_at`, `is_active`.
  - Payload columns: `validation_json jsonb`, `payload_json jsonb`.
  - A partial unique index allows only one active version.
- `catalog_skus`
  - Primary key: `(snapshot_version, sku)`.
  - Foreign key to `catalog_versions`.
  - Query columns: `category`, `brand`, `price_vnd`, `stock_quantity`,
    `stock_status`, `specs_confidence`, `catalog_snapshot_at`.
  - Payload columns: `highlights_json jsonb`, `specs_json jsonb`,
    `payload_json jsonb`.

Indexes cover active version lookup, category/price filters, brand search,
in-stock category filters, and JSONB spec containment.

## UI / Platform Impact

No UI changes. Catalog freshness, pilot readiness, and production gaps continue
to surface through `GET /catalog/health`.

Production needs the active snapshot loaded into the same Neon Postgres
database that already stores sessions/builds.

## Observability

Platform proof should verify:

- `catalog_versions` has one active version.
- `catalog_skus` row count matches the loaded snapshot.
- Deployed `/api/catalog/health` returns the active snapshot version.
- Deployed `/api/catalog/skus` returns Postgres-backed filtered SKUs.

## Alternatives Considered

1. Keep JSON-only catalog in production. Rejected because the next real product
   step needs database-owned catalog versions and freshness proof.
2. Build Typesense/pgvector immediately. Deferred because the current active
   catalog has 27 SKUs; relational durability and active-versioning should come
   first.
3. Add scheduled scraping immediately. Deferred because the loaded active
   snapshot path must be reliable before automation runs on a schedule.
4. Use live Phong Vu/Teko APIs directly. Deferred until official API access is
   available.

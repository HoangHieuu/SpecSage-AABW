# Design

## Domain Model

This story reuses the existing catalog mirror and audit model:

- `CatalogSnapshot`
- `CatalogValidationReport`
- `CatalogRefreshResponse`
- `catalog_versions`
- `catalog_skus`
- `catalog_publish_runs`

The deployed JSON snapshot remains the validated ingestion artifact. The cron
path does not let an LLM choose SKUs, infer numeric compatibility facts, or
override validation.

## Application Flow

1. Vercel Cron sends `GET /api/catalog/refresh`.
2. The backend route validates `Authorization: Bearer <CRON_SECRET>`.
3. The refresh service resolves `DATABASE_URL`, `POSTGRES_URL`, or
   `POSTGRES_URL_NON_POOLING`.
4. The service reads the deployed `catalog_snapshot.json`.
5. The service calls `load_catalog_snapshot(..., allow_blocking=False)` with
   load options that identify the trigger as `vercel_cron`.
6. The existing loader records `catalog_publish_runs`, blocks invalid snapshots,
   and activates exactly one successful catalog version.

## Interface Contract

Protected platform route:

```text
GET /api/catalog/refresh
Authorization: Bearer <CRON_SECRET>
```

Success response:

```json
{
  "status": "loaded",
  "trigger": "vercel_cron",
  "snapshot_version": "catalog_v2026_06_27_fixture",
  "snapshot_generated_at": "2026-06-27T00:00:00Z",
  "source": "catalog_sources",
  "sku_count": 27,
  "issue_count": 0,
  "blocking_issue_count": 0
}
```

Failure behavior:

- `401` for missing or invalid bearer token.
- `503` when `CRON_SECRET` or a Postgres URL is not configured.
- `409` when catalog validation blocks the publish.

## Data Model

No new table is required. `catalog_publish_runs.load_options_json` now records
the scheduled trigger metadata:

```json
{
  "allow_blocking": false,
  "trigger": "vercel_cron",
  "snapshot_path": "..."
}
```

## UI / Platform Impact

`vercel.json` defines one daily cron job:

```json
{
  "path": "/api/catalog/refresh",
  "schedule": "0 18 * * *"
}
```

The schedule is UTC and runs daily at 01:00 Vietnam time. The route is not
customer-facing and has no browser UI.

## Observability

Durable observability remains in Postgres:

- each attempted publish creates a `catalog_publish_runs` row;
- successful runs have `status = loaded`;
- blocked validation has `status = blocked`;
- post-start loader exceptions are best-effort marked `failed`;
- no secrets are stored in audit payloads.

## Alternatives Considered

1. Cron live scraping public Phong Vu pages. Deferred because live scraping
   needs rate-limit, fixture, and validation controls before unattended writes.
2. Queue-based ARQ/BullMQ refresh. Deferred because the Vercel deployment can
   prove the scheduled publish path before a separate worker exists.
3. Unprotected route with obscured URL. Rejected because the endpoint mutates
   production catalog state.

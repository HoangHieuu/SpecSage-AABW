# Design

## Domain Model

This story adds audit metadata around the existing catalog publish path without
changing recommendation behavior:

- `CatalogSnapshot`
- `CatalogValidationReport`
- `catalog_versions`
- `catalog_skus`
- `catalog_publish_runs`

The active catalog remains limited to validated SKU payloads from the local
mirror. LLMs are not involved in catalog validation or activation.

## Application Flow

1. `pnpm catalog:sync` continues to produce the validated JSON snapshot.
2. `pnpm catalog:load-postgres` revalidates the snapshot before load.
3. The loader inserts a `catalog_publish_runs` row with status `started`.
4. If validation has blocking issues and `--allow-blocking` is not set, the run
   is marked `blocked` and SKU rows are not loaded.
5. If the load succeeds, the loader writes `catalog_versions`, rewrites the
   version's `catalog_skus`, activates exactly one version, and marks the run
   `loaded` inside the activation transaction.
6. If the load fails after the run starts, the loader attempts to mark the run
   `failed` and re-raises the original error.

## Data Model

`catalog_publish_runs` fields:

- `run_id`: Postgres identity primary key.
- `snapshot_version`, `snapshot_generated_at`, `source`.
- `status`: `started`, `loaded`, `blocked`, or `failed`.
- `sku_count`, `issue_count`, `blocking_issue_count`.
- `validation_json`, `load_options_json`.
- `started_at`, `finished_at`, `activated_at`.
- `error_text`.

Indexes cover snapshot-version lookup and status dashboards:

- `idx_catalog_publish_runs_snapshot_started`
- `idx_catalog_publish_runs_status_started`

## Interface Contract

No HTTP route shape changes.

The operator command remains:

```bash
pnpm catalog:load-postgres
```

The command still exits non-zero for blocked validation unless
`--allow-blocking` is passed through the Python module directly.

## Platform Impact

Production Neon gains one additional audit table. Existing deployed catalog
health and SKU query responses stay unchanged.

## Alternatives Considered

1. Wait until cron exists. Rejected because scheduled automation needs run
   history before it can be trusted.
2. Log publish results only to stdout. Rejected because Vercel/serverless logs
   are not the durable catalog source of truth.
3. Add an admin UI now. Deferred because mutation and staff/admin authorization
   are outside the current selected scope.

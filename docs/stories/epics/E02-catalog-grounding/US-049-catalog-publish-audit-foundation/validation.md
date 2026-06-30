# Validation

## Proof Strategy

The story is done when catalog publish attempts create durable Postgres audit
rows, blocked snapshots do not write SKU rows by default, existing catalog
query behavior remains unchanged, and production Neon records a successful
publish run for the active snapshot.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Schema includes `catalog_publish_runs`, status constraint, and publish-run indexes; successful loads mark a publish run loaded; blocked snapshots mark a publish run blocked. |
| Integration | Existing catalog API, ingestion, and build-generation tests continue to pass with publish audit enabled. |
| E2E | Not required; this is a backend operator-data slice. |
| Platform | Run `pnpm catalog:load-postgres` against Neon and verify the latest `catalog_publish_runs` row is `loaded`. |
| Logs/Audit | No secrets are logged or committed; audit rows store validation metadata, not credentials. |

## Fixtures

- `services/agent-api/catalog/catalog_snapshot.json`
- `services/agent-api/catalog/catalog_sources.json`
- `services/agent-api/catalog/sku_specs_overrides.json`
- Neon Postgres `DATABASE_URL` configured in Vercel production.

## Commands

```text
.venv/bin/python -m pytest services/agent-api/tests/test_postgres_catalog.py services/agent-api/tests/test_catalog_api.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_build_generation.py
pnpm check
scripts/bin/harness-cli story verify US-049
pnpm catalog:load-postgres
```

## Acceptance Evidence

- Focused verification passed: 69 tests across Postgres catalog, catalog API,
  catalog ingestion, and build generation.
- `pnpm check` passed with Next.js production build and 142 API tests.
- `scripts/bin/harness-cli story verify US-049` passed after rerun. The first
  parallel attempt collided with another simultaneous `next build` and failed
  on transient `.next/types` files.
- Neon publish proof: latest publish run for `catalog_v2026_06_27_fixture`
  recorded status `loaded`, 27 SKUs, 0 blocking issues, `finished=true`, and
  `activated=true`.
- Production platform proof: Vercel deployment completed and aliased to
  `https://specsage-aabw.vercel.app`; deployed `/api/health` returned `ok`;
  deployed `/api/catalog/health` returned snapshot
  `catalog_v2026_06_27_fixture`, 27 SKUs, and 0 blocking issues.

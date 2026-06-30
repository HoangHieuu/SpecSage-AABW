# Validation

## Proof Strategy

The story is done when the API can select a Postgres-backed catalog repository,
the current validated catalog snapshot can be loaded into Postgres, existing
catalog/build behavior remains unchanged, and the deployed app returns catalog
health from the active Postgres version.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Repository factory chooses Postgres when a database URL exists; `PC_BUILD_COPILOT_CATALOG_STORE=json` forces JSON fallback; schema includes active version and SKU indexes. |
| Integration | Catalog snapshot is revalidated before load; existing catalog API filters and build generation still pass. |
| E2E | Not required for this backend data slice; existing build flow remains covered by `pnpm check`. |
| Platform | Load the current snapshot into Neon, redeploy, verify `/api/catalog/health`, verify active version and row count in Postgres. |
| Performance | Indexes cover category/price, brand, in-stock, and JSONB spec lookup paths. |
| Logs/Audit | No secrets are logged or committed; `.env*.local` stays ignored. |

## Fixtures

- `services/agent-api/catalog/catalog_snapshot.json`
- `services/agent-api/catalog/catalog_sources.json`
- `services/agent-api/catalog/sku_specs_overrides.json`
- Neon Postgres `DATABASE_URL` configured in Vercel production.

## Commands

```text
.venv/bin/python -m pytest services/agent-api/tests/test_postgres_catalog.py services/agent-api/tests/test_catalog_api.py services/agent-api/tests/test_catalog_ingestion.py services/agent-api/tests/test_build_generation.py
pnpm check
pnpm catalog:load-postgres
scripts/bin/harness-cli story verify US-048
```

## Acceptance Evidence

- Focused verification passed: 68 tests across Postgres catalog, catalog API,
  catalog ingestion, and build generation.
- `pnpm check` passed with Next.js production build and 141 API tests.
- `scripts/bin/harness-cli story verify US-048` passed.
- Neon load proof: active snapshot `catalog_v2026_06_27_fixture`, one active
  catalog version, 27 loaded SKU rows, and 27 active SKU count.
- Direct Postgres repository proof: catalog health returned 27 SKUs with 0
  blocking issues; filtered VGA query returned 3 in-stock 8GB+ GPU SKUs.
- Production platform proof: Vercel deployment completed and aliased to
  `https://specsage-aabw.vercel.app`; deployed `/api/catalog/health` returned
  snapshot `catalog_v2026_06_27_fixture`, 27 SKUs, and 0 blocking issues;
  deployed `/api/catalog/skus?category=vga&in_stock=true&min_vram_gb=8`
  returned 3 matching SKUs.

# Validation

## Proof Strategy

`US-002` is proven at unit and integration layers. Browser E2E is not required
because this slice introduces ingestion and read-only API contracts, not a
customer-visible workflow.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Parse saved `__NEXT_DATA__`, normalize SKU fields, infer highlights, merge overrides, block missing required specs. |
| Integration | CLI writes `catalog_snapshot.json` with embedded validation; FastAPI exposes catalog health and filtered SKU queries. |
| E2E | Not required for ingestion-only slice. |
| Platform | Not required until scheduled sync, deploy, or live provider connectivity exists. |
| Performance | Not required for seven-SKU fixture; later catalog scale should add timing checks. |
| Logs/Audit | Snapshot validation report and Harness trace provide audit evidence. |

## Fixtures

- `services/agent-api/fixtures/phongvu-category-components.html`
- `services/agent-api/catalog/sku_specs_overrides.json`
- `services/agent-api/catalog/catalog_snapshot.json`

## Commands

```bash
pnpm catalog:sync
.venv/bin/python -m pytest services/agent-api/tests
pnpm check
scripts/bin/harness-cli story verify US-002
```

## Acceptance Evidence

- `pnpm catalog:sync`: wrote 7 SKUs with 0 blocking validation issues.
- `.venv/bin/python -m pytest services/agent-api/tests`: 14 passed.
- `pnpm check`: Next.js production build passed and 14 API tests passed.
- `scripts/bin/harness-cli story verify US-002`: pass.
- `US-002` verification command: `pnpm catalog:sync && pnpm test:api`.

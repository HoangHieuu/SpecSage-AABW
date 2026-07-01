# Validation

## Proof Strategy

The story is done when the protected refresh endpoint rejects unauthenticated
calls, fails closed when required environment variables are missing, loads a
valid deployed snapshot through the Postgres catalog publish/audit path, returns
a blocked response for invalid snapshots, and keeps existing web/API checks
passing.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | `CatalogRefreshResponse` and loader load-options path preserve publish-audit behavior. |
| Integration | FastAPI endpoint returns `503` without `CRON_SECRET`, `401` for a wrong bearer token, `503` without a Postgres URL, `200` for a valid refresh, and `409` for blocked validation. |
| E2E | Not required; this is a protected platform route with no customer UI. |
| Platform | Vercel Cron points at `/api/catalog/refresh`; production proof should invoke the deployed route with `CRON_SECRET` and verify a loaded `catalog_publish_runs` row. |
| Performance | The current endpoint loads the deployed 27-SKU snapshot; broader live scraping remains out of scope. |
| Logs/Audit | No secret is returned or stored; audit rows record trigger metadata, validation counts, and status only. |

## Fixtures

- `services/agent-api/catalog/catalog_snapshot.json`
- `services/agent-api/tests/test_catalog_refresh.py`
- `services/agent-api/tests/test_postgres_catalog.py`
- Vercel production `CRON_SECRET`
- Neon/Vercel `DATABASE_URL` or equivalent Postgres URL

## Commands

```text
.venv/bin/python -m pytest services/agent-api/tests/test_catalog_refresh.py services/agent-api/tests/test_postgres_catalog.py
pnpm check
scripts/bin/harness-cli story verify US-050
```

## Acceptance Evidence

- Focused verification passed: 11 tests across catalog refresh and Postgres
  catalog audit behavior.
- `pnpm check` passed with Next.js production build and 147 API tests.
- `scripts/bin/harness-cli story verify US-050` passed.
- Vercel production deployment completed and aliased to
  `https://specsage-aabw.vercel.app` with deployment
  `dpl_2Ksv1VSiW8xk7EBq9BuZNMhhcK7v`.
- Production smoke proof: `/api/health` returned `ok`; unauthenticated
  `/api/catalog/refresh` returned `401 Unauthorized`; authenticated
  `/api/catalog/refresh` returned `loaded` for
  `catalog_v2026_06_27_fixture`, 27 SKUs, 1 non-blocking issue, and 0 blocking
  issues; `/api/catalog/health` returned 27 SKUs and 0 blocking issues.
- Neon audit proof: latest `catalog_publish_runs` row recorded
  `snapshot_version = catalog_v2026_06_27_fixture`, `status = loaded`,
  `trigger = vercel_cron`, 27 SKUs, 1 issue, 0 blocking issues,
  `finished = true`, and `activated = true`.

# Exec Plan

## Goal

Add a protected scheduled publish refresh so production Postgres catalog state
can be kept aligned with the deployed validated catalog snapshot and audited
through the existing publish-run table.

## Scope

In scope:

- Add the US-050 story packet and Harness row.
- Add `CatalogRefreshResponse` and refresh service code.
- Add `GET /catalog/refresh` to the FastAPI backend.
- Require `Authorization: Bearer <CRON_SECRET>`.
- Wire one daily Vercel Cron entry to `/api/catalog/refresh`.
- Reuse `load_catalog_snapshot` and `catalog_publish_runs`.
- Add focused API and loader tests.
- Update product docs, decision log, README, and test matrix.

Out of scope:

- Live scraping or crawling from the scheduled endpoint.
- Typesense, pgvector, or embedding refresh.
- Admin or staff UI.
- Real cart/checkout or promo integration.

## Risk Classification

Risk flags:

- Data model: scheduled execution writes catalog mirror/audit rows.
- Audit/security: secret-gated protected mutation route.
- External systems: Vercel Cron invokes the deployed API.
- Public contracts: new protected platform endpoint.
- Existing behavior: catalog loader options and API routing change.

Hard gates:

- Audit/security.
- External provider behavior.

## Work Phases

1. Discovery: read existing catalog mirror, publish audit, Vercel config, and
   product docs.
2. Design: keep cron bounded to publish the deployed validated snapshot.
3. Validation planning: cover auth, missing config, success, blocked validation,
   and existing loader behavior.
4. Implementation: add service, route, cron config, tests, and docs.
5. Verification: run focused tests, `pnpm check`, and Harness story verify.
6. Platform proof: after env configuration, invoke the protected deployed route
   and verify a `catalog_publish_runs` loaded row.
7. Harness update: update story state, evidence, decision row, and trace.

## Stop Conditions

Pause for human confirmation if:

- The story needs live scraping instead of deployed snapshot publish refresh.
- A data migration or deletion path appears.
- Validation requirements need to be weakened.
- The endpoint needs to accept unauthenticated calls.
- Real Phong Vu/Teko private API access becomes part of the scope.

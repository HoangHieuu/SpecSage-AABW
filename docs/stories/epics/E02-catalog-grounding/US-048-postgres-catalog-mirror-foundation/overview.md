# Overview

## Current Behavior

The active catalog is generated from saved Phong Vu public payload fixtures into
`services/agent-api/catalog/catalog_snapshot.json`. The snapshot is validated,
real-SKU grounded, and pilot-ready for the core full-build flow, but production
API reads still depend on a repository-local JSON file baked into the
deployment.

## Target Behavior

The catalog snapshot can be loaded into PostgreSQL as the active catalog
version. In production, the Agent API prefers the active Postgres catalog when
a database URL is configured, while keeping the existing JSON snapshot as a
safe fallback for local development and empty catalog tables.

## Affected Users

- Customers receiving build recommendations from the deployed app.
- Developers running catalog sync and deployment checks.
- Operators checking catalog freshness and production readiness.

## Affected Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`
- `Data.md`
- `techstack.md`

## Non-Goals

- Fully automated scheduled scraping.
- Typesense, pgvector, semantic catalog search, or embeddings.
- Admin catalog editing or human review UI.
- Real Phong Vu/Teko private catalog API access.
- Real cart/checkout or promo integration.

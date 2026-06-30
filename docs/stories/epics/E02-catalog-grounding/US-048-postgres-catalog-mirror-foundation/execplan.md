# Exec Plan

## Goal

Move the active product catalog from deployment-bundled JSON only to a
production-readable Postgres catalog mirror with active-version semantics and
freshness proof.

## Scope

In scope:

- Add Postgres catalog version and SKU schema.
- Add a loader CLI for the current validated catalog snapshot.
- Add API repository selection that prefers Postgres in production.
- Preserve JSON fallback for local development and empty Postgres catalog
  tables.
- Verify existing catalog API and build generation behavior.
- Load the active snapshot into Neon and prove production reads it.

Out of scope:

- Scheduled crawler infrastructure.
- Typesense, pgvector, or semantic retrieval.
- Admin catalog editing.
- Private Teko/Phong Vu APIs.
- Real checkout, promos, or cart mutation.

## Risk Classification

Risk flags:

- Data model.
- External systems.
- Public contracts.
- Existing behavior.
- Weak proof until platform load is verified.

Hard gates:

- External provider behavior.

The direction is selected by `Data.md` and `techstack.md`: Postgres is the
primary Phase 2 catalog datastore, but the local mirror remains the ingestion
source until official APIs or scheduled crawling are selected.

## Work Phases

1. Discovery: read source snapshots, catalog repository, catalog CLI, validation
   rules, and current matrix.
2. Design: choose active Postgres snapshot mirror before Typesense/pgvector.
3. Implementation: add Postgres catalog repository, schema, loader CLI, and API
   selection.
4. Verification: run focused catalog tests and full `pnpm check`.
5. Platform: load the active snapshot into Neon, redeploy, and verify catalog
   health and row count.
6. Harness update: record intake, story, decision, and evidence.

## Stop Conditions

Pause for human confirmation if:

- We need live scraping credentials or private API access.
- The catalog load would require deleting or rewriting unrelated production
  tables.
- Validation requirements need to be weakened.
- The next step changes from catalog freshness to checkout/auth/admin.

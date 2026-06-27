# Exec Plan

## Goal

Implement a reproducible local catalog snapshot pipeline that can parse saved
Phong Vu public frontend payloads, enrich compatibility-critical specs through
auditable overrides, validate the snapshot, and expose read-only API queries for
the next compatibility and build-generation stories.

## Scope

In scope:

- Parse saved `__NEXT_DATA__`-style category payload fixtures.
- Normalize SKU ID, name, category, price, stock, URL, brand, warranty, and
  highlight fields.
- Apply versioned curated spec overrides from JSON.
- Generate `services/agent-api/catalog/catalog_snapshot.json`.
- Validate missing compatibility-critical fields as blocking issues.
- Expose read-only `/catalog/health` and `/catalog/skus` API endpoints.
- Cover parser, enrichment, validation, CLI, and API with tests.

Out of scope:

- Live scraping or scheduled crawling of `phongvu.vn`.
- Firecrawl, TinyFish, Bright Data, or Teko/private API integration.
- PostgreSQL, Typesense, pgvector, image mirroring, or product detail crawling.
- Staff/admin review UI for overrides.
- Checkout/cart behavior.

## Risk Classification

Risk flags:

- Data model: introduces typed catalog SKU/snapshot/validation contracts.
- External systems: uses Phong Vu public-page payload shape, but only from a
  saved fixture in this slice.
- Public contracts: adds read-only API endpoints consumed by later stories.
- Weak proof: first catalog proof is fixture-based, not live provider proof.

Hard gates:

- No credentials, private API, auth, data migration, or destructive storage.
- Story verification must not depend on live Phong Vu availability.

## Work Phases

1. Discovery: read source snapshots, product docs, story packet, matrix, and
   tool registry.
2. Design: define typed catalog, snapshot, validation, repository, and CLI
   boundaries inside `services/agent-api`.
3. Validation planning: fixture parser tests, validation tests, CLI integration
   test, API query tests.
4. Implementation: add parser, overrides, generated snapshot, repository, API
   endpoints, and docs.
5. Verification: run `pnpm catalog:sync`, backend tests, `pnpm check`, and
   Harness story verification.
6. Harness update: mark `US-002` implemented and record a detailed trace.

## Stop Conditions

Pause for human confirmation if:

- Live scraping, credentials, or private API access becomes required.
- A product-data source cannot be represented as a reproducible fixture.
- Validation requirements need to be weakened.
- The snapshot format must become a database migration instead of JSON.

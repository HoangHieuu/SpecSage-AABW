# US-021 Sanitized Catalog Fixtures

## Status

implemented

## Lane

high-risk

## Product Contract

The local catalog mirror may capture public Phong Vu pages, but committed
fixtures must contain only the deterministic product payload required by the
catalog parser. Page shell scripts, public environment blocks, and unrelated
third-party keys must not be committed with fixture data.

## Relevant Product Docs

- `docs/product/data-strategy.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/decisions/0022-sanitized-catalog-captures-before-committed-fixtures.md`

## Acceptance Criteria

- `pnpm catalog:capture` writes a sanitized fixture containing only
  `__NEXT_DATA__`.
- Existing catalog fixtures are sanitized to remove page environment scripts
  while preserving parseable product payloads.
- Local scans do not find Google API key patterns in the current working tree
  outside `.git`.
- Raw capture review files are ignored by default.
- Catalog source reporting, sync, full checks, and evals still pass.

## Design Notes

- Sanitization uses the existing Next.js payload extractor, then renders a
  minimal HTML fixture with the `__NEXT_DATA__` script.
- The parser remains unchanged: sanitized fixtures are still valid inputs to
  `parse_next_data_products`.
- No runtime API or web UI behavior changes.
- This story does not revoke external provider keys and does not rewrite Git
  history. Those are separate operator actions.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-021 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Focused catalog tests cover capture sanitization and preserved product parsing. |
| Integration | `pnpm catalog:source-report`, `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`, and local secret-pattern scans. |
| E2E | Not required; this is catalog fixture/tooling infrastructure. |
| Platform | Not required; no hosted provider integration changes. |
| Logs/Audit | Harness intake, decision, story, and trace record the security remediation. |

## Harness Delta

This story changes the catalog capture contract from raw public page storage to
sanitized fixture storage.

## Evidence

Validation passed:

- Local scan found no Google API key patterns in the current working tree
  outside `.git`.
- `.venv/bin/python -m pytest services/agent-api/tests/test_catalog_ingestion.py`
  passed with 14 focused catalog tests.
- `pnpm catalog:source-report` reported 370 unique SKU candidates from 10
  sources, with 1 enabled source and 9 staged sources.
- `pnpm catalog:sync` wrote the active 11-SKU snapshot with 0 blocking issues.
- `pnpm check` passed with Next.js build and 80 API tests.
- `pnpm eval:run` passed 30/30 canonical scenarios.

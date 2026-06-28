# 0022 Sanitized Catalog Captures Before Committed Fixtures

## Status

Accepted

## Context

`US-019` made public Phong Vu category capture repeatable, and `US-020` staged
broader saved captures before recommendation eligibility. The initial broad
captures stored full public HTML pages. Those pages include unrelated page-shell
environment data such as public Google/Firebase keys, which GitHub secret
scanning treats as leaked secrets even though the catalog parser only needs the
Next.js product payload.

## Decision

Committed catalog fixtures must store only the parseable `__NEXT_DATA__`
payload needed by the local catalog mirror.

- `pnpm catalog:capture` validates the original page, then writes a sanitized
  fixture containing only `__NEXT_DATA__`.
- Existing committed category fixtures are rewritten to the same sanitized
  shape.
- Raw captured pages remain local-only review artifacts and are ignored under
  `services/agent-api/fixtures/raw_html/` or `*.raw.html`.
- Catalog parsing, source reporting, sync, and evals continue to use local
  fixtures without requiring live Phong Vu access.

## Consequences

- Future fixture commits avoid page-level public keys and unrelated scripts.
- Secret scanning should not flag current fixture contents for Google API keys.
- The pushed commit that contained raw fixtures still exists in remote history
  until the branch history is rewritten or the alert is closed after external
  key revocation/ownership review.
- Keeping only `__NEXT_DATA__` reduces fixture noise while preserving the SKU,
  price, stock, image, link, and category data needed by current parsers.

## Follow-Ups

- Rotate or revoke any affected keys if the project owner controls them.
- If required for the public repository, rewrite the pushed commit history to
  remove the raw fixture blobs and force-push with explicit maintainer approval.
- Keep future product-detail captures under the same sanitized-fixture rule.

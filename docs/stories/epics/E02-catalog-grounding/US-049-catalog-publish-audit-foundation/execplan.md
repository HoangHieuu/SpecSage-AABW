# Execution Plan

## Steps

1. Add the US-049 story packet and Harness rows.
2. Extend Postgres catalog schema with `catalog_publish_runs`.
3. Update the catalog loader to record started, loaded, blocked, and failed
   publish outcomes.
4. Add focused tests for schema, successful publish audit, and blocked publish
   audit.
5. Update product docs, test matrix, and README.
6. Run focused tests, `pnpm check`, and Harness story verification.
7. Load the active snapshot into Neon and verify latest publish-run metadata.
8. Commit and push the implemented slice.

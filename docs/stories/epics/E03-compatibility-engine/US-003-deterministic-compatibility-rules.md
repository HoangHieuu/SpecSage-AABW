# US-003 Deterministic Compatibility Rules

## Status

implemented

## Lane

normal

## Product Contract

Compatibility checks are deterministic, versioned, and block invalid builds
before explanations or commerce handoff.

## Relevant Product Docs

- `docs/product/technical-architecture.md`
- `docs/product/data-strategy.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- CPU/mainboard socket mismatch returns `COMPAT_SOCKET_MISMATCH` block.
- RAM type mismatch returns a block-level compatibility result.
- PSU wattage and GPU connector checks produce block-level failures.
- GPU/case clearance and cooler/case checks produce block or warning severity
  according to configured thresholds.
- Compatibility report includes rules version, catalog version, status, severity,
  Vietnamese explanation key, and remediation hints.
- Final build cannot be approved with any block-level result.

## Design Notes

- Commands: validate build.
- Queries: none beyond selected SKU/spec lookup.
- API: `POST /builds/{id}/validate`.
- Tables/files: `services/agent-api/rules/compatibility_rules_v2026_06_27.json`
  and Pydantic compatibility report schema.
- Domain rules: pure functions with Pydantic models.
- UI surfaces: compatibility report panel.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | rule tests for socket, RAM, PSU, GPU/case, cooler/case |
| Integration | API validation rejects invalid build payloads |
| E2E | optional in US-004 vertical slice |
| Platform | none |
| Release | story verify command once implemented |

## Harness Delta

The test matrix should mark unit proof required for any future rule changes.

## Evidence

- Added deterministic rule engine in
  `services/agent-api/src/pc_build_copilot/compatibility_rules.py`.
- Added report/request schema in
  `services/agent-api/src/pc_build_copilot/compatibility_models.py`.
- Added versioned rule manifest
  `services/agent-api/rules/compatibility_rules_v2026_06_27.json`.
- Added `POST /builds/{build_id}/validate`.
- `.venv/bin/python -m pytest services/agent-api/tests` passed with 26 tests.
- `pnpm check` passed with Next.js production build and 26 API tests.
- `scripts/bin/harness-cli story verify US-003` passed.
- Rule tests cover socket mismatch, RAM type mismatch, PSU wattage, GPU power
  connector, GPU/case clearance, cooler/case clearance, missing SKU, and final
  approval blocking when a block-level result exists.

# US-001 Session And Intent Foundation

## Status

implemented

## Lane

normal

## Product Contract

Users can start a build session, describe PC needs in Vietnamese or mixed
Vietnamese-English, receive focused clarifying questions, and confirm a
structured `BuildIntent` before generation begins.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`

## Acceptance Criteria

- A session ID is created with timestamp, locale, channel, and TTL behavior.
- Free-text intent maps to structured fields for use case, budget range, games,
  apps, performance targets, form factor, brand, noise, and aesthetics.
- Missing required fields trigger at most one focused clarification per turn.
- Mixed Vietnamese-English terms such as GPU model names and refresh rates are
  preserved.
- The user can confirm or revise the intent summary before build generation.

## Design Notes

- Commands: create session, submit intent, revise intent.
- Queries: read session, read intent revisions.
- API: `POST /sessions`, `POST /sessions/{id}/intent`.
- Tables: `build_sessions`, `intent_revisions`.
- Domain rules: budget parser handles `trieu`, `tr`, and numeric VND forms
  before LLM fallback.
- UI surfaces: first customer web flow only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest services/agent-api/tests` covers budget parser, preset/use-case mapping, and `BuildIntent` schema flow |
| Integration | `.venv/bin/python -m pytest services/agent-api/tests` covers FastAPI session and intent endpoints |
| E2E | Browser desktop flow at `http://127.0.0.1:3000` covers Vietnamese prompt to confirmed intent summary |
| Platform | none |
| Release | `pnpm check` |

## Harness Delta

Story verification now uses `pnpm check`.

## Evidence

- `pnpm check` passed: Next.js typecheck/build and 7 FastAPI/parser tests.
- Browser desktop QA passed: page title `PC Build Copilot`, nonblank content,
  no console errors, `Phân tích intent` and `Xác nhận intent` produced a
  confirmed summary with `25.000.000`, `Valorant`, `LMHT`, `144Hz`, and a
  `bs_` session ID.
- Browser mobile viewport override could not be completed because the Browser
  viewport capability timed out; mobile remains a follow-up rendered QA item.

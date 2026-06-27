# US-006 OpenRouter LLM Intent Advisor

## Status

implemented

## Lane

normal

## Product Contract

Intent analysis may call OpenRouter with `deepseek/deepseek-v4-flash` to add a
Vietnamese advisory summary, clarification suggestion, and safety notes to the
intent response. The LLM output is explanatory only. Deterministic parser
fields, catalog SKUs, prices, budget gates, compatibility reports, build
generation, approval, and cart handoff remain authoritative code or catalog
outputs.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/TEST_MATRIX.md`

## Acceptance Criteria

- Backend reads OpenRouter configuration from local environment without
  exposing the API key to the browser or logs.
- `POST /sessions/{build_session_id}/intent` can opt into LLM analysis with
  `use_llm=true` and returns nullable `agent_analysis`.
- Provider errors, invalid JSON, missing credentials, or disabled LLM mode never
  block deterministic intent parsing or confirmation.
- Frontend shows the LLM Agent model, status, Vietnamese summary, suggested
  clarification, confidence notes, and safety notes when analysis is present.
- LLM analysis does not mutate the stored `BuildIntent` revision and is not
  called during confirm/generate/approve actions.

## Design Notes

- Commands: `OPENROUTER_API_KEY`, optional `OPENROUTER_MODEL`,
  `LLM_AGENT_ENABLED`, `OPENROUTER_TIMEOUT_SECONDS`,
  `OPENROUTER_MAX_TOKENS`.
- Queries: no catalog or database query changes.
- API: `IntentRequest.use_llm` opt-in flag and
  `IntentResponse.agent_analysis`.
- Tables: none; still using in-memory stores for the first slice.
- Domain rules: LLM output is advisory and may not decide SKU, price, stock,
  budget, or compatibility.
- UI surfaces: summary panel adds an inline LLM Agent section.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | OpenRouter config/client/advisor tests with fake transport |
| Integration | FastAPI intent endpoint includes/skips `agent_analysis` correctly |
| E2E | Browser flow shows the LLM Agent panel and still confirms/generates safely |
| Platform | Optional live OpenRouter call with local `.env` key |
| Release | `pnpm check`; `scripts/bin/harness-cli story verify US-006` |

## Harness Delta

No harness behavior change. The story records provider-boundary friction in the
trace if live OpenRouter availability differs from local test proof.

## Evidence

- `.venv/bin/python -m pytest services/agent-api/tests`: 43 passed, 1
  existing Starlette/httpx deprecation warning.
- `pnpm check`: Next.js build passed and API tests passed.
- Direct OpenRouter diagnostic returned HTTP 200 for
  `deepseek/deepseek-v4-flash-20260423`.
- Playwright browser flow showed `LLM Agent` as `Đang hoạt động` with
  `OpenRouter deepseek/deepseek-v4-flash`, then confirmed intent and generated
  a valid 7-SKU build under budget.
- Browser console had one existing missing `favicon.ico` 404 and no feature
  regression errors.

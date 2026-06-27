# Stories

Stories are work packets. They turn product intent into bounded implementation
and validation work.

Initial PC Build Copilot story packets:

| Story | Title | Status | Lane |
| --- | --- | --- | --- |
| `US-000` | Product contract wiring | implemented | high-risk |
| `US-001` | Session and intent foundation | implemented | normal |
| `US-002` | Catalog snapshot ingestion | implemented | high-risk |
| `US-003` | Deterministic compatibility rules | implemented | normal |
| `US-004` | Build generation vertical slice | implemented | normal |
| `US-005` | Review approval and mock cart-ready handoff | implemented | normal |
| `US-006` | OpenRouter LLM intent advisor | implemented | normal |
| `US-007` | Deterministic performance fit profile | implemented | normal |
| `US-008` | Build alternatives and iteration controls | implemented | normal |
| `US-009` | Apply alternative as active build | implemented | normal |
| `US-010` | Persistent session and build store | implemented | normal |
| `US-011` | LangGraph build orchestration foundation | implemented | normal |

Use `scripts/bin/harness-cli query matrix` for durable status before work.

## Normal Story

Use `docs/templates/story.md` for normal feature work.

Suggested path:

```text
docs/stories/epics/E01-domain-name/US-001-short-story-title.md
```

## High-Risk Story

Use `docs/templates/high-risk-story/` when the feature intake classifies work as
high-risk.

`US-002` is already marked high-risk because catalog ingestion touches external
product data and catalog contracts. Expand it into the high-risk folder template
before implementation if it introduces live scraping, credentials, provider
APIs, or persisted product data.

Suggested path:

```text
docs/stories/epics/E02-risky-domain/US-012-risky-story-title/
  execplan.md
  overview.md
  design.md
  validation.md
```

## Status Flow

```text
planned -> in_progress -> implemented
                  |
                  v
               changed
                  |
                  v
               retired
```

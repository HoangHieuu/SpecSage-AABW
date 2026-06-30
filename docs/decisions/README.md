# Decisions

Decision records explain why important product, architecture, or harness choices
were made.

Use `docs/templates/decision.md` when adding a new decision.

## Current Project Decisions

| ID | Title |
| --- | --- |
| `0008` | PC Build Copilot source hierarchy |
| `0009` | Hybrid Python and TypeScript stack |
| `0010` | Local catalog mirror before private API |
| `0011` | Local SQLite product state before Postgres |
| `0012` | LangGraph build orchestration before autonomous optimization |
| `0013` | Local trace replay before Langfuse |
| `0014` | Local quality evals before Langfuse experiments |
| `0015` | CI quality gate for local evals |
| `0016` | Feedback capture before admin console |
| `0017` | Catalog demo readiness before live scraping |
| `0018` | Catalog variety health before broad SKU expansion |
| `0019` | Catalog source manifest before live scraping |
| `0020` | Public category capture before automated scraping |
| `0021` | Staged catalog captures before recommendations |
| `0022` | Sanitized catalog captures before committed fixtures |
| `0023` | Curated catalog subsets before source enablement |
| `0024` | Local benchmark matrix before performance claims |
| `0025` | Monitor overspec warning before monitor SKU recommendations |
| `0026` | Balance score before optimizer weighting |
| `0027` | Config-driven workload profiles before app benchmarks |
| `0028` | Office monitor guidance before monitor SKU recommendations |
| `0029` | Deterministic alternative ranking before autonomous optimization |
| `0030` | One-swap budget optimizer before full search |
| `0031` | Benchmark coverage before gaming GPU auto-swaps |
| `0032` | Benchmark-preserving gaming optimizer guard |
| `0033` | Source-backed benchmark coverage before broader FPS claims |
| `0034` | Bounded two-swap optimizer before full search |
| `0035` | Benchmark delta ranking before broader gaming search |
| `0036` | Config-driven optimizer loop before Pareto search |
| `0037` | Natural-language iteration before Pareto variants |
| `0038` | Managed Postgres state before AWS RDS |

After adding or updating a markdown decision file, also add or refresh the
durable decision row:

```bash
scripts/bin/harness-cli decision add \
  --id 0008-auth-boundary \
  --title "Auth Boundary" \
  --doc docs/decisions/0008-auth-boundary.md
```

Trace fields such as `--decisions` summarize task-level choices. They do not
count as the Harness decision log.

Add a decision when:

- A locked technical choice changes.
- A product rule changes meaningfully.
- A validation requirement is added, removed, or weakened.
- A high-risk feature chooses one design over another.
- Auth, authorization, data ownership, audit/security, or API behavior changes.
- The source-of-truth hierarchy changes.

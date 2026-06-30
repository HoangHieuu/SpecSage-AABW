# Validation Strategy

## Proof Ladder

| Layer | What it proves |
| --- | --- |
| Unit | Parsers, rules, scoring, optimizer helpers, DTO validation |
| Integration | FastAPI endpoints, database constraints, catalog sync, search, adapters |
| E2E | Browser path from Vietnamese intent to visible validated build |
| Platform | Deployment health, environment config, real provider connectivity |

Use the smallest proof that actually exercises the contract. Do not mark a
story implemented until its expected proof is recorded in Harness.

## First Canonical Scenarios

| ID | Persona | Input | Expected outcome |
| --- | --- | --- | --- |
| T-01 | First-time | Gaming 20M, Valorant + League at 1080p | Valid GPU-weighted build under budget |
| T-02 | Parent | Office/study 12M, quiet | iGPU or entry GPU, SSD 512GB+, approved |
| T-03 | Creator | Premiere/After Effects 35M | 32GB+ RAM, VRAM-aware GPU, NVMe storage |
| T-04 | Enthusiast | Cyberpunk 1440p High, 30M | Warns if FPS target is unlikely |
| T-05 | Upgrader | Existing i5-12400F/B660/RTX 3060, GPU budget 10M | Compatible upgrade options and PSU check |
| T-06 | Edge | Gaming 8M | Honest over-budget or nearest viable option |
| T-07 | Edge | Incompatible CPU/mainboard swap | Hard block with remediation |
| T-08 | Staff | T-01 through staff console | QR/share handoff when staff scope exists |
| T-09 | Commerce | Build with active combo promo | Promo savings shown when promo data exists |
| T-10 | AI use case | Local LLM 13B, 40M | VRAM guidance and 32GB+ RAM |

The first demo does not need all ten scenarios automated. It should automate at
least T-01, T-02, T-06, and T-07 before claiming the vertical slice is stable.

## Story Verification Commands

Early docs-only stories may verify with Harness queries. Implementation stories
should replace those with real checks, for example:

```bash
pnpm catalog:sync
pnpm check
pytest services/agent-api packages/rules-engine
pnpm test:e2e
scripts/bin/harness-cli story verify US-003
```

`US-003` is currently verified by `pnpm test:api`, which covers the pure rule
engine and `POST /builds/{build_id}/validate` integration contract.

`US-004` is currently verified by `pnpm check` plus Browser E2E against local
dev servers. Required rendered flows are one happy path from Vietnamese intent
to visible generated build and one over-budget path with an explicit gap.

`US-005` is verified by `pnpm check` plus Browser E2E against local dev
servers. Required rendered flows are one happy path from Vietnamese intent to a
visible cart-ready handoff and one over-budget path proving approval remains
blocked or the API returns 409.

`US-006` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit and integration proof must mock OpenRouter transport so normal validation
does not spend tokens. Browser proof should make one live intent analysis call
when `OPENROUTER_API_KEY` is configured, then confirm/generate to prove the
deterministic flow still works if the LLM panel is available or degraded.

`US-007` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers deterministic fit thresholds for gaming, creator, AI/local
LLM, and office builds. Integration proof checks the generate endpoint returns
`performance_profile`. Browser proof must show the generated build view renders
the `Mức phù hợp` panel. Unsupported numeric FPS claims remain blocked.

`US-023` is verified by focused benchmark lookup tests, build generation tests,
`pnpm check`, `pnpm eval:run`, and Harness story verification. Unit proof covers
local matrix loading, exact-match lookup, and FPS target parsing. Integration
proof checks that a matching Cyberpunk/RX 7600/1440p/Ultra request emits
`source="benchmark"` evidence with provenance and raises `PERF_BELOW_TARGET`
when the row is below a declared high-refresh target. Eval proof must still
reject unsupported numeric FPS claims while allowing FPS only in benchmark
evidence with source label and URL.

`US-024` is verified by focused parser and build generation tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks
Vietnamese monitor mentions are captured in `BuildIntent.mentioned_components`.
Integration proof checks that a monitor-targeted Cyberpunk/RX
7600/1440p/Ultra/144Hz request raises `PERF_MONITOR_OVERSPEC` from matched
benchmark evidence and does not add monitor SKUs.

`US-030` is verified by focused benchmark/build generation tests, `pnpm check`,
`pnpm eval:run`, and Harness story verification. Unit proof checks RTX 4060
Cyberpunk 2077 1440p Ultra exact lookup returns source-backed evidence.
Integration proof checks a generated RTX 4060 Cyberpunk 1440p Ultra 144Hz build
raises `PERF_BELOW_TARGET` instead of dropping benchmark provenance.

`US-031` is verified by focused build generation tests, `pnpm check`, `pnpm
eval:run`, and Harness story verification. Unit proof checks Cyberpunk 2077
1440p Ultra can auto-swap from RX 7600 to RTX 4060 only when the candidate has
exact benchmark evidence, while Valorant and already-sufficient benchmark
targets do not auto-swap. Integration proof checks the optimized artifact still
reruns compatibility, budget, performance profile, warnings, and explanations.

`US-032` is verified by focused benchmark/build generation tests, `pnpm check`,
`pnpm eval:run`, and Harness story verification. Unit proof checks the matrix
loads RX 7600 Cyberpunk 2077 1080p Ultra source-backed evidence and unsupported
resolutions still return no estimates. Integration proof checks exact matching
requests can surface the new benchmark evidence without interpolation.

`US-025` is verified by focused build generation/orchestration tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks
normal builds expose a balance score and intentionally imbalanced CPU/GPU/RAM
facts raise `PERF_IMBALANCE`. Integration proof checks the generate endpoint
returns `performance_profile.balance`; trace proof checks the performance agent
exports the score in its outputs.

`US-026` is verified by focused parser/build generation tests, `pnpm check`,
`pnpm eval:run`, and Harness story verification. Unit proof checks OBS/streaming
apps and local LLM model classes are parsed. Integration proof checks Premiere,
After Effects, Photoshop, OBS/streaming, and Local LLM 13B return app-fit rows
with bottleneck labels and workload warnings when thresholds are missed.

`US-027` is verified by focused parser/build generation tests, `pnpm check`,
`pnpm eval:run`, and Harness story verification. Unit proof checks explicit
monitor counts and office quiet preference parsing. Integration proof checks
office profiles explain no-iGPU discrete GPU requirements, iGPU office
suitability, and `OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN` warnings without adding
monitor SKUs.

`US-008` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers deterministic alternative generation from catalog SKUs,
changed slot deltas, compatibility revalidation, and absence of FPS claims.
Integration proof checks `GET /builds/{build_id}/alternatives` returns variants
for stored builds and 404s missing build IDs. Browser proof must show the
generated build view renders the `Phương án thay thế` panel with concrete SKU deltas.

`US-009` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers converting a deterministic variant into a new versioned build
artifact. Integration proof checks
`POST /builds/{build_id}/alternatives/{variant_id}/apply` stores a new build,
preserves the original build, rejects missing variants, and allows approval when
the applied build remains eligible. Browser proof must apply a visible variant,
show the main build table updated, and approve the applied build through the
existing handoff gate.

`US-028` is verified by focused build generation tests, `pnpm check`,
`pnpm eval:run`, and Harness story verification. Unit proof checks alternatives
are sorted by rank/score and AI workload alternatives prioritize CUDA/NVIDIA
when the deterministic performance profile indicates CUDA relevance.
Integration proof checks the alternatives endpoint returns rank, score,
priority, and ranking reasons for stored builds.

`US-029` is verified by focused build/orchestration/persistence tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks the
generator applies recommended creator RAM and streaming NVIDIA swaps while raw
profile tests can disable the optimizer. Integration proof checks generated
artifacts remain stored, approvable, budget-gated, and replayable through the
existing orchestration and SQLite paths.

`US-033` is verified by focused build/orchestration/persistence tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks the
generator applies creator RAM+SSD and AI GPU+RAM sequences while streaming stops
after one eligible swap. Integration proof checks orchestration and SQLite
persistence still store generated artifacts and traces after optimizer changes.

`US-034` is verified by focused build generation and benchmark tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks the
Cyberpunk 2077 1440p Ultra RTX 4060 alternative ranks first because exact
benchmark evidence improves over the RX 7600 base, and that ranking reasons do
not add raw numeric FPS text to generated explanations. Integration proof
checks the existing generation guard still skips auto-apply when the base
benchmark already meets the declared target.

`US-035` is verified by focused build generation and orchestration tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks
config-driven budget allocation, priority overrides, accepted/rejected
optimizer decisions, and preservation of the benchmark gate for gaming
auto-swaps. Integration proof checks the LangGraph optimizer step exports
optimizer-loop counts and tool calls.

`US-036` is verified by the API demo-flow test, browser desktop/mobile proof,
`pnpm check`, `pnpm eval:run`, and Harness story verification. The demo proof
must show the Cyberpunk 2077 prompt, customer-facing build summary,
benchmark-backed warning, alternatives panel, applied build, mock cart handoff,
saved feedback, support-details access to optimizer trace, and no page-wide
horizontal overflow on mobile.

`US-037` is verified by focused parser, API, generation, and trace replay
tests, `pnpm check`, `pnpm eval:run`, Harness story verification, and browser
proof. Unit proof checks command parsing and deterministic rejection behavior.
Integration proof checks `POST /builds/{id}/iterate` creates a versioned build,
keeps unsupported commands from guessing, preserves budget/compatibility gates,
and appends iteration decisions to `optimizer_trace`. Browser proof must show a
generated Cyberpunk build, the `Điều chỉnh build` panel, an applied SSD command,
and the resulting build v2 state.

`US-038` is verified by `pnpm check:web`, Harness story verification, and
browser desktop/mobile proof. Browser proof must show Basic mode with
buyer-facing copy, the customer decision summary, no customer-visible
engineering/demo terminology in the first decision path, advanced details still
reachable, and no page-wide horizontal overflow.

`US-010` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit and integration proof cover SQLite round-trips for sessions, intent
revisions, builds, applied build versions, and idempotent cart handoffs by
re-instantiating FastAPI apps over the same DB file. Browser proof must show the
default persistent API still supports the generate -> alternatives -> apply ->
approve flow.

`US-011` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers the LangGraph orchestration service, expected agent sequence,
and deterministic build output preservation. Integration proof checks the
generate endpoint returns `orchestration_trace` and existing alternatives,
apply, approval, and SQLite persistence paths remain compatible. Browser proof
must show the generated build view renders the `Agent orchestration` panel.

`US-012` is verified by `pnpm check` plus Browser E2E against local dev servers.
Unit proof covers trace replay conversion and PII-sensitive payload redaction.
Integration proof checks build/session trace endpoints, build-version grouping,
support-export text, and SQLite restart survival. Browser proof must show the
generated build view keeps trace details out of the default customer path while
`Chi tiết hỗ trợ` renders the support trace with redacted events and a support-export
copy action.

`US-013` is verified by `pnpm check`, `pnpm eval:run`, and Harness story
verification. Unit proof covers canonical scenario loading, minimum scenario
count, persona/budget coverage, and hallucinated-SKU failure detection.
Integration proof runs 30 scenarios through the deterministic parser and
LangGraph-wrapped generator against the local catalog snapshot. Browser proof is
not required because this story adds a local release gate, not a UI surface.

`US-014` is verified locally by `pnpm check`, `pnpm eval:run`, and Harness story
verification, and structurally by the checked-in GitHub Actions workflow. The
workflow installs pnpm, Node.js, Python, and Agent API dev dependencies before
running the same local gate. Browser proof is not required because the story has
no user-visible surface. Hosted CI pass evidence should be added after the
workflow runs on GitHub.

`US-015` is verified by focused feedback API tests, SQLite restart-survival
tests, `pnpm check`, `pnpm eval:run`, Harness story verification, and Browser
E2E. Integration proof must show that feedback links to the generated build,
catalog version, rules version, and review queue status, and that part-level
feedback rejects SKUs not present in the build. Browser proof must show the
post-generation feedback panel can submit and render saved feedback.

`US-016` is verified by `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`,
and Harness story verification. Unit proof covers category coverage counts and
blocking issues for missing required demo categories. Integration proof checks
`GET /catalog/health` exposes `demo_ready`, required categories, missing
categories, and per-category counts.

`US-017` is verified by `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`,
and Harness story verification. Unit proof covers recommended category counts,
thin-category warning issues, and missing categories remaining blocking.
Integration proof checks `GET /catalog/health` exposes recommended demo counts,
thin demo categories, and warning issues without making the current snapshot
not demo-ready.

`US-018` is verified by `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`,
and Harness story verification. Unit proof covers manifest parsing, relative
source paths, source merging, SKU deduplication, and override application.
Integration proof checks the real `pnpm catalog:sync` command uses
`catalog_sources.json` and still writes a validation-clean local snapshot.

`US-019` is verified by focused capture tests, a local `pnpm catalog:capture`
smoke command, `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`, and Harness
story verification. Unit proof covers local input capture, invalid payload
rejection, and manifest upsert idempotency. Integration proof uses a saved
fixture so normal validation does not depend on live Phong Vu availability.

`US-020` is verified by focused staged-source tests, `pnpm
catalog:source-report`, `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`, and
Harness story verification. Unit proof covers disabled source skipping, staged
manifest entries, current Teko listing normalization, source report counts, and
invalid staged rows. Integration proof checks broad staged captures are counted
without changing the active validation-clean snapshot.

`US-021` is verified by focused capture sanitization tests, local secret-pattern
scans, `pnpm catalog:source-report`, `pnpm catalog:sync`, `pnpm check`, `pnpm
eval:run`, and Harness trace evidence. Unit proof covers removing page-shell
environment data while preserving parseable `__NEXT_DATA__` products.

`US-022` is verified by focused manifest-subset tests, `pnpm
catalog:source-report`, `pnpm catalog:sync`, `pnpm check`, `pnpm eval:run`, and
Harness story verification. Unit proof covers `include_skus` filtering, missing
SKU failures, source-report counts, and the active snapshot reaching the
recommended two-SKU coverage for every required full-build category.

`US-039` is verified by focused catalog/API tests, `pnpm catalog:sync`,
`pnpm catalog:source-report`, `pnpm check:web`, and Harness story verification.
Unit proof covers stale snapshot warnings, pilot readiness thresholds, spec
confidence counts, production target gaps, and the real manifest reaching three
active SKUs for every required full-build category. Integration proof checks
`GET /catalog/health` exposes freshness, pilot, and production fields while the
active snapshot remains validation-clean and honest about production gaps.

`US-040` is verified by the same focused catalog/API gate, `pnpm catalog:sync`,
`pnpm catalog:source-report`, `pnpm check:web`, and Harness story verification.
Unit proof covers the real manifest reaching three cooler SKUs and three
monitor SKUs with all required validation fields present. Integration proof
checks the active snapshot remains validation-clean, `pilot_ready=true`, and
`production_ready=false` while optional category gaps are reduced but not
overclaimed.

`US-041` and `US-042` are verified by focused build-generation tests, focused
catalog/API tests, `pnpm check:web`, and Harness story verification. Unit proof
covers monitor and cooler add-on selection from the active catalog, including
monitor resolution/refresh ranking and cooler socket/TDP/case-clearance fit
notes. Integration proof checks the new `recommended_addons` artifact field and
web UI type/build path while confirming add-on SKUs stay out of selected build
items, total price, approval payloads, and the primary mock cart payload.

`US-043` is verified by focused build/catalog/API tests, `pnpm check:web`, and
Harness story verification. Unit and integration proof cover selected add-ons
being accepted only from `recommended_addons`, invalid add-on SKUs returning
422, approval selected SKUs and approval total staying PC-only, and the mock
shopping list reporting separate add-on and combined totals.

`US-044` is verified by focused upgrade planner tests, `pnpm check:web`, and
Harness story verification. Unit proof checks existing-system parsing,
unknown-field warnings, in-stock catalog GPU selection, PSU wattage pass/block
logic, PCIe connector checks, and GPU/case clearance checks. Integration proof
checks `POST /upgrade-plans/gpu` returns a typed plan from the active catalog.
Browser E2E is not required for this foundation story; the web panel is covered
by the Next.js type/build gate.

`US-045` is verified by focused upgrade planner tests, `pnpm check:web`, and
Harness story verification. Unit proof checks confirmed existing-system fields
override parsed free text before deterministic checks run. Integration proof
checks `POST /upgrade-plans/existing-system/parse` returns the typed parsed
summary, unknown fields, warnings, and confirmation next steps. Browser E2E is
not required for this foundation story; the confirmation panel is covered by the
Next.js type/build gate.

`US-046` is verified by focused orchestration and trace replay tests, `pnpm
check`, `pnpm eval:run`, and Harness story verification. Unit proof checks the
eight-agent order, intent outputs, commerce outputs, and blocked validator
behavior. Integration proof checks trace replay returns all eight events and
redacts raw intent text. Browser E2E is not required for this foundation story;
web trace labels are covered by the Next.js type/build gate.

## Never Claim Without Proof

- Do not claim real Phong Vu cart integration without a real Teko cart adapter.
- Do not claim full catalog coverage when using a curated snapshot.
- Do not claim compatibility correctness without rule tests.
- Do not claim production readiness without deployment and observability proof.
- Do not claim LLM output is authoritative for SKU, price, budget, stock,
  compatibility, approval, or cart readiness.
- Do not claim FPS, benchmark deltas, or game-specific performance numbers
  without a maintained benchmark source with source label and URL.

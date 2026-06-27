# US-015 User Feedback Loop Foundation

## Status

implemented

## Lane

normal

## Product Contract

After a build is generated, a Vietnamese customer can rate the overall build,
optionally rate individual parts, and leave free-text feedback tied to the exact
build version, catalog version, and rules version that produced the
recommendation.

Low ratings are queued as review metadata for later operator review. This is a
foundation slice for SPEC `US-11.3`; it does not add staff auth, RBAC, a full
admin console, or production analytics.

## Relevant Product Docs

- `SPEC.md` Phase 11 / `US-11.3 User Feedback Loop`
- `Data.md` grounding and catalog snapshot constraints
- `techstack.md` local persistence and observability recommendations
- `docs/product/technical-architecture.md`
- `docs/product/validation-strategy.md`
- `docs/decisions/0016-feedback-capture-before-admin-console.md`

## Acceptance Criteria

- A generated build can receive overall thumbs up/down feedback.
- Feedback can include reason tags and optional Vietnamese free text.
- Feedback can include part-level thumbs up/down for SKUs present in that exact
  build artifact.
- Part-level feedback rejects SKUs that are not in the build.
- Feedback persists in the in-memory store and local SQLite store.
- Feedback responses include build session id, build version, catalog version,
  and rules version.
- Low ratings are marked `queued` for the local review queue.
- The web app exposes the feedback controls after build generation.

## Design Notes

- API:
  - `POST /builds/{build_id}/feedback`
  - `GET /builds/{build_id}/feedback`
  - `GET /feedback/review-queue`
- Store:
  - `BuildStore.save_feedback`
  - `BuildStore.feedback_for_build`
  - `BuildStore.feedback_review_queue`
  - `SqliteBuildStore` mirrors those methods with `build_feedback`.
- UI:
  - `BuildFeedbackPanel` in `apps/web/components/build-copilot-client.tsx`
- Review queue:
  - A low overall rating or low part rating marks feedback as `queued`.
  - No staff auth, moderation workflow, or admin dashboard is added in this
    story.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-015 --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Feedback model/store validation rejects invalid part SKUs and duplicates |
| Integration | API tests cover submit/list/review queue and SQLite restart survival |
| E2E | Browser flow generates a build, submits feedback, and renders saved/queued status |
| Platform | Not required; no external provider or deployment change |
| Release | `pnpm check`; `pnpm eval:run`; `scripts/bin/harness-cli story verify US-015` |

## Harness Delta

Add customer feedback capture as the first closed-loop quality signal before
production analytics, staff tools, or Langfuse user-feedback integrations.

## Evidence

- `pnpm check` passed with Next.js build and 70 API tests, including focused
  feedback API/store tests and SQLite restart-survival proof.
- `pnpm eval:run` passed 30/30 canonical scenarios.
- `scripts/bin/harness-cli story verify US-015` passed with
  `pnpm check && pnpm eval:run`.
- Browser E2E generated a build, submitted low overall feedback plus low
  part-level GPU feedback, and rendered the saved `Đã đưa vào review queue`
  state with catalog and rules versions visible and no console errors.

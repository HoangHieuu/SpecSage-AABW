# 0016 Feedback Capture Before Admin Console

## Status

Accepted

## Context

SPEC `US-11.3` calls for users to rate builds, provide part-level feedback,
leave optional free text, and tie the feedback to session/build/catalog
versions. It also says low ratings should be surfaced for review. The product
guardrails defer staff, admin, auth, and broad enterprise operations unless a
story selects that scope.

## Decision

Implement feedback capture directly on generated builds before building a staff
or admin console. Store feedback against immutable build artifacts with:

- Build session id
- Build version
- Catalog version
- Rules version
- Overall thumbs up/down rating
- Optional reason tags and free text
- Optional part-level ratings for SKUs present in the build
- Local review queue status for low ratings

Expose a narrow local review-queue API for queued feedback records. Do not add
staff auth, RBAC, moderation workflow, analytics warehouse, or a separate admin
UI in this slice.

## Consequences

- Hackathon demos can show a closed feedback loop without expanding scope.
- Low ratings become durable local signals for later review workflows.
- Feedback remains grounded to the exact deterministic build artifact.
- A production review console, privacy policy, and analytics/export workflow
  still need later stories.

## Follow-Ups

- Add authenticated staff review once the staff/admin epic is selected.
- Add privacy policy and retention rules before collecting production customer
  free text.
- Forward feedback to Langfuse or analytics only after credentials and data
  governance are ready.

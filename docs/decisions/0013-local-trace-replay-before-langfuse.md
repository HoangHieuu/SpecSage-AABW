# 0013 Local Trace Replay Before Langfuse

Date: 2026-06-28

## Status

Accepted

## Context

`SPEC.md` Phase 11 requires agent trace and session replay, while
`techstack.md` recommends Langfuse and OpenTelemetry for production
observability. The local Harness tool registry did not report a present
`observability` capability for Langfuse MCP, and the hackathon demo still needs
inspectable agent behavior without extra credentials.

The current application already persists full build artifacts in local SQLite,
including `orchestration_trace` from `US-011`.

## Decision

Implement trace replay first as a local API/UI slice derived from persisted
build artifacts:

- `GET /builds/{build_id}/trace`
- `GET /sessions/{build_session_id}/trace`
- Redacted event payloads, tool-call labels, local latency, and deterministic
  model/runtime version metadata.
- Support-export text in the session trace response.

Do not add Langfuse, OpenTelemetry, Sentry, ClickHouse, or a new trace table in
this story.

## Alternatives Considered

1. Integrate Langfuse immediately.
2. Add a separate SQLite `agent_trace_events` table now.
3. Keep only `BuildArtifact.orchestration_trace` in the build response.

## Consequences

Positive:

- The demo can replay agent decisions without external credentials.
- Trace replay survives local API restarts because it is derived from persisted
  build artifacts.
- The API exposes a clearer support/debug surface than raw build payloads.

Tradeoffs:

- This is not production observability.
- Applied alternative builds can appear as build versions with no LangGraph
  event list because they are deterministic transformations, not graph runs.
- Real span ingestion, dashboards, eval datasets, and cross-service telemetry
  remain future work.

## Follow-Up

- Add Langfuse/OTEL spans once credentials and the MCP/tooling are available.
- Add a separate event table only if future graph branches produce events that
  should outlive or differ from build artifact payloads.

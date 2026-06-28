# 0028 Office Monitor Guidance Before Monitor SKU Recommendations

Date: 2026-06-28

## Status

Accepted

## Context

Office and student buyers often care about quiet operation, power efficiency,
basic productivity responsiveness, and one or more displays. The active catalog
snapshot can validate core PC parts, but active monitor SKUs are not curated
yet and GPU/mainboard output-port counts are not modeled in SKU specs.

The product guardrails require numeric or compatibility claims to come from
catalog, benchmark, rule, or build artifact fields. The system therefore cannot
invent HDMI/DisplayPort support or recommend monitor SKUs from staged captures.

## Decision

Use deterministic office adequacy guidance before monitor SKU recommendations:

- Parse explicit monitor counts into `BuildIntent.monitor_count`.
- Explain whether an office build uses iGPU or needs a discrete GPU because the
  selected CPU lacks iGPU.
- Add quiet/power guidance as qualitative fit notes.
- Warn with `OFFICE_MULTI_MONITOR_OUTPUTS_UNKNOWN` when a user asks for two or
  more monitors and the catalog lacks output-port data.
- Keep monitor SKU recommendations out of generated builds until monitor rows
  are promoted with verified specs.

## Alternatives Considered

1. Recommend staged monitor SKUs immediately.
2. Infer output-port support from product names or brand assumptions.
3. Ask an LLM to decide whether multiple monitors are supported.

## Consequences

Positive:

- Office guidance becomes more useful without weakening catalog grounding.
- Multi-monitor requests are captured for later curation and validation.
- iGPU office builds are not falsely treated as discrete-GPU requirements.

Tradeoffs:

- The build may still require a human check for exact HDMI/DP output support.
- Monitor-specific shopping advice remains deferred until curated monitor SKUs
  and output-port specs exist.

## Follow-Up

- Promote verified monitor SKUs with `resolution`, `refresh_rate_hz`, and input
  port fields.
- Add GPU/mainboard output-port specs before turning multi-monitor warnings
  into pass/fail compatibility checks.

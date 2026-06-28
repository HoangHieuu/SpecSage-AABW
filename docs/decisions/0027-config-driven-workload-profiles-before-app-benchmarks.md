# 0027 Config-Driven Workload Profiles Before App Benchmarks

## Status

Accepted

## Context

Phase 4 requires creator, productivity, streaming, and local LLM workload fit.
The repo does not yet have maintained application benchmark tables for Premiere,
Blender, Photoshop, OBS, or local LLM throughput. Using an LLM to infer app
performance would violate the product guardrail that numeric claims must come
from maintained data.

## Decision

Use deterministic config-driven workload profiles before app benchmark tables.
Each profile defines RAM, VRAM, CPU-thread, storage, NVMe, and NVIDIA/CUDA
preference thresholds. Generated builds expose app-fit rows with:

- Fit level.
- Bottleneck labels.
- Vietnamese requirement summary.
- Vietnamese recommendation.

The profiles are qualitative. They do not claim render time, tokens per second,
or FPS.

## Consequences

- Creator and AI guidance is more specific without inventing benchmark numbers.
- Local LLM guidance can distinguish 7B, 13B, and 70B model classes.
- Streaming workflows can warn when NVIDIA/CUDA or encoder assumptions need
  confirmation.
- Future app benchmark tables can replace or augment these thresholds without
  changing the build artifact surface.

## Follow-Ups

- Add maintained app benchmark tables only after source review.
- Promote 32GB/64GB RAM and higher-VRAM GPU catalog options before claiming
  stronger creator/AI fit.
- Add optimizer weighting from these profiles in a separate story.

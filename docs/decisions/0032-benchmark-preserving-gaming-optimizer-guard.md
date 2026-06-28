# 0032 Benchmark-Preserving Gaming Optimizer Guard

Date: 2026-06-28

## Status

Accepted

## Context

`US-029` kept gaming generation unchanged because a GPU swap can remove or
weaken source-backed benchmark warnings. `US-030` added the missing RTX 4060
Cyberpunk 2077 1440p Ultra row, which makes one active GPU swap safe for that
target, but most games and settings still lack exact rows.

## Decision

Enable gaming GPU auto-swaps only when the candidate alternative:

- is compatible and within budget
- is a GPU alternative
- has exact benchmark evidence in the generated performance profile
- has enough deterministic ranking lift to be more than a generic affordable
  swap

Non-GPU gaming alternatives remain manual. Gaming requests without candidate
benchmark evidence remain on the base generated build.

## Alternatives Considered

1. Enable all ranked gaming alternatives.
2. Enable all GPU swaps and fall back to qualitative performance warnings.
3. Keep gaming optimization disabled until a large benchmark table exists.

## Consequences

Positive:

- Cyberpunk 2077 1440p Ultra can now choose RTX 4060 while preserving
  `PERF_BELOW_TARGET`.
- Valorant and other unsupported targets do not gain unsupported FPS claims.
- The optimizer rule is deterministic and testable.

Tradeoffs:

- Some sensible gaming upgrades remain manual alternatives until benchmark
  coverage expands.
- The guard is conservative and tied to the local benchmark matrix.

## Follow-Up

- Add exact rows for more active GPU/game/resolution/preset combinations.
- Consider benchmark-aware FPS delta scoring once the matrix is large enough.

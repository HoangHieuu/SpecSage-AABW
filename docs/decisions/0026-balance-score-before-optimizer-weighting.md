# 0026 Balance Score Before Optimizer Weighting

## Status

Accepted

## Context

Phase 4 requires bottleneck and balance analysis, but changing the optimizer to
use performance weights would affect build selection and budget behavior across
many existing stories. The current need is to explain whether the selected CPU,
GPU, RAM, and SSD are balanced without weakening deterministic compatibility or
catalog grounding.

## Decision

Add a deterministic balance score to `PerformanceProfile` before using it as an
optimizer input. The score is computed from catalog-derived CPU, GPU, RAM, and
storage factors. It returns:

- Score from 0 to 100.
- Vietnamese interpretation.
- First limiting component.
- Upgrade suggestions.
- `PERF_IMBALANCE` warning when the score is severely low.

The score is explanatory only in this slice. It does not change SKU selection,
price optimization, alternatives ranking, or approval gates.

## Consequences

- Users can see a plain-language balance assessment on every generated build.
- Severe CPU/GPU/RAM/storage mismatch becomes visible through existing warning
  surfaces.
- Future optimizer weighting has a stable field to consume after separate
  validation.

## Follow-Ups

- Add optimizer weighting only after a story explicitly selects it.
- Extend factor formulas as the catalog gains richer CPU/GPU tiers.
- Add side-by-side balance comparison for alternatives in a later Phase 5
  story.

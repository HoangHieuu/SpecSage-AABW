# 0015 CI Quality Gate for Local Evals

## Status

Accepted

## Context

`US-013` created a deterministic local evaluation suite and release gate with
`pnpm check` plus `pnpm eval:run`. SPEC `US-11.2` also calls for CI to block
critical regressions. The repo did not yet have a hosted workflow, and the
current story does not require Langfuse, production deployment, or keyed cloud
services.

## Decision

Add a GitHub Actions workflow that runs on pull requests and pushes to `main`.
The workflow installs pnpm, Node.js, Python, and Agent API dev dependencies,
then runs:

- `pnpm check`
- `pnpm eval:run`

The workflow does not depend on OpenRouter, Langfuse, Vercel, PostgreSQL, or
Phong Vu/Teko credentials. LLM advisory paths remain optional and must degrade
without blocking deterministic quality checks.

## Consequences

- Critical local regression checks now have a CI path.
- Hackathon demos can reference one command sequence locally and in CI.
- CI setup remains lightweight and self-contained.
- Hosted CI proof still depends on GitHub Actions actually running after the
  workflow is pushed to a repository.

## Follow-Ups

- Add CI status evidence after a remote GitHub Actions run exists.
- Add Langfuse dataset/experiment tracking only after credentials and target
  project ownership are available.

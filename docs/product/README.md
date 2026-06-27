# Product Docs

This directory is now the living product contract for **PC Build Copilot for
Phong Vu**.

Source snapshots:

- `SPEC.md`
- `Data.md`
- `techstack.md`
- `tools.md`

Living contract files:

- `overview.md`
- `data-strategy.md`
- `technical-architecture.md`
- `validation-strategy.md`
- `coding-agent-tooling.md`

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.

Do not keep extending `SPEC.md` as the operating plan after a story is accepted.
Update the smaller contract docs instead.

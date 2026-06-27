# Coding-Agent Tooling

## Live Codex Tool Inventory

Tool search in this session found these useful live capabilities:

| Capability | Current availability | Use |
| --- | --- | --- |
| Context7 | Available | Current docs for Next.js, FastAPI, LangGraph, Pydantic AI, shadcn |
| Playwright | Available | Browser/UI verification once a web app exists |
| Vercel plugin | Available | Vercel docs, deployment/project checks when a Vercel target exists |
| OpenAI Developer Docs | Available | OpenAI API/Codex docs when OpenAI integration is selected |
| Figma plugin | Available | Design-system or UI mock work when a Figma file is provided |
| Canva plugin | Available | Presentation/visual collateral, not core implementation |
| Node REPL/browser controls | Available | Scripted browser or JS inspection when needed |

Absent or not configured in this workspace yet:

- Firecrawl MCP.
- Langfuse MCP.
- PostgreSQL MCP.
- AWS Cursor plugins.
- GitHub MCP credentials.

## Cursor MCP Defaults

The project includes `.cursor/mcp.json` with no-secret defaults:

- `context7`
- `playwright`
- `shadcn`

Do not add keyed tools to the live config until the required credentials exist.
Preferred optional additions:

- Firecrawl or TinyFish for catalog ingestion.
- Langfuse for agent trace/eval inspection.
- PostgreSQL MCP after the local database exists.
- GitHub MCP after `GITHUB_TOKEN` exists.
- AWS/Vercel tooling only when deploy targets exist.

## Harness Capabilities

Use Harness lookup before external tooling:

```bash
scripts/bin/harness-cli query tools --capability documentation-lookup --status present
scripts/bin/harness-cli query tools --capability e2e-verification --status present
scripts/bin/harness-cli query tools --capability ui-components --status present
```

If a capability is not registered or present, skip it cleanly and record the
gap in the trace when it weakens proof.

## Workflow

```text
intake -> story packet -> docs lookup -> test/proof first -> implementation
  -> story verify -> trace
```

Use Context7 whenever implementing or debugging current library APIs. Use
Playwright for browser-visible flows. Use shadcn tooling when adding UI
components. Keep the tool set small so agents choose the right tool reliably.

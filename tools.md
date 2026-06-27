# PC Build Copilot — Coding Agent Tools, Skills & Plugins

**Companion to:** [SPEC.md](./SPEC.md), [techstack.md](./techstack.md), [Data.md](./Data.md)  
**Version:** 1.0  
**Last updated:** 2026-06-27

A curated toolkit map for **PC Build Copilot** — organized by what helps a **coding agent** (Cursor) build effectively, not random plugin hoarding.

---

## Three Layers (Use All Three)

| Layer | What it does | Your project |
|-------|----------------|--------------|
| **1. Harness** | Repo contract: what to build, proof required | [repository-harness](https://github.com/hoangnb24/repository-harness) |
| **2. Skills** | Repeatable workflows (TDD, review, planning) | Superpowers, agent-skills |
| **3. MCP / plugins** | Live tools (scrape, DB, browser, docs) | Cursor `.cursor/mcp.json` |

> The **product** uses LangGraph. The **coding agent** uses harness + MCP. Don't confuse the two.

---

## Tier 1 — Install These (Highest ROI)

### 1. Repository Harness (Contract)

**[hoangnb24/repository-harness](https://github.com/hoangnb24/repository-harness)**

- `AGENTS.md`, stories, test matrix, `harness-cli`
- Same pattern as VibeGraph
- Agent works **one story** (e.g. US-002 catalog sync), not the whole SPEC at once

```bash
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh" \
  | bash -s -- --merge --refresh-agent-shim --yes
```

---

### 2. Context7 (Up-to-Date Docs)

**[upstash/context7](https://github.com/upstash/context7)** — [context7.com](https://context7.com/)

Stops the agent from hallucinating outdated Next.js / FastAPI / LangGraph APIs.

```json
"context7": {
  "command": "npx",
  "args": ["-y", "@upstash/context7-mcp"]
}
```

Use when implementing: Next.js 15, LangGraph, Pydantic AI, TanStack Query, shadcn.

---

### 3. Playwright MCP (UI + E2E)

**[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)**

- Test chat UI, Phong Vũ embed, demo flows
- Agent drives browser without manual clicking

```json
"playwright": {
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest"]
}
```

---

### 4. Firecrawl MCP (Phong Vũ Catalog)

**[firecrawl/firecrawl-mcp-server](https://github.com/firecrawl/firecrawl-mcp-server)**

- Scrape `phongvu.vn` categories / product pages
- Fits [Data.md](./Data.md) Layer 1–2 strategy
- AABW partner **TinyFish** is similar for web agents

```json
"firecrawl": {
  "command": "npx",
  "args": ["-y", "firecrawl-mcp"],
  "env": { "FIRECRAWL_API_KEY": "${env:FIRECRAWL_API_KEY}" }
}
```

**Free alternative:** custom Python script parsing `__NEXT_DATA__` (no MCP needed).

---

### 5. PostgreSQL MCP (Local Catalog DB)

Community servers such as [pgedge PostgreSQL MCP](https://www.pgedge.com/blog/lessons-learned-writing-an-mcp-server-for-postgresql) or `@modelcontextprotocol/server-postgres`.

- Agent queries `skus`, `benchmark_matrix`, session tables
- Validates catalog sync and compatibility test data

```json
"postgres": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "${env:DATABASE_URL}"]
}
```

---

### 6. Official shadcn MCP (Frontend)

**[ui.shadcn.com/docs/mcp](https://ui.shadcn.com/docs/mcp)**

- Add Button, Card, Dialog, Table with correct Tailwind v4 patterns
- Critical for split-pane chat + build table UI

```json
"shadcn": {
  "command": "npx",
  "args": ["-y", "shadcn@latest", "mcp"]
}
```

---

### 7. Langfuse MCP (Agent Observability)

**[Langfuse MCP docs](https://langfuse.com/docs/api-and-data-platform/features/mcp-server)**

- AABW workshop partner
- Agent inspects traces, prompts, eval datasets while building product agents
- Strong demo story for judges

```json
"langfuse": {
  "url": "https://cloud.langfuse.com/api/public/mcp",
  "headers": {
    "Authorization": "Basic ${env:LANGFUSE_MCP_AUTH}"
  }
}
```

Encode credentials: `echo -n "pk-lf-...:sk-lf-..." | base64`

---

## Tier 2 — Strong Complements

| Tool | Repo / source | Use for PC Build Copilot |
|------|----------------|-------------------|
| **Superpowers** | [obra/superpowers](https://github.com/obra/superpowers) | Enforce plan → TDD → review before merge |
| **agent-skills** | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Quality gates, testing, security patterns |
| **GitHub MCP** | [github/github-mcp-server](https://github.com/github/github-mcp-server) | PRs, issues, CI status |
| **AWS Core plugin** | [Cursor Marketplace](https://cursor.com/marketplace) | ECS, Bedrock, Lambda — Built with AWS track |
| **AWS Agents plugin** | Cursor Marketplace | Bedrock AgentCore, LangGraph on AWS scaffolding |
| **ChatPRD** | Cursor Marketplace | SPEC → stories → verify implementation matches requirements |
| **Subtext** | Cursor Marketplace | Verify agent work against running app |
| **Docs Canvas** | Cursor Marketplace | Render architecture / API docs in Cursor |

### Superpowers Workflow

From [blog.fsck.com](https://blog.fsck.com/2025/10/09/superpowers/):

1. **Brainstorm** before coding
2. **Write plan** → human approves
3. **TDD** — test first, then implement
4. **Subagent review** before done

Pair with harness stories: one story = one superpowers cycle.

---

## Tier 3 — Phase-Specific Tools

| PC Build Copilot phase | Best agent tools |
|------------------|------------------|
| **Catalog sync** (Data.md) | Firecrawl MCP or Python `httpx` + `__NEXT_DATA__` parser |
| **Compatibility engine** | Plain pytest + harness `story verify` (no MCP) |
| **Next.js UI** | shadcn MCP + Context7 (Next.js 15 App Router) |
| **FastAPI + LangGraph** | Context7 + [fastapi-mcp-langgraph-template](https://github.com/NicholasGoh/fastapi-mcp-langgraph-template) as reference |
| **Agent runtime** | Langfuse MCP + AWS Agents plugin |
| **Deploy** | AWS Core / Vercel (manual or plugin) |
| **Demo E2E** | Playwright MCP — "PC gaming 25 triệu" → build table appears |
| **Hackathon perks** | OpenRouter/Kimi API keys in `.env` (not MCP; agent uses via code) |

---

## Suggested `.cursor/mcp.json` for PC Build Copilot

Put in project root (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "shadcn": {
      "command": "npx",
      "args": ["-y", "shadcn@latest", "mcp"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

Add Firecrawl + Langfuse when you have API keys.

**Keep 5–7 MCP servers max** — too many slows the agent and causes wrong tool picks.

### Discovery links

- [cursor.directory](https://cursor.directory)
- [Cursor Marketplace](https://cursor.com/marketplace)
- [awesome-agent-harness](https://github.com/Picrew/awesome-agent-harness)
- [Cursor MCP docs](https://cursor.com/docs/mcp)

---

## Register Tools in repository-harness

From [TOOL_REGISTRY.md](https://github.com/hoangnb24/repository-harness/blob/main/docs/TOOL_REGISTRY.md):

```bash
scripts/bin/harness-cli tool register --name context7 --kind mcp \
  --capability documentation-lookup --scan ".cursor/mcp.json" \
  --command "mcp:context7" --description "Up-to-date framework docs" \
  --responsibility Verification

scripts/bin/harness-cli tool register --name playwright --kind mcp \
  --capability e2e-verification --scan ".cursor/mcp.json" \
  --command "mcp:playwright" --description "Browser E2E for demo flows" \
  --responsibility Verification

scripts/bin/harness-cli tool register --name firecrawl --kind mcp \
  --capability catalog-ingestion --scan ".cursor/mcp.json" \
  --command "mcp:firecrawl" --description "Scrape Phong Vũ product pages" \
  --responsibility Verification

scripts/bin/harness-cli tool register --name shadcn --kind mcp \
  --capability ui-components --scan ".cursor/mcp.json" \
  --command "mcp:shadcn" --description "shadcn/ui component registry" \
  --responsibility Verification

scripts/bin/harness-cli tool register --name langfuse --kind mcp \
  --capability observability --scan ".cursor/mcp.json" \
  --command "mcp:langfuse" --description "Agent trace and eval inspection" \
  --responsibility Verification

scripts/bin/harness-cli tool check
scripts/bin/harness-cli query tools --summary
```

Before each story, agent runs:

```bash
scripts/bin/harness-cli query tools --capability documentation-lookup --status present
```

### Recommended capability vocabulary

```
documentation-lookup · catalog-ingestion · e2e-verification · ui-components
observability · deploy-verification · security-scan · impact-analysis
```

---

## Skills to Add (Not MCP)

| Skill pack | When to use |
|------------|-------------|
| **Superpowers** | Every feature — plan, TDD, review |
| **repository-harness** | Every session — stories, proof, traces |
| **implement** (`/implement`) | Larger features with multi-reviewer loop |
| **review** (`/review`) | Before demo day |
| **design** (`/design`) | Only if architecture changes |

### Cursor workflow rules (adapt from Superpowers)

Copy into `.cursor/rules/` or `AGENTS.md`:

1. Read story
2. Plan
3. Test
4. Implement
5. `harness-cli story verify`
6. `harness-cli trace`

---

## AABW Perks → Coding Agent Usage

| Partner | How coding agent uses it |
|---------|-------------------------|
| **Langfuse** | MCP + trace product agents during dev |
| **AWS** | Cursor AWS Core/Agents plugins for deploy |
| **Kimi / Qwen** | API keys in `.env`; agent writes integration code |
| **TinyFish / Bright Data** | Catalog scraping if Firecrawl blocked |
| **TRAE / Cursor** | Daily IDE |
| **ClickHouse** | Later — analytics pipeline, not day-1 coding |
| **Notion** | SPEC/story drafts for humans; optional |

---

## What NOT to Install

| Skip | Why |
|------|-----|
| 15+ MCP servers | Tool noise, slow agent, wrong picks |
| CrewAI / AutoGen for **building** | Product-runtime frameworks, not coding harness |
| Generic "AI chatbot" templates | Wrong architecture for agentic commerce |
| Figma / Slack / Linear MCP | Unless you actually use them for this hackathon |
| LangGraph as coding MCP | LangGraph is what you **implement**, not what guides the coder |

---

## Effective Agent Workflow

```
1. harness-cli intake + story pick (US-00X)
2. context7 → fetch docs for stack in that story
3. implement with TDD (superpowers-style)
4. playwright → verify UI flow
5. harness-cli story verify US-00X
6. harness-cli trace --summary "..."
7. next story
```

### Prompt template for Cursor

```
Read AGENTS.md, docs/stories/US-002-catalog-sync.md, Data.md.
Use Context7 for FastAPI docs. Use Firecrawl only for catalog ingestion.
Do not touch UI stories. Run harness-cli story verify US-002 when done.
```

---

## Priority Summary

| Priority | Tool |
|----------|------|
| **Must** | repository-harness, Context7, shadcn MCP, Playwright MCP |
| **Should** | Firecrawl (or custom scraper), Langfuse MCP, Superpowers workflow |
| **Nice** | AWS plugins, GitHub MCP, ChatPRD, Subtext, PostgreSQL MCP |
| **Skip for now** | 10+ random MCPs from awesome lists |

---

## References

- [repository-harness](https://github.com/hoangnb24/repository-harness)
- [Context7](https://github.com/upstash/context7)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
- [Firecrawl MCP](https://github.com/firecrawl/firecrawl-mcp-server)
- [shadcn MCP](https://ui.shadcn.com/docs/mcp)
- [Langfuse MCP](https://langfuse.com/docs/api-and-data-platform/features/mcp-server)
- [Superpowers](https://github.com/obra/superpowers)
- [awesome-agent-harness](https://github.com/Picrew/awesome-agent-harness)
- [Cursor Marketplace](https://cursor.com/marketplace)

---

*PC Build Copilot — Coding Agent Tools — Phong Vũ Retail Track*

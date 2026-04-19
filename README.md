# TechStackLens

**Full-stack AI tooling audit with bidirectional wiki sync.**

Periodic health checks for your entire AI/dev stack — LLM providers, databases, deployment, dependencies, SaaS services — with PDF/Markdown/HTML reports.

Built for the [CARNET Intelligence Platform](https://github.com/BartWScout), forked from [claude-code-optimizer](https://github.com/ronchestermusic/claude-code-optimizer) and expanded to cover the full technology stack.

## What It Does

TechStackLens is a Claude Code skill that runs a 7-step audit pipeline:

| Step | What happens |
|------|-------------|
| **0. Profile** | Confirms your role, tech level, audit scope, and report style |
| **1. Audit** | Deep scan across 7 categories (Claude Code, SaaS providers, databases, deployment, cross-tool configs, dependencies, env vars) |
| **2. Research** | Parallel search across 5-7 high-signal sources for new tools |
| **3. Filter** | Overlap detection, profile filtering, diff against last run |
| **3.5. Safety** | Trust & supply-chain screening on every candidate |
| **4. Ask** | Two-confirmation flow before any changes |
| **5. Install** | Approved tools only, with post-install verification |
| **6. Report** | PDF + Markdown + HTML dashboard |

## Quick Start

```bash
# Clone the skill
git clone https://github.com/BartWScout/tech-stack-lens ~/.claude/skills/tech-stack-lens

# Run it
# In Claude Code, type: /tech-stack-lens
```

## Audit Scope

Choose what to audit in Step 0:

| Scope | What it covers |
|-------|---------------|
| `full stack` | All 7 categories below |
| `claude-code only` | Original optimizer behavior — plugins, skills, MCP servers |
| `saas providers` | API key health, provider connectivity |
| `databases` | Supabase, Notion, Dataverse status |
| `deployment` | n8n, Vercel, DigitalOcean health |
| `dependencies` | Outdated packages, security vulnerabilities |
| `custom` | Pick any combination |

## Reports

Three output formats, three PDF styles:

| Format | Output |
|--------|--------|
| **PDF** | `~/Desktop/tech-stack-lens-YYYY-MM-DD.pdf` |
| **Markdown** | `~/Desktop/tech-stack-lens-YYYY-MM-DD.md` (Obsidian-compatible) |
| **HTML** | `~/Desktop/tech-stack-lens-YYYY-MM-DD.html` (self-contained dashboard) |

PDF styles: **warm cream editorial** (default), **plain minimal**, or **colorful**.

## Configuration

### `config/default-profile.yaml`

Defines which providers to audit, their expected env keys, deployment targets, and report defaults. Customize for your team.

### `config/sources.yaml`

Registry of research sources with priority, query patterns, and health status. Add your own sources or disable broken ones.

## Safety Model

Two-confirmation flow for all installations. Trust screening on every candidate. Full threat model in [SAFETY.md](./SAFETY.md).

- Never installs without explicit approval
- Never prints API key values
- Scans for prompt injection in fetched content
- Post-install verification on skills

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | Current | Full-stack audit + multi-format reports |
| **Phase 2** | Planned | Wiki write-path (auto-generate provider notes in scouting-llm-wiki) |
| **Phase 3** | Planned | Wiki read-path (leverage existing wiki intelligence before researching) |
| **Phase 4** | Planned | Freshness tracking + cross-tool awareness |
| **Phase 5** | Planned | Documentation + samples + team onboarding |

## Credits

Forked from [Stackshift — Claude Code Optimizer](https://github.com/ronchestermusic/claude-code-optimizer) by [@ronchestermusic](https://github.com/ronchestermusic). Extended with full-stack auditing, multi-format reports, and wiki integration for the CARNET team.

## License

MIT — See [LICENSE](./LICENSE) for details.

# Architecture

## Pipeline Overview

```
User invokes /tech-stack-lens
         │
         ▼
┌─────────────────────┐
│  Step 0: Profile     │  AskUserQuestion x5
│  (use case, scope,   │  → working profile block
│   tech level, style) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 1: Audit       │  7 categories in parallel
│  (Claude Code, SaaS, │  → snapshot summary
│   DBs, deploy, deps) │  → memory reconciliation
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 1.5: Wiki      │  Read provider profiles,
│  Prefetch            │  comparisons, ADRs
│  (read-path)         │  → freshness dashboard
│                      │  → context block for Step 2-3
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 2: Research    │  5-7 sources in parallel
│  (budget-capped)     │  → candidate list
│                      │  Skips wiki-current providers
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 3: Filter      │  Overlap → profile → diff
│  + Step 3.5: Safety  │  Trust screening per candidate
│                      │  → numbered recommendation table
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 4: Ask         │  Two-confirmation flow
│  (by number)         │  → approved list
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 5: Install /   │  Plugins, MCP, skills, SaaS
│  Configure           │  → post-install verification
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 6: Reports     │  PDF + Markdown + HTML
│                      │  → ~/Desktop/tech-stack-lens-*
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Step 7: Wiki Sync   │  Provider notes, comparisons
│  (write-path)        │  log.md, indices
│                      │  → scouting-llm-wiki updates
└─────────────────────┘
```

## Tool Calls by Step

| Step | Tools Used | Purpose |
|------|-----------|---------|
| 0 | AskUserQuestion | Profile questions |
| 1.1 | Bash (jq, claude mcp list, ls) | Claude Code audit |
| 1.2 | Bash (printenv, curl) | SaaS provider health |
| 1.3 | MCP (Supabase, Notion) | Database connectivity |
| 1.4 | Bash (curl), MCP (Vercel) | Deployment status |
| 1.5 | Read (wiki files), Bash (ls, grep) | Wiki intelligence |
| 1.6 | Bash (pip, npm) | Dependency audit |
| 1.7 | Bash (printenv) | Env var presence |
| 2 | WebSearch, WebFetch | Research sources |
| 3 | (analysis, no tools) | Filter and compare |
| 3.5 | (analysis, no tools) | Trust screening |
| 4 | AskUserQuestion | User picks |
| 5 | Bash (claude plugin install, claude mcp add, git clone) | Installation |
| 6 | Bash (cat, Chrome headless), Write | Report generation |
| 7 | Read, Write, Edit | Wiki sync |

## Data Flow

```
config/default-profile.yaml
         │
         ├──► Step 1: provider list, deployment targets
         ├──► Step 1.5: wiki path
         └──► Step 7: wiki path, template selection

config/sources.yaml
         │
         └──► Step 2: research source registry

templates/pdf-*.html
         │
         └──► Step 6: PDF styling

templates/wiki-*.md
         │
         └──► Step 7: wiki note generation

scouting-llm-wiki/
         │
         ├──► Step 1.5 reads: 03-providers/, 06-comparisons/, 07-decisions/
         └──► Step 7 writes: 03-providers/, 06-comparisons/, log.md, indices
```

## File Structure

```
tech-stack-lens/
├── SKILL.md                    # Core skill (Claude Code reads this)
├── SAFETY.md                   # Threat model and trust signals
├── README.md                   # Project overview
├── LICENSE                     # MIT
├── config/
│   ├── default-profile.yaml    # Team defaults, provider registry
│   └── sources.yaml            # Research source registry
├── templates/
│   ├── pdf-cream.html          # Warm cream editorial PDF
│   ├── pdf-minimal.html        # Plain minimal PDF
│   ├── pdf-colorful.html       # Colorful PDF
│   ├── wiki-provider.md        # Provider note template
│   └── wiki-comparison.md      # Comparison note template
├── docs/
│   ├── ARCHITECTURE.md         # This file
│   ├── CUSTOMIZATION.md        # How to customize
│   └── WIKI-INTEGRATION.md     # Bidirectional sync protocol
└── examples/                   # Sample reports (generated)
```

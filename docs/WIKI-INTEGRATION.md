# Wiki Integration Protocol

TechStackLens has bidirectional integration with [scouting-llm-wiki](https://github.com/BartWScout/scouting-llm-wiki), an Obsidian vault following Karpathy-style LLM wiki patterns.

## Architecture

```
TechStackLens                          scouting-llm-wiki
─────────────                          ─────────────────
Step 1 (Audit)                         
     │                                 
Step 1.5 (Read) ◄──────────────────── 03-providers/*.md
     │           ◄──────────────────── 06-comparisons/*.md
     │           ◄──────────────────── 07-decisions/*.md
     │                                 
Step 2 (Research)                      
  [skips recently-verified providers]  
     │                                 
Steps 3-6 (Filter, Install, Report)   
     │                                 
Step 7 (Write) ────────────────────► 03-providers/provider-<name>.md
               ────────────────────► 06-comparisons/comparison-<scope>.md
               ────────────────────► log.md (append-only)
               ────────────────────► providers-index.md
               ────────────────────► sources-index.md
```

## Read-Path (Step 1.5)

### What gets read

| Wiki path | What's extracted | How it's used |
|-----------|-----------------|---------------|
| `03-providers/provider-*.md` | status, last_verified, confidence, free_tier_summary, mcp_support, TLDR | Skip recently-verified in Step 2, use as baseline in Step 3 |
| `06-comparisons/comparison-*.md` | verdict, criteria matrix, last_verified | Cite instead of re-deriving in Step 3 |
| `07-decisions/ADR-*.md` | Decision context, constraints | Inform recommendations in Step 3 |
| `index.md` | Wiki structure | Navigate to relevant files |

### Staleness classification

| Age | Classification | Research action |
|-----|---------------|-----------------|
| <14 days | Current | Skip (save budget) |
| 14-30 days | Aging | Include, lower priority |
| >30 days | Stale | Prioritize, flag for re-verification |
| No date | Missing | Treat as stale |

### Freshness dashboard

After reading all provider profiles, display a visual dashboard showing counts per classification. Offer re-verification of stale profiles via targeted WebSearch.

## Write-Path (Step 7)

### What gets written

| Action | Target | Condition |
|--------|--------|-----------|
| Create provider note | `03-providers/provider-<name>.md` | Provider recommended as INSTALL/CONFIGURE and no wiki profile exists |
| Update provider note | `03-providers/provider-<name>.md` | Provider re-verified and wiki profile exists |
| Create comparison | `06-comparisons/comparison-<scope>.md` | 2+ providers in same category researched, no comparison exists |
| Update comparison | `06-comparisons/comparison-<scope>.md` | New data for existing comparison |
| Append log | `log.md` | Always (after any wiki write) |
| Update index | `providers-index.md` | After creating new provider note |
| Update source index | `01-sources/sources-index.md` | After gathering new source evidence |

### Template compliance

Wiki writes use exact copies of the wiki's own templates:
- `templates/wiki-provider.md` = `10-templates/template-provider-profile.md`
- `templates/wiki-comparison.md` = `10-templates/template-comparison-note.md`

Dataview dashboards in the wiki depend on exact frontmatter field names. Every generated note must include all required fields.

### Safety constraints

1. **Two confirmations** before any wiki write (same model as tool installation)
2. **Never overwrite** existing content without explicit approval
3. **Append-only** to log.md
4. **Never modify** files in `01-sources/` (except frontmatter enrichment)
5. **Diff preview** shown to user before each write
6. **Prefer updates** over creating duplicates

### Frontmatter requirements

Every provider note must include:

```yaml
type: provider
provider: <name>
category: <category>
status: active|experimental|deprecated
free_tier_summary: <text>
api_access: yes|partial|no
mcp_support: native|custom|none
source_refs: [<urls>]
source_dates: [<dates>]
last_verified: YYYY-MM-DD
confidence: low|medium|high
review_cycle_days: 14
tags: [provider, tech-stack-lens-generated]
```

### Log format

```markdown
## [YYYY-MM-DD] tech-stack-lens | audit

- Scope: <audit scope>
- Providers audited: <count>
- New notes created: <list>
- Notes updated: <list>
- Comparisons: <list or "none">
- Report: ~/Desktop/tech-stack-lens-YYYY-MM-DD.pdf
```

## Configuration

Wiki path is set in `config/default-profile.yaml`:

```yaml
wiki_path: /Users/bartek/projects/scouting-llm-wiki
```

If the path doesn't exist, both read and write paths are skipped silently.

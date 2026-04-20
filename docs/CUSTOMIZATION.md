# Customization Guide

## Adding a New Provider

Edit `config/default-profile.yaml` and add an entry under `providers`:

```yaml
providers:
  - name: my-provider           # lowercase, hyphenated
    env_key: MY_PROVIDER_KEY    # env var name (value never stored here)
    category: enrichment        # one of: llm, web-scraping, enrichment,
                                # email-discovery, communication, database,
                                # infrastructure, auth, dev-tooling,
                                # research, workspace, knowledge
```

The provider will automatically be included in:
- **Step 1** (Category 2): API key presence check
- **Step 1.5**: Wiki profile lookup
- **Step 7**: Wiki note generation if recommended

## Adding a Health Check

Add a `health_check` field to the provider entry:

```yaml
  - name: my-provider
    env_key: MY_PROVIDER_KEY
    category: enrichment
    health_check: https://api.my-provider.com/v1/health
```

Step 1 will `curl` this URL with a 5-second timeout and report the HTTP status.

## Changing Audit Scope

Edit `config/default-profile.yaml`:

```yaml
audit_scope:
  claude_code: true       # Category 1: plugins, skills, MCP
  saas_providers: true    # Category 2: API key health
  databases: true         # Category 3: Supabase, Notion, Dataverse
  deployment: true        # Category 4: n8n, Vercel, DigitalOcean
  cross_tool: true        # Category 5: rulesync, config drift
  dependencies: true      # Category 6: pip/npm outdated, vulnerabilities
  env_vars: true          # Category 7: .env.shared presence check
```

Set any to `false` to skip that category. The user can also override at runtime via Step 0's "Audit scope" question.

## Changing the Wiki Path

```yaml
wiki_path: /path/to/your/obsidian/vault
```

Set to empty string or remove to disable wiki integration entirely.

## Adding Research Sources

Edit `config/sources.yaml`:

```yaml
sources:
  - name: My Custom Source
    priority: 9              # lower = higher priority (checked first)
    method: WebSearch        # WebSearch or WebFetch
    query: 'my search query' # for WebSearch
    # url: https://...       # for WebFetch
    signal: Description of signal quality
    status: active           # active or broken
    last_tested: 2026-04-20
    notes: Optional notes
```

Budget cap is 5-7 sources per run. Sources are checked in priority order.

## Changing PDF Style

Three built-in presets in `config/default-profile.yaml`:

```yaml
pdf_style: cream    # warm cream editorial (default)
# pdf_style: minimal  # plain, no accent fonts
# pdf_style: colorful # saturated palette, gradient accents
```

### Customizing a PDF Template

Edit the HTML files in `templates/`:

- `templates/pdf-cream.html` — Playfair Display + Source Serif 4 + IBM Plex Mono
- `templates/pdf-minimal.html` — System sans-serif + system mono
- `templates/pdf-colorful.html` — Playfair Display + Inter + JetBrains Mono

Templates use `{{PLACEHOLDER}}` tokens replaced at runtime:
- `{{DATE}}` — report date
- `{{PROFILE_SUMMARY}}` — one-line user profile
- `{{HEADLINE}}` — what changed this run
- `{{CONTENT}}` — all report sections (HTML)

## Changing Report Defaults

```yaml
report_formats: [pdf, markdown]  # any combination of: pdf, markdown, html
```

## Changing Staleness Thresholds

```yaml
stale_threshold_days: 30  # days before a wiki profile is flagged as stale
```

Step 1.5 uses this to classify profiles:
- Current: < 14 days
- Aging: 14 days to threshold
- Stale: > threshold

## Adding Deployment Targets

```yaml
deployment:
  n8n:
    health_url: https://carnetscout.app/healthz
    host: 159.89.23.221
  vercel:
    method: mcp
  my-server:
    health_url: https://my-server.com/health
    host: 10.0.0.1       # optional SSH check target
```

## Team Profiles

To create a profile for a different team, copy `config/default-profile.yaml` to a new file (e.g., `config/research-team.yaml`) and modify the provider list and scope. Reference it at runtime by updating the wiki path and provider list.

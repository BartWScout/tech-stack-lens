# Tests

Regression tests for tech-stack-lens scripts.

## Run

```bash
cd ~/projects/tools/tech-stack-lens
python3 -m pytest tests/ -v
```

Requires `pytest` (no other third-party deps — scripts use only stdlib).

## Fixtures

- `fixtures/flat-wiki/` — mimics a wiki where `provider-*.md` sits directly under `03-providers/`
- `fixtures/layered-wiki/` — mimics the real CARNET wiki layout: files under `03-providers/_layers/layer-N-*/` and sibling `04-providers-monitoring/`

A failing test in `test_wiki_scan.py` means the pre-2026-04-21 bug is back: flat-glob assumptions that miss layered files.

"""Regression tests for the layered-wiki rglob fix.

These fixtures mirror the two layouts the skill sees in the wild:

- flat-wiki: provider-*.md lives directly under 03-providers/
- layered-wiki: provider-*.md lives under 03-providers/_layers/layer-N-*/ and
  under sibling directories like 04-providers-monitoring/

The scan must discover every provider file in both layouts. A regression here
means the pre-2026-04-21 bug is back.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import _wiki
from wiki_scan import scan


def test_flat_wiki_discovers_all_providers(flat_wiki: Path):
    result = scan(flat_wiki)
    names = {p["name"] for p in result["providers"]}
    assert result["total"] == 2
    assert names == {"Gamma", "Delta"}


def test_layered_wiki_discovers_providers_across_subdirs(layered_wiki: Path):
    result = scan(layered_wiki)
    names = {p["name"] for p in result["providers"]}
    assert result["total"] == 3
    assert names == {"Alpha", "Beta", "Epsilon"}


def test_layered_wiki_infers_category_from_layer(layered_wiki: Path):
    result = scan(layered_wiki)
    by_name = {p["name"]: p for p in result["providers"]}
    assert by_name["Alpha"]["category"] == "discovery"
    assert by_name["Beta"]["category"] == "enrichment"


def test_orphan_file_is_missing_date_bucket(layered_wiki: Path):
    result = scan(layered_wiki)
    by_name = {p["name"]: p for p in result["providers"]}
    assert by_name["Epsilon"]["has_frontmatter"] is False
    assert by_name["Epsilon"]["bucket"] == "missing-date"


def test_classify_freshness_buckets():
    provider_current = _wiki.Provider(path=Path("x"), name="x", has_frontmatter=True, frontmatter={"last_verified": "2026-04-20"})
    provider_stale = _wiki.Provider(path=Path("x"), name="x", has_frontmatter=True, frontmatter={"last_verified": "2026-01-01"})
    provider_missing = _wiki.Provider(path=Path("x"), name="x", has_frontmatter=False, frontmatter={})
    today = date(2026, 4, 21)
    assert _wiki.classify_freshness(provider_current, today=today) == "current"
    assert _wiki.classify_freshness(provider_stale, today=today) == "stale"
    assert _wiki.classify_freshness(provider_missing, today=today) == "missing-date"


def test_render_frontmatter_round_trip():
    fields = {
        "type": "provider",
        "provider": "Test",
        "source_refs": ["https://a.example", "https://b.example"],
        "empty_list": [],
        "tags": ["provider", "test"],
    }
    rendered = _wiki.render_frontmatter(fields)
    assert rendered.startswith("---\n")
    assert rendered.rstrip().endswith("---")
    parsed, _ = _wiki.split_frontmatter(rendered + "body\n")
    assert parsed["type"] == "provider"
    assert parsed["provider"] == "Test"
    assert parsed["source_refs"] == ["https://a.example", "https://b.example"]
    assert parsed["empty_list"] == []
    assert parsed["tags"] == ["provider", "test"]

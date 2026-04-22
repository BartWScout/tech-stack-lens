"""Tests for backfill_last_verified.py — update last_verified on wiki provider files.

Covers:
  - dry-run never writes
  - apply updates exactly the last_verified line, leaves everything else intact
  - --all-stale selects only providers classified as stale, skips current ones
  - --providers all touches every file that has frontmatter
  - --providers <name> matches by display name AND by filename stem
  - --date YYYY-MM-DD writes the specified date, not today
  - files without frontmatter are silently skipped
  - no matching names → zero updates, clean exit
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import _wiki
from backfill_last_verified import update_last_verified


# ---------------------------------------------------------------------------
# Shared fixture — a mini wiki with controlled freshness states
# ---------------------------------------------------------------------------

@pytest.fixture
def backfill_wiki(tmp_path: Path) -> Path:
    """Wiki with a stale provider, a fresh provider, and an orphan (no frontmatter)."""
    today = date.today()
    stale_date = (today - timedelta(days=60)).isoformat()   # always stale (>30d)
    fresh_date = (today - timedelta(days=5)).isoformat()    # always current (<14d)

    wiki = tmp_path / "wiki"
    providers = wiki / "03-providers"
    providers.mkdir(parents=True)

    (providers / "provider-stale.md").write_text(
        f"---\ntype: provider\nprovider: Stale Provider\ncategory: enrichment\n"
        f"last_verified: {stale_date}\nconfidence: medium\n---\n\n# Stale Provider\n",
        encoding="utf-8",
    )
    (providers / "provider-fresh.md").write_text(
        f"---\ntype: provider\nprovider: Fresh Provider\ncategory: enrichment\n"
        f"last_verified: {fresh_date}\nconfidence: medium\n---\n\n# Fresh Provider\n",
        encoding="utf-8",
    )
    (providers / "provider-nofm.md").write_text(
        "# No Frontmatter\nThis file has no frontmatter block.\n",
        encoding="utf-8",
    )
    return wiki


# ---------------------------------------------------------------------------
# update_last_verified — unit tests for the core rewrite function
# ---------------------------------------------------------------------------

def test_dry_run_does_not_write(backfill_wiki: Path):
    path = backfill_wiki / "03-providers" / "provider-stale.md"
    original = path.read_text()
    changed = update_last_verified(path, "2026-04-22", apply=False)
    assert changed
    assert path.read_text() == original, "dry-run must not touch the file"


def test_apply_rewrites_last_verified_only(backfill_wiki: Path):
    path = backfill_wiki / "03-providers" / "provider-stale.md"
    original = path.read_text()
    changed = update_last_verified(path, "2026-04-22", apply=True)
    assert changed

    text = path.read_text()
    assert "last_verified: 2026-04-22" in text

    # Every other line must be unchanged
    original_lines = [l for l in original.splitlines() if not l.startswith("last_verified:")]
    new_lines = [l for l in text.splitlines() if not l.startswith("last_verified:")]
    assert original_lines == new_lines


def test_apply_writes_custom_date(backfill_wiki: Path):
    path = backfill_wiki / "03-providers" / "provider-stale.md"
    update_last_verified(path, "2025-12-31", apply=True)
    assert "last_verified: 2025-12-31" in path.read_text()


def test_no_last_verified_field_returns_false(tmp_path: Path):
    f = tmp_path / "provider-missing.md"
    f.write_text("---\ntype: provider\nprovider: Missing\n---\nbody\n", encoding="utf-8")
    changed = update_last_verified(f, "2026-04-22", apply=True)
    assert not changed


# ---------------------------------------------------------------------------
# Integration via main() — tests the full CLI argument flow
# ---------------------------------------------------------------------------

def _run_main(args: list[str]) -> int:
    """Call backfill_last_verified.main() with the given argv."""
    import backfill_last_verified
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = ["backfill_last_verified.py"] + args
    try:
        return backfill_last_verified.main()
    finally:
        _sys.argv = old_argv


def test_main_providers_by_name_apply(backfill_wiki: Path):
    stale_path = backfill_wiki / "03-providers" / "provider-stale.md"
    fresh_path = backfill_wiki / "03-providers" / "provider-fresh.md"
    fresh_before = fresh_path.read_text()

    ret = _run_main(["--wiki", str(backfill_wiki), "--providers", "stale provider", "--date", "2026-04-22", "--apply"])
    assert ret == 0
    assert "last_verified: 2026-04-22" in stale_path.read_text()
    assert fresh_path.read_text() == fresh_before, "fresh provider must not be touched"


def test_main_providers_match_by_stem(backfill_wiki: Path):
    """'stale' (bare stem) should match provider-stale.md."""
    stale_path = backfill_wiki / "03-providers" / "provider-stale.md"
    ret = _run_main(["--wiki", str(backfill_wiki), "--providers", "stale", "--date", "2026-04-22", "--apply"])
    assert ret == 0
    assert "last_verified: 2026-04-22" in stale_path.read_text()


def test_main_all_stale_skips_fresh(backfill_wiki: Path):
    fresh_path = backfill_wiki / "03-providers" / "provider-fresh.md"
    fresh_before = fresh_path.read_text()

    ret = _run_main(["--wiki", str(backfill_wiki), "--all-stale", "--date", "2026-04-22", "--apply"])
    assert ret == 0
    assert fresh_path.read_text() == fresh_before, "--all-stale must not touch current files"


def test_main_all_stale_updates_stale(backfill_wiki: Path):
    stale_path = backfill_wiki / "03-providers" / "provider-stale.md"
    ret = _run_main(["--wiki", str(backfill_wiki), "--all-stale", "--date", "2026-04-22", "--apply"])
    assert ret == 0
    assert "last_verified: 2026-04-22" in stale_path.read_text()


def test_main_providers_all_updates_all_with_frontmatter(backfill_wiki: Path):
    stale_path = backfill_wiki / "03-providers" / "provider-stale.md"
    fresh_path = backfill_wiki / "03-providers" / "provider-fresh.md"
    nofm_path = backfill_wiki / "03-providers" / "provider-nofm.md"
    nofm_before = nofm_path.read_text()

    ret = _run_main(["--wiki", str(backfill_wiki), "--providers", "all", "--date", "2026-04-22", "--apply"])
    assert ret == 0
    assert "last_verified: 2026-04-22" in stale_path.read_text()
    assert "last_verified: 2026-04-22" in fresh_path.read_text()
    assert nofm_path.read_text() == nofm_before, "no-frontmatter file must never be touched"


def test_main_no_match_exits_zero(backfill_wiki: Path, capsys):
    ret = _run_main(["--wiki", str(backfill_wiki), "--providers", "nonexistent", "--dry-run"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "No matching" in out


def test_main_dry_run_writes_nothing(backfill_wiki: Path):
    stale_path = backfill_wiki / "03-providers" / "provider-stale.md"
    before = stale_path.read_text()
    _run_main(["--wiki", str(backfill_wiki), "--all-stale", "--date", "2026-04-22", "--dry-run"])
    assert stale_path.read_text() == before


# ---------------------------------------------------------------------------
# _parse_simple_yaml: any indentation depth for block lists (fix 2)
# ---------------------------------------------------------------------------

def test_block_list_with_4space_indent():
    """4-space indented list items must be parsed (not silently dropped)."""
    fm, _ = _wiki.split_frontmatter(
        "---\ntype: provider\ntags:\n    - provider\n    - test\n---\nbody\n"
    )
    assert fm is not None
    assert fm["tags"] == ["provider", "test"]


def test_block_list_with_1space_indent():
    """1-space indented list items must also be parsed."""
    fm, _ = _wiki.split_frontmatter(
        "---\ntype: provider\ntags:\n - provider\n - test\n---\nbody\n"
    )
    assert fm is not None
    assert fm["tags"] == ["provider", "test"]


def test_block_list_mixed_indent_uses_each_item():
    """Mixed indent within the same list — each item accepted regardless of depth."""
    fm, _ = _wiki.split_frontmatter(
        "---\ntype: provider\ntags:\n  - a\n    - b\n---\nbody\n"
    )
    assert fm is not None
    assert fm["tags"] == ["a", "b"]

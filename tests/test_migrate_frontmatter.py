"""Tests for migrate_frontmatter.py — the script that writes provider files.

Covers the three code paths:
  - inject: file has no frontmatter → full block is inserted
  - normalize: file has frontmatter with wrong `type:` → only that line is rewritten
  - skip-non-provider: file has a NON_PROVIDER_TYPES type → left completely alone
  - skip-valid: file already has `type: provider` → untouched

dry-run must never write, apply must write exactly the right change.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import _wiki
from migrate_frontmatter import NON_PROVIDER_TYPES, migrate_file, normalize_type_in_place


FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "migrate"


@pytest.fixture
def tmp_migrate(tmp_path: Path) -> Path:
    """Copy migrate fixtures into a temp dir so tests can write without polluting the repo."""
    dest = tmp_path / "migrate"
    shutil.copytree(FIXTURE_DIR, dest)
    return dest


# ---------------------------------------------------------------------------
# Dry-run: migrate_file returns the expected action without touching the file
# ---------------------------------------------------------------------------


def test_dry_run_inject_returns_would_inject(tmp_migrate: Path):
    path = tmp_migrate / "provider-orphan.md"
    before = path.read_text()
    action, note = migrate_file(path, apply=False)
    assert action == "would-inject"
    assert path.read_text() == before, "dry-run must not modify the file"


def test_dry_run_normalize_returns_would_normalize(tmp_migrate: Path):
    path = tmp_migrate / "provider-wrong-type.md"
    before = path.read_text()
    action, note = migrate_file(path, apply=False)
    assert action == "would-normalize"
    assert "Wrong Type" in note or "enrichment-tool" in note
    assert path.read_text() == before, "dry-run must not modify the file"


def test_dry_run_catalog_returns_skip_non_provider(tmp_migrate: Path):
    path = tmp_migrate / "provider-catalog.md"
    before = path.read_text()
    action, note = migrate_file(path, apply=False)
    assert action == "skip-non-provider"
    assert "provider-catalog" in note
    assert path.read_text() == before


def test_dry_run_valid_returns_skip_valid(tmp_migrate: Path):
    path = tmp_migrate / "provider-valid.md"
    before = path.read_text()
    action, note = migrate_file(path, apply=False)
    assert action == "skip-valid"
    assert path.read_text() == before


# ---------------------------------------------------------------------------
# Apply: files are actually modified correctly
# ---------------------------------------------------------------------------


def test_apply_inject_adds_frontmatter(tmp_migrate: Path):
    path = tmp_migrate / "provider-orphan.md"
    action, _ = migrate_file(path, apply=True)
    assert action == "injected"

    text = path.read_text()
    assert text.startswith("---\n")
    fm, body = _wiki.split_frontmatter(text)
    assert fm is not None
    assert fm["type"] == "provider"
    assert fm["status"] == "active"
    assert isinstance(fm["source_refs"], list)
    assert "Orphan Provider" in body


def test_apply_normalize_rewrites_only_type_line(tmp_migrate: Path):
    path = tmp_migrate / "provider-wrong-type.md"
    original = path.read_text()
    action, _ = migrate_file(path, apply=True)
    assert action == "normalized"

    text = path.read_text()
    fm, _ = _wiki.split_frontmatter(text)
    assert fm is not None
    assert fm["type"] == "provider"
    # All other keys must be unchanged
    assert fm["provider"] == "Wrong Type"
    assert fm["category"] == "enrichment"
    assert fm["last_verified"] == "2026-01-01"
    assert "enrichment-tool" not in text


def test_apply_catalog_is_never_touched(tmp_migrate: Path):
    path = tmp_migrate / "provider-catalog.md"
    before = path.read_text()
    action, _ = migrate_file(path, apply=True)
    assert action == "skip-non-provider"
    assert path.read_text() == before, "NON_PROVIDER_TYPES file must never be written"


def test_apply_valid_is_never_touched(tmp_migrate: Path):
    path = tmp_migrate / "provider-valid.md"
    before = path.read_text()
    action, _ = migrate_file(path, apply=True)
    assert action == "skip-valid"
    assert path.read_text() == before


# ---------------------------------------------------------------------------
# NON_PROVIDER_TYPES denylist completeness
# ---------------------------------------------------------------------------


def test_non_provider_types_includes_expected_values():
    assert "provider-catalog" in NON_PROVIDER_TYPES
    assert "comparison" in NON_PROVIDER_TYPES
    assert "adr" in NON_PROVIDER_TYPES
    # These must NOT be in the denylist — they are the target type
    assert "provider" not in NON_PROVIDER_TYPES


# ---------------------------------------------------------------------------
# normalize_type_in_place edge cases
# ---------------------------------------------------------------------------


def test_normalize_inserts_type_when_missing(tmp_path: Path):
    """File with frontmatter but NO type: key at all — type: provider is inserted."""
    f = tmp_path / "provider-notype.md"
    f.write_text("---\nprovider: NoType\ncategory: enrichment\n---\nbody\n")
    changed = normalize_type_in_place(f, apply=True)
    assert changed
    text = f.read_text()
    assert "type: provider" in text
    assert "provider: NoType" in text  # existing keys preserved


def test_normalize_does_not_change_already_correct_type(tmp_path: Path):
    """Already-correct type: provider should return changed=False."""
    f = tmp_path / "provider-ok.md"
    f.write_text("---\ntype: provider\nprovider: Ok\n---\nbody\n")
    changed = normalize_type_in_place(f, apply=True)
    assert not changed


# ---------------------------------------------------------------------------
# _parse_simple_yaml: empty scalar must not become an empty list
# ---------------------------------------------------------------------------


def test_empty_scalar_stays_empty_string():
    """An empty `key:` with no following list items is a scalar, not a list."""
    fm, _ = _wiki.split_frontmatter(
        "---\ntype: provider\nfree_tier_summary:\napi_access: yes\n---\nbody\n"
    )
    assert fm is not None
    assert fm["free_tier_summary"] == ""
    assert fm["api_access"] == "yes"


def test_block_list_is_still_parsed_correctly():
    """A genuine block list must still work after the empty-scalar fix."""
    fm, _ = _wiki.split_frontmatter(
        "---\ntype: provider\ntags:\n  - provider\n  - test\n---\nbody\n"
    )
    assert fm is not None
    assert fm["tags"] == ["provider", "test"]

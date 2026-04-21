"""Shared pytest fixtures for wiki_scan tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.fixture
def layered_wiki() -> Path:
    return REPO_ROOT / "tests" / "fixtures" / "layered-wiki"


@pytest.fixture
def flat_wiki() -> Path:
    return REPO_ROOT / "tests" / "fixtures" / "flat-wiki"

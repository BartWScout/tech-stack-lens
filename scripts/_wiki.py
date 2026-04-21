"""Shared helpers for wiki discovery, frontmatter parsing, and freshness classification.

Used by wiki_scan.py, migrate_frontmatter.py, and backfill_last_verified.py.
Also imported by tests/test_wiki_scan.py.

Uses only the Python standard library — no third-party deps. YAML frontmatter
is parsed with a small hand-rolled reader that handles the subset of YAML this
skill writes (scalars, lists, block style). If more complex frontmatter appears,
extend the reader instead of pulling in PyYAML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path


LAYER_CATEGORY = {
    "layer-1-signal-discovery": "discovery",
    "layer-2-enrichment": "enrichment",
    "layer-3-storage": "storage",
    "layer-4-orchestration": "orchestration",
    "layer-5-observability": "observability",
    "layer-6-delivery": "delivery",
    "layer-7-development": "development",
    "layer-8-memory": "memory",
    "layer-9-devops": "devops",
}


@dataclass
class Provider:
    path: Path
    name: str
    has_frontmatter: bool
    frontmatter: dict = field(default_factory=dict)
    body: str = ""

    @property
    def last_verified(self) -> date | None:
        raw = self.frontmatter.get("last_verified")
        if not raw:
            return None
        try:
            return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    @property
    def layer(self) -> str | None:
        for part in self.path.parts:
            if part in LAYER_CATEGORY:
                return part
        return None

    @property
    def category(self) -> str:
        explicit = self.frontmatter.get("category")
        if explicit:
            return str(explicit)
        return LAYER_CATEGORY.get(self.layer or "", "unknown")


def find_providers(wiki_root: Path) -> list[Path]:
    """Return every provider-*.md file under the wiki, sorted by path."""
    return sorted(p for p in wiki_root.rglob("provider-*.md") if p.is_file())


def has_valid_provider_frontmatter(provider: "Provider") -> bool:
    """True only if the file has a frontmatter block AND `type: provider`.

    A file with only `title:` or other stray keys is treated as malformed, not
    migrated — Dataview dashboards filter on `type = "provider"` and skip anything
    without it.
    """
    return provider.has_frontmatter and str(provider.frontmatter.get("type", "")).strip() == "provider"


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Return (frontmatter_dict, body). Returns (None, full_text) if no frontmatter."""
    if not text.startswith("---\n"):
        return None, text
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return None, text
    raw_yaml = text[4:end]
    body = text[end + 5 :]
    return _parse_simple_yaml(raw_yaml), body


def _parse_simple_yaml(raw: str) -> dict:
    """Minimal YAML reader for frontmatter. Handles scalars, inline lists, block lists.

    Not a general YAML parser. Good enough for what this skill emits and for the
    frontmatter shape seen in scouting-llm-wiki.
    """
    out: dict = {}
    current_key: str | None = None
    current_list: list | None = None
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip().strip('"').strip("'"))
            continue
        if ": " in line or line.endswith(":"):
            if current_list is not None and current_key is not None:
                out[current_key] = current_list
                current_list = None
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            current_key = key
            if value == "" or value == "[]":
                out[key] = [] if value == "[]" else ""
                if value == "":
                    current_list = []
                continue
            if value.startswith("[") and value.endswith("]"):
                items = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
                out[key] = items
                current_list = None
                continue
            out[key] = value.strip('"').strip("'")
            current_list = None
    if current_list is not None and current_key is not None:
        # flush trailing block list
        if out.get(current_key) in ("", []):
            out[current_key] = current_list
    return out


def load_provider(path: Path) -> Provider:
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    name = _infer_name(path, body if fm is not None else text)
    return Provider(
        path=path,
        name=name,
        has_frontmatter=fm is not None,
        frontmatter=fm or {},
        body=body if fm is not None else text,
    )


def _infer_name(path: Path, body: str) -> str:
    """Prefer the first '# <Name>' heading in the body; fall back to filename stem."""
    match = re.search(r"^#\s+(.+?)$", body, flags=re.MULTILINE)
    if match:
        raw = match.group(1).strip()
        raw = re.sub(r"\s*\(.*?\)\s*$", "", raw)
        if raw:
            return raw
    stem = path.stem
    if stem.startswith("provider-"):
        stem = stem[len("provider-") :]
    return stem.replace("-", " ").title()


def classify_freshness(provider: Provider, today: date | None = None, aging_days: int = 14, stale_days: int = 30) -> str:
    """Return one of: current, aging, stale, missing-date."""
    today = today or date.today()
    lv = provider.last_verified
    if lv is None:
        return "missing-date"
    delta = (today - lv).days
    if delta < aging_days:
        return "current"
    if delta < stale_days:
        return "aging"
    return "stale"


def file_mtime_date(path: Path) -> date:
    """Return the file's modification time as a calendar date (UTC)."""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def render_frontmatter(fields: dict) -> str:
    """Render a dict as YAML frontmatter (between --- markers). Preserves insertion order."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
        elif value is None or value == "":
            lines.append(f"{key}:")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"

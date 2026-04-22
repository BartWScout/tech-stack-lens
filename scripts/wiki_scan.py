#!/usr/bin/env python3
"""Recursive wiki scan + freshness dashboard.

Replaces the inline bash/Python scattered through SKILL.md Step 1.5.
Works on flat or layered wiki layouts without configuration.

Usage:
    python scripts/wiki_scan.py                    # scan default wiki from config
    python scripts/wiki_scan.py --wiki /path/to/wiki
    python scripts/wiki_scan.py --json             # machine-readable output

Prints:
    - total providers found
    - freshness buckets (current / aging / stale / missing-date)
    - breakdown by layer
    - list of stale + missing-date files (when --list is passed)

Exit code is always 0 — this is a read-only scan.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import re

sys.path.insert(0, str(Path(__file__).parent))
from _wiki import classify_freshness, find_providers, load_provider  # noqa: E402

_SCRIPTS_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _SCRIPTS_DIR.parent / "config" / "default-profile.yaml"
_WIKI_PATH_RE = re.compile(r"^\s*wiki_path:\s*(.+)$")


def _wiki_from_config() -> Path | None:
    """Read wiki_path from config/default-profile.yaml at runtime."""
    if not _CONFIG_FILE.exists():
        return None
    for line in _CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        m = _WIKI_PATH_RE.match(line)
        if m:
            return Path(m.group(1).strip()).expanduser()
    return None


def scan(wiki_root: Path) -> dict:
    providers = [load_provider(p) for p in find_providers(wiki_root)]
    buckets: Counter = Counter()
    by_layer_bucket: defaultdict = defaultdict(lambda: Counter())
    detail: list[dict] = []
    for p in providers:
        bucket = classify_freshness(p)
        buckets[bucket] += 1
        by_layer_bucket[p.layer or "root"][bucket] += 1
        detail.append(
            {
                "path": str(p.path),
                "name": p.name,
                "layer": p.layer,
                "category": p.category,
                "has_frontmatter": p.has_frontmatter,
                "last_verified": str(p.last_verified) if p.last_verified else None,
                "bucket": bucket,
            }
        )
    return {
        "wiki": str(wiki_root),
        "total": len(providers),
        "buckets": dict(buckets),
        "by_layer": {k: dict(v) for k, v in by_layer_bucket.items()},
        "providers": detail,
    }


def render_dashboard(result: dict) -> str:
    total = result["total"]
    buckets = result["buckets"]
    max_count = max(buckets.values()) if buckets else 1
    bar_width = 24

    def bar(count: int) -> str:
        filled = int((count / max_count) * bar_width) if max_count else 0
        return "█" * filled + " " * (bar_width - filled)

    order = [
        ("current", "Current (<14d)"),
        ("aging", "Aging (14-30d)"),
        ("stale", "Stale (>30d)"),
        ("missing-date", "Missing date"),
    ]
    lines = ["", "WIKI FRESHNESS DASHBOARD", "─" * 54]
    for key, label in order:
        count = buckets.get(key, 0)
        lines.append(f"  {label:<18} {bar(count)}  {count}")
    lines.append("─" * 54)
    lines.append(f"  Total: {total} provider profiles")

    lines.append("")
    lines.append("By layer:")
    for layer, layer_counts in sorted(result["by_layer"].items()):
        parts = [f"{k}={v}" for k, v in sorted(layer_counts.items()) if v]
        lines.append(f"  {layer:<32} {' · '.join(parts)}")
    return "\n".join(lines)


def render_list(result: dict, bucket: str) -> str:
    rows = [p for p in result["providers"] if p["bucket"] == bucket]
    if not rows:
        return f"No providers in bucket '{bucket}'."
    lines = [f"\n{bucket.upper()} ({len(rows)} files)", "─" * 80]
    for i, p in enumerate(rows, 1):
        rel = Path(p["path"]).relative_to(Path(result["wiki"]))
        verified = p["last_verified"] or "(none)"
        lines.append(f"  {i:3d}. {p['name']:<30} · {verified} · {rel}")
    return "\n".join(lines)


def main() -> int:
    default_wiki = _wiki_from_config() or Path("/Users/bartek/projects/scouting-llm-wiki")
    parser = argparse.ArgumentParser(description="Scan the wiki for provider freshness.")
    parser.add_argument("--wiki", type=Path, default=default_wiki)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the dashboard")
    parser.add_argument("--list", choices=["stale", "missing-date", "aging", "current"], help="Also list files in this bucket")
    args = parser.parse_args()

    if not args.wiki.exists():
        print(f"ERROR: wiki not found at {args.wiki}", file=sys.stderr)
        return 2

    result = scan(args.wiki)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(render_dashboard(result))
    if args.list:
        print(render_list(result, args.list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

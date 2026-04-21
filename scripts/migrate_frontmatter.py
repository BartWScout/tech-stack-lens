#!/usr/bin/env python3
"""One-off migration: add YAML frontmatter to provider-*.md files that lack it.

Dataview dashboards in the wiki query frontmatter fields (`type`, `provider`,
`category`, `status`, `last_verified`, etc.). Files without frontmatter are
invisible to those queries. This script injects a minimal valid frontmatter
block at the top of each orphan file, preserving the body content exactly.

Behavior:
    - Provider name is inferred from the first '# <Name>' heading in the body,
      falling back to the filename stem.
    - Category is inferred from the layer directory (`layer-N-<slug>`).
    - `last_verified` is set from file mtime so the freshness dashboard reflects
      reality (not an artificial "today" value).
    - `source_refs` and `source_dates` are empty lists — the dashboard flags
      these for research follow-up, which is accurate.

Usage:
    python scripts/migrate_frontmatter.py --wiki /path/to/wiki --dry-run
    python scripts/migrate_frontmatter.py --wiki /path/to/wiki --apply
    python scripts/migrate_frontmatter.py --wiki /path/to/wiki --apply --limit 5

The script refuses to run without one of --dry-run or --apply. Always dry-run
first. When --apply is used, a single-line summary is printed per file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _wiki import (  # noqa: E402
    LAYER_CATEGORY,
    file_mtime_date,
    find_providers,
    load_provider,
    render_frontmatter,
)


def build_frontmatter(path: Path, provider_name: str) -> dict:
    """Build the frontmatter dict for a single orphan file."""
    layer = next((p for p in path.parts if p in LAYER_CATEGORY), None)
    category = LAYER_CATEGORY.get(layer or "", "unknown")
    return {
        "type": "provider",
        "provider": provider_name,
        "layer": layer or "",
        "category": category,
        "status": "active",
        "free_tier_summary": "unknown",
        "api_access": "unknown",
        "mcp_support": "unknown",
        "source_refs": [],
        "source_dates": [],
        "last_verified": file_mtime_date(path).isoformat(),
        "confidence": "low",
        "review_cycle_days": 30,
        "tags": ["provider", "migrated-frontmatter"],
    }


def migrate_file(path: Path, apply: bool) -> tuple[str, str]:
    """Migrate one file. Returns (action, note) for reporting.

    action: 'skip-has-frontmatter' | 'would-migrate' | 'migrated'
    """
    provider = load_provider(path)
    if provider.has_frontmatter:
        return "skip-has-frontmatter", ""

    fm = build_frontmatter(path, provider.name)
    new_text = render_frontmatter(fm) + "\n" + provider.body.lstrip("\n")

    if apply:
        path.write_text(new_text, encoding="utf-8")
        return "migrated", f"{provider.name} · {fm['category']}"
    return "would-migrate", f"{provider.name} · {fm['category']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Add frontmatter to orphan provider-*.md files.")
    parser.add_argument("--wiki", type=Path, required=True, help="Wiki root path")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview without writing")
    mode.add_argument("--apply", action="store_true", help="Actually write changes")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N orphans (0 = all)")
    parser.add_argument("--show-sample", action="store_true", help="Print full first sample output")
    args = parser.parse_args()

    if not args.wiki.exists():
        print(f"ERROR: wiki not found at {args.wiki}", file=sys.stderr)
        return 2

    all_files = find_providers(args.wiki)
    processed = 0
    migrated = 0
    skipped = 0
    sample_printed = False

    for path in all_files:
        if args.limit and processed >= args.limit:
            break
        action, note = migrate_file(path, apply=args.apply)
        if action == "skip-has-frontmatter":
            skipped += 1
            continue

        processed += 1
        migrated += 1
        rel = path.relative_to(args.wiki)
        print(f"  [{action:>15}] {rel}  ·  {note}")

        if args.show_sample and not sample_printed and action in ("would-migrate", "migrated"):
            sample_printed = True
            print("\n--- sample rendered frontmatter ---")
            provider = load_provider(path)
            fm = build_frontmatter(path, provider.name)
            print(render_frontmatter(fm))
            print("--- end sample ---\n")

    mode_label = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n{mode_label}: {migrated} files {'written' if args.apply else 'would be written'} · {skipped} already had frontmatter · {len(all_files)} scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

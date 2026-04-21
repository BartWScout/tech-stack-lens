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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _wiki import (  # noqa: E402
    LAYER_CATEGORY,
    file_mtime_date,
    find_providers,
    has_valid_provider_frontmatter,
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


def normalize_type_in_place(path: Path, apply: bool) -> bool:
    """Rewrite only the `type:` line of an existing frontmatter block to `type: provider`.

    If the block has no `type:` line, insert one after the opening `---`. Preserves
    every other key and the body exactly. Returns True on change.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return False
    header = text[4:end]
    body = text[end + 5 :]

    type_line = re.compile(r"^type:\s*.*$", re.MULTILINE)
    if type_line.search(header):
        new_header = type_line.sub("type: provider", header, count=1)
    else:
        new_header = "type: provider\n" + header

    new_text = f"---\n{new_header}\n---\n{body}"
    if new_text == text:
        return False
    if apply:
        path.write_text(new_text, encoding="utf-8")
    return True


# Existing `type:` values that identify the file as something other than an
# individual provider profile (catalogs, references, comparisons). Normalizing
# these to `type: provider` would wrongly pull them into the provider-status
# dashboard. Skipped with a visible warning so the user can rename or retype by hand.
NON_PROVIDER_TYPES = {
    "provider-catalog",
    "reference-catalog",
    "comparison",
    "adr",
    "quick-decision",
    "benchmark",
    "startup",
    "source",
}


def migrate_file(path: Path, apply: bool) -> tuple[str, str]:
    """Migrate one file. Returns (action, note) for reporting.

    Paths:
      - skip-valid                → already has `type: provider`
      - skip-non-provider         → frontmatter says this is a catalog/reference/etc.
      - inject / would-inject     → no frontmatter at all, insert full template
      - normalize / would-normalize → has frontmatter with non-provider type, rewrite
                                       only the `type:` line (preserves all other keys)
    """
    provider = load_provider(path)
    if has_valid_provider_frontmatter(provider):
        return "skip-valid", ""

    if provider.has_frontmatter:
        existing_type = str(provider.frontmatter.get("type", "")).strip()
        if existing_type in NON_PROVIDER_TYPES:
            return "skip-non-provider", f"type={existing_type!r} — rename file or retype by hand"
        changed = normalize_type_in_place(path, apply=apply)
        if not changed:
            return "skip-no-change", ""
        action = "normalized" if apply else "would-normalize"
        display = existing_type or "(missing)"
        return action, f"{provider.name}  (was type={display!r})"

    fm = build_frontmatter(path, provider.name)
    new_text = render_frontmatter(fm) + "\n" + provider.body.lstrip("\n")
    if apply:
        path.write_text(new_text, encoding="utf-8")
        return "injected", f"{provider.name} · {fm['category']}"
    return "would-inject", f"{provider.name} · {fm['category']}"


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
    injected = 0
    normalized = 0
    skipped = 0
    skipped_non_provider = 0
    sample_printed = False

    for path in all_files:
        if args.limit and processed >= args.limit:
            break
        action, note = migrate_file(path, apply=args.apply)
        if action in ("skip-valid", "skip-no-change"):
            skipped += 1
            continue
        if action == "skip-non-provider":
            skipped_non_provider += 1
            rel = path.relative_to(args.wiki)
            print(f"  [{action:>18}] {rel}  ·  {note}")
            continue

        processed += 1
        if action in ("injected", "would-inject"):
            injected += 1
        elif action in ("normalized", "would-normalize"):
            normalized += 1
        rel = path.relative_to(args.wiki)
        print(f"  [{action:>18}] {rel}  ·  {note}")

        if args.show_sample and not sample_printed and action in ("would-inject", "injected"):
            sample_printed = True
            print("\n--- sample rendered frontmatter (inject path) ---")
            provider = load_provider(path)
            fm = build_frontmatter(path, provider.name)
            print(render_frontmatter(fm))
            print("--- end sample ---\n")

    mode_label = "APPLIED" if args.apply else "DRY-RUN"
    verb = "written" if args.apply else "would be written"
    print(
        f"\n{mode_label}: {injected + normalized} files {verb} "
        f"({injected} full-inject, {normalized} type normalized) · "
        f"{skipped} already valid · {skipped_non_provider} non-provider (catalog/reference) skipped · "
        f"{len(all_files)} scanned"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Update `last_verified` on provider files that already have frontmatter.

Used by Step 7 wiki sync to mark a provider as re-verified today. Differs from
migrate_frontmatter.py: that script injects frontmatter into orphans, this one
modifies the `last_verified` line in place.

Usage:
    python scripts/backfill_last_verified.py --wiki /path/to/wiki --providers pdl,clay --dry-run
    python scripts/backfill_last_verified.py --wiki /path/to/wiki --all-stale --apply
    python scripts/backfill_last_verified.py --wiki /path/to/wiki --providers all --apply

Flags:
    --providers <csv|all>  providers to update, by name (matches `provider:` field)
    --all-stale            update every provider whose last_verified is >30 days old
    --date YYYY-MM-DD      date to write (default: today)
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _wiki import classify_freshness, find_providers, load_provider  # noqa: E402


def update_last_verified(path: Path, new_date: str, apply: bool) -> bool:
    """Replace the `last_verified:` line in the frontmatter. Returns True on change."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"^last_verified:\s*.*$", re.MULTILINE)
    if not pattern.search(text):
        return False
    new_text = pattern.sub(f"last_verified: {new_date}", text, count=1)
    if new_text == text:
        return False
    if apply:
        path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update last_verified on wiki provider files.")
    parser.add_argument("--wiki", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--providers", help="Comma-separated provider names, or 'all'")
    mode.add_argument("--all-stale", action="store_true", help="Only providers currently classified as stale")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD date to write (default: today)")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.wiki.exists():
        print(f"ERROR: wiki not found at {args.wiki}", file=sys.stderr)
        return 2

    providers_with_fm = [load_provider(p) for p in find_providers(args.wiki)]
    providers_with_fm = [p for p in providers_with_fm if p.has_frontmatter]

    if args.all_stale:
        targets = [p for p in providers_with_fm if classify_freshness(p) == "stale"]
    elif args.providers == "all":
        targets = providers_with_fm
    else:
        wanted = {n.strip().lower() for n in args.providers.split(",") if n.strip()}
        targets = [p for p in providers_with_fm if p.name.lower() in wanted or p.path.stem.replace("provider-", "").lower() in wanted]

    if not targets:
        print("No matching providers.")
        return 0

    updated = 0
    for p in targets:
        changed = update_last_verified(p.path, args.date, apply=args.apply)
        rel = p.path.relative_to(args.wiki)
        verb = "UPDATED" if args.apply and changed else ("WOULD UPDATE" if changed else "NO CHANGE")
        print(f"  [{verb:>12}] {p.name:<30} · {rel}")
        if changed:
            updated += 1

    mode_label = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n{mode_label}: {updated}/{len(targets)} files {'updated' if args.apply else 'would be updated'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

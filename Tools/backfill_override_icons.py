# -*- coding: utf-8 -*-
"""
backfill_override_icons.py
--------------------------
Copies already-present icon PNGs to their override-slug names, without
needing to re-run the full parse_asset_recipes pipeline.

Also cleans up orphaned override-slug PNGs: if a "to" slug exists in the
icons folder but has no corresponding entry in name_overrides.json, it was
likely created by a previous typo and is deleted.

Run this whenever name_overrides.json has been updated.

Usage
-----
    python Tools\\backfill_override_icons.py
"""

import json
import shutil
from pathlib import Path

NAME_OVERRIDES_JSON = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\data\name_overrides.json")
RECIPES_JSON        = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\data\recipes.json")
ICON_DIR            = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\images\icons")


def display_to_slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def load_overrides() -> list[dict]:
    if not NAME_OVERRIDES_JSON.exists():
        print(f"ERROR: {NAME_OVERRIDES_JSON} not found.")
        return []

    with open(NAME_OVERRIDES_JSON, encoding="utf-8") as f:
        data = json.load(f)

    return [
        e for e in data.get("items", [])
        if e.get("from", "").strip() and e.get("to", "").strip()
    ]


def load_raw_recipe_slugs() -> set[str]:
    """
    Returns the set of slugs derived from the raw names in recipes.json.
    These are the PNGs the parser wrote -- we must never delete these.
    """
    if not RECIPES_JSON.exists():
        return set()

    with open(RECIPES_JSON, encoding="utf-8") as f:
        recipes = json.load(f)

    return {display_to_slug(r["name"]) for r in recipes if r.get("name")}


def main():
    entries = load_overrides()
    if not entries:
        return

    # Build the valid set of override-destination slugs from the current file
    valid_override_slugs = {
        display_to_slug(e["to"].strip()) for e in entries
    }

    # Build the set of raw-name slugs (parser-generated PNGs -- never touch these)
    raw_slugs = load_raw_recipe_slugs()

    # ── Phase 1: Copy missing override icons ──────────────────
    print("Phase 1: Copying override icons...")
    copied  = 0
    missing = 0

    for entry in entries:
        raw_name      = entry["from"].strip()
        override_name = entry["to"].strip()

        src_slug  = display_to_slug(raw_name)
        dest_slug = display_to_slug(override_name)

        src  = ICON_DIR / f"{src_slug}.png"
        dest = ICON_DIR / f"{dest_slug}.png"

        if dest.exists():
            print(f"  SKIP (already exists): {dest.name}")
            continue

        if not src.exists():
            print(f"  MISSING source icon:   {src.name}  ('{raw_name}' -> '{override_name}')")
            missing += 1
            continue

        shutil.copy2(src, dest)
        print(f"  COPIED: {src.name} -> {dest.name}")
        copied += 1

    print(f"\n  {copied} icon(s) copied, {missing} source(s) missing.")

    # ── Phase 2: Delete orphaned override-slug PNGs ───────────
    print("\nPhase 2: Cleaning up orphaned override icons...")
    deleted = 0

    for png in sorted(ICON_DIR.glob("*.png")):
        slug = png.stem  # filename without .png

        # Never delete a raw parser-generated icon
        if slug in raw_slugs:
            continue

        # If it's a valid current override destination, keep it
        if slug in valid_override_slugs:
            continue

        # Not a raw icon and not a valid override -- orphan, safe to delete
        print(f"  DELETED orphan: {png.name}")
        png.unlink()
        deleted += 1

    if deleted == 0:
        print("  No orphaned icons found.")
    else:
        print(f"\n  {deleted} orphaned icon(s) deleted.")


if __name__ == "__main__":
    main()
"""
parse_asset_recipes.py
----------------------
Reads all Unity MonoBehaviour .asset files exported by AssetRipper v3,
resolves ingredient GUIDs via .meta sidecar files, and produces:

  1. extracted_recipes.json  – recipes.json-compatible array
  2. wwwroot/images/icons/   – PNG icon files copied from the export

Usage
-----
    python parse_asset_recipes.py
    python parse_asset_recipes.py --export-icons
    python parse_asset_recipes.py --help

Requires Python 3.8+. No third-party packages needed.
"""

import argparse
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------
MONO_ROOT    = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\MonoBehaviour")
EXPORT_ROOT  = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject")
OUTPUT_FILE  = Path(r"D:\PlanetCrafterAssistant\Tools\extracted_recipes.json")
ICON_OUT_DIR = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\images\icons")

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "0": "Raw",       "1": "Resource",  "2": "Equipment",
    "3": "Structure", "4": "Machine",   "5": "Energy",
    "6": "Machine",   "7": "Rocket",    "8": "Automation",
    "9": "Toxicity",  "10": "Storage",
}
WORLD_UNIT_MAP = {
    "1": "Heat",    "2": "Pressure", "3": "Oxygen",
    "4": "Biomass", "5": "Insects",  "6": "Animals", "7": "Humidity",
}
UNIT_LABEL_MAP = {
    "Heat": "nK", "Pressure": "µPa", "Oxygen": "ppm",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_asset(path: Path) -> str:
    """Read a Unity .asset or .meta file, handling UTF-16 LE and UTF-8."""
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw.decode("utf-16-le")
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def get_field(text: str, field: str) -> str | None:
    """Extract a scalar YAML field value, e.g. 'id: Iron1' → 'Iron1'."""
    m = re.search(rf"^\s*{re.escape(field)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def get_guid_from_ref(ref: str) -> str | None:
    """Extract guid from a Unity object reference string."""
    m = re.search(r"guid:\s*([0-9a-fA-F]{32})", ref)
    return m.group(1).lower() if m else None


def pascal_to_display(raw_id: str) -> str:
    """
    Convert a Unity id string to a human-readable display name.
      'AnimalFeeder1'  → 'Animal Feeder T1'
      'SuperAlloy'     → 'Super Alloy'
      'OreExtractorT3' → 'Ore Extractor T3'
    """
    name = re.sub(r"(\d+)$", r" T\1", raw_id)
    name = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", name)
    return name.strip()


# ---------------------------------------------------------------------------
# Pass 1 – Build GUID maps from .meta sidecars
#           guid_to_id   : guid → item id string (e.g. 'Iron1')
#           guid_to_path : guid → asset/png file path on disk
#           png_guid_map : guid → Path for every PNG found in the export
# ---------------------------------------------------------------------------

def build_guid_maps(export_root: Path):
    guid_to_id   = {}
    guid_to_path = {}
    png_guid_map = {}   # guid → Path of the .png file itself

    meta_files = list(export_root.rglob("*.meta"))
    print(f"  {len(meta_files)} .meta files found.")

    for meta_path in meta_files:
        try:
            meta_text = read_asset(meta_path)
        except Exception:
            continue

        m = re.search(r"^\s*guid:\s*([0-9a-fA-F]{32})", meta_text, re.MULTILINE)
        if not m:
            continue

        guid = m.group(1).lower()

        # The asset this .meta describes is the path without the .meta suffix
        asset_path = Path(str(meta_path)[:-5])  # strip ".meta"
        if not asset_path.exists():
            continue

        guid_to_path[guid] = asset_path

        # Track PNGs separately for icon resolution
        if asset_path.suffix.lower() == ".png":
            png_guid_map[guid] = asset_path

        # Read id field from .asset files
        if asset_path.suffix == ".asset":
            try:
                asset_text = read_asset(asset_path)
                item_id = get_field(asset_text, "id")
                if item_id:
                    guid_to_id[guid] = item_id
            except Exception:
                pass

    return guid_to_id, guid_to_path, png_guid_map


# ---------------------------------------------------------------------------
# Pass 2 – Find all craftable assets (those containing recipeIngredients)
# ---------------------------------------------------------------------------

def find_craftable_assets(mono_root: Path) -> list[Path]:
    craftable = []
    for asset_path in mono_root.rglob("*.asset"):
        try:
            text = read_asset(asset_path)
            if "recipeIngredients:" in text:
                craftable.append(asset_path)
        except Exception:
            continue
    return craftable


# ---------------------------------------------------------------------------
# Pass 3 – Extract recipe data from each craftable asset
# ---------------------------------------------------------------------------

def extract_recipes(craftable: list[Path], guid_to_id: dict, guid_to_path: dict,
                    png_guid_map: dict, export_icons: bool,
                    icon_out_dir: Path) -> list[dict]:
    recipes     = []
    icons_found = 0
    icons_miss  = 0

    for asset_path in craftable:
        try:
            text = read_asset(asset_path)
        except Exception:
            continue

        # --- Item identity ---
        item_id      = get_field(text, "id") or asset_path.stem
        display_name = pascal_to_display(item_id)

        # --- Category ---
        group_cat = get_field(text, "groupCategory") or ""
        category  = CATEGORY_MAP.get(group_cat, "Resource")

        # --- Icon ---
        # The icon: field references a Sprite/Texture2D asset by GUID.
        # AssetRipper exports the actual PNG alongside that asset, with its
        # own .meta file containing the same GUID — so we look in png_guid_map.
        icon_line = re.search(r"^\s*icon:\s*(\{.+\})", text, re.MULTILINE)
        icon_guid = get_guid_from_ref(icon_line.group(1)) if icon_line else None
        icon_file = None

        if icon_guid:
            png_path = png_guid_map.get(icon_guid)

            # Fallback: the icon GUID may point to a Sprite .asset whose
            # paired PNG shares the same base name in the same folder.
            if png_path is None and icon_guid in guid_to_path:
                sprite_asset = guid_to_path[icon_guid]
                candidate    = sprite_asset.with_suffix(".png")
                if candidate.exists():
                    png_path = candidate

            if png_path and png_path.exists():
                icon_file = png_path.name
                icons_found += 1
                if export_icons:
                    icon_out_dir.mkdir(parents=True, exist_ok=True)
                    dest = icon_out_dir / icon_file
                    if not dest.exists():
                        shutil.copy2(png_path, dest)
            else:
                icons_miss += 1

        # --- Ingredients ---
        ingredient_guids = []
        in_block = False
        for line in text.splitlines():
            if re.match(r"^\s*recipeIngredients:", line):
                in_block = True
                continue
            if in_block:
                ref_match = re.match(r"^\s*-\s*(\{.+\})", line)
                if ref_match:
                    g = get_guid_from_ref(ref_match.group(1))
                    if g:
                        ingredient_guids.append(g)
                elif re.match(r"^\s*\w+:", line) and not line.strip().startswith("-"):
                    in_block = False

        # Resolve guids → names, group and sum duplicates
        name_counts: dict[str, int] = defaultdict(int)
        for g in ingredient_guids:
            resolved_id = guid_to_id.get(g)
            if resolved_id:
                friendly = re.sub(r"\d+$", "", resolved_id)
                friendly = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", friendly)
                name_counts[friendly.strip()] += 1

        ingredients = [
            {"name": name, "quantity": qty}
            for name, qty in name_counts.items()
        ]

        # --- Unlock condition ---
        world_unit  = get_field(text, "unlockingWorldUnit") or ""
        world_value = float(get_field(text, "unlockingValue") or "0")
        stage       = WORLD_UNIT_MAP.get(world_unit)

        unlock_condition = None
        if stage and world_value > 0:
            unlock_condition = {
                "stage":     stage,
                "threshold": world_value,
                "unit":      UNIT_LABEL_MAP.get(stage, "units"),
            }

        recipes.append({
            "name":            display_name,
            "category":        category,
            "description":     "",
            "ingredients":     ingredients,
            "unlockCondition": unlock_condition,
            "craftedIn":       "Crafting Table" if ingredients else None,
            "recyclerYields":  bool(ingredients),
            "_sourceAsset":    asset_path.name,
            "_iconFile":       icon_file,
        })

    print(f"  Icons resolved: {icons_found}  |  Icons not found: {icons_miss}")
    return recipes


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract Planet Crafter recipes from AssetRipper export."
    )
    parser.add_argument("--mono-root",    default=str(MONO_ROOT),    help="Path to MonoBehaviour folder")
    parser.add_argument("--export-root",  default=str(EXPORT_ROOT),  help="Root of full AssetRipper export")
    parser.add_argument("--output",       default=str(OUTPUT_FILE),  help="Output JSON file path")
    parser.add_argument("--icon-out-dir", default=str(ICON_OUT_DIR), help="Destination for copied PNG icons")
    parser.add_argument("--export-icons", action="store_true",       help="Copy icon PNGs to --icon-out-dir")
    args = parser.parse_args()

    mono_root    = Path(args.mono_root)
    export_root  = Path(args.export_root)
    output_file  = Path(args.output)
    icon_out_dir = Path(args.icon_out_dir)

    # Pass 1
    print(f"Pass 1: Building GUID maps from {export_root} ...")
    guid_to_id, guid_to_path, png_guid_map = build_guid_maps(export_root)
    print(f"  {len(guid_to_id)} GUID → id entries indexed.")
    print(f"  {len(png_guid_map)} PNG files indexed.")

    # Pass 2
    print(f"Pass 2: Scanning {mono_root} for craftable assets ...")
    craftable = find_craftable_assets(mono_root)
    print(f"  {len(craftable)} craftable assets found.")

    # Pass 3
    print("Pass 3: Extracting recipe data ...")
    recipes = extract_recipes(
        craftable, guid_to_id, guid_to_path, png_guid_map,
        args.export_icons, icon_out_dir
    )

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(recipes, f, indent=4, ensure_ascii=False)

    print(f"\nDone. {len(recipes)} recipes written to:\n  {output_file}")
    if args.export_icons:
        print(f"  Icons copied to: {icon_out_dir}")
    print("\nNext steps:")
    print("  1. Review extracted_recipes.json — verify names and ingredient counts")
    print("  2. Fill in 'description' fields")
    print("  3. Remove _sourceAsset and _iconFile fields before merging")
    print("  4. Merge into wwwroot/data/recipes.json")


if __name__ == "__main__":
    main()
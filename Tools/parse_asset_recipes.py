# -*- coding: utf-8 -*-
"""
parse_asset_recipes.py
----------------------
Reads all Unity MonoBehaviour .asset files exported by AssetRipper v3,
resolves ingredient GUIDs via .meta sidecar files, and:

  1. Copies ONLY matched PNGs from Texture2D -> wwwroot/icons/
     Each PNG is renamed to match the app's IconSlug convention:
       AnimalFeeder1.png  ->  animal_feeder_t1.png
  2. Writes extracted_recipes.json  (includes _sourceAsset/_iconFile helpers)
  3. Writes wwwroot/data/recipes.json (clean, ready for the app)

Usage
-----
    python Tools\\parse_asset_recipes.py
    python Tools\\parse_asset_recipes.py --help

Requires Python 3.8+. No third-party packages needed.
"""

import argparse
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------
MONO_ROOT      = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\MonoBehaviour")
EXPORT_ROOT    = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject")
TEXTURE2D_DIR  = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject\Assets\Texture2D")
EXTRACTED_FILE = Path(r"D:\PlanetCrafterAssistant\Tools\extracted_recipes.json")
RECIPES_JSON   = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\data\recipes.json")
ICON_OUT_DIR   = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\icons")  # matches /icons/ in the app

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
    "Heat": "nK", "Pressure": "\u00b5Pa", "Oxygen": "ppm",
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
    """Extract a scalar YAML field value, e.g. 'id: Iron1' -> 'Iron1'."""
    m = re.search(rf"^\s*{re.escape(field)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def get_guid_from_ref(ref: str) -> str | None:
    """Extract guid from a Unity object reference string."""
    m = re.search(r"guid:\s*([0-9a-fA-F]{32})", ref)
    return m.group(1).lower() if m else None


def pascal_to_display(raw_id: str) -> str:
    """
    Convert a Unity id string to a human-readable display name.
      'AnimalFeeder1'  -> 'Animal Feeder T1'
      'SuperAlloy'     -> 'Super Alloy'
      'OreExtractorT3' -> 'Ore Extractor T3'
    """
    name = re.sub(r"(\d+)$", r" T\1", raw_id)
    name = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", name)
    return name.strip()


def display_to_slug(display_name: str) -> str:
    """
    Convert display name to the IconSlug the app uses.
    Matches C# model: Name.ToLower().Replace(" ", "_")
      'Animal Feeder T1' -> 'animal_feeder_t1'
      'Super Alloy'      -> 'super_alloy'
    """
    return display_name.lower().replace(" ", "_")


def to_clean_recipe(r: dict) -> dict:
    """Strip helper fields to produce a clean recipes.json entry."""
    return {
        "name":            r["name"],
        "category":        r["category"],
        "description":     r["description"],
        "ingredients":     r["ingredients"],
        "unlockCondition": r["unlockCondition"],
        "craftedIn":       r["craftedIn"],
        "recyclerYields":  r["recyclerYields"],
    }


# ---------------------------------------------------------------------------
# Pass 1 – Build GUID -> id map from .meta sidecars
# ---------------------------------------------------------------------------

def build_guid_map(export_root: Path) -> dict:
    """Returns guid_to_id: dict[str, str]  guid -> item id (e.g. 'Iron1')"""
    guid_to_id = {}
    meta_files = list(export_root.rglob("*.asset.meta"))
    print(f"  {len(meta_files)} .asset.meta files found.")

    for meta_path in meta_files:
        try:
            meta_text = read_asset(meta_path)
        except Exception:
            continue

        m = re.search(r"^\s*guid:\s*([0-9a-fA-F]{32})", meta_text, re.MULTILINE)
        if not m:
            continue

        guid       = m.group(1).lower()
        asset_path = Path(str(meta_path)[:-5])  # strip ".meta"
        if not asset_path.exists():
            continue

        try:
            asset_text = read_asset(asset_path)
            item_id    = get_field(asset_text, "id")
            if item_id:
                guid_to_id[guid] = item_id
        except Exception:
            pass

    return guid_to_id


# ---------------------------------------------------------------------------
# Pass 1b – Index Texture2D PNGs by lowercase stem
# ---------------------------------------------------------------------------

def build_texture_map(texture2d_dir: Path) -> dict:
    """
    Returns stem_to_png: dict[str, Path]
    e.g. 'autocrafter1' -> Path('.../Texture2D/AutoCrafter1.png')
    """
    stem_to_png = {}
    if not texture2d_dir.exists():
        print(f"  WARNING: Texture2D folder not found at {texture2d_dir}")
        return stem_to_png

    for png in texture2d_dir.rglob("*.png"):
        stem_to_png[png.stem.lower()] = png

    print(f"  {len(stem_to_png)} PNGs indexed from Texture2D.")

    # Show a few samples so we can verify the stem format
    for stem, path in list(stem_to_png.items())[:5]:
        print(f"    sample: '{stem}' -> {path.name}")

    return stem_to_png


# ---------------------------------------------------------------------------
# Pass 2 – Find all craftable assets (those containing recipeIngredients)
# ---------------------------------------------------------------------------

def find_craftable_assets(mono_root: Path) -> list:
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
# Pass 3 – Extract recipe data and copy only matched icons
# ---------------------------------------------------------------------------

def extract_recipes(craftable: list, guid_to_id: dict,
                    stem_to_png: dict, icon_out_dir: Path) -> list:
    recipes      = []
    icons_found  = 0
    icons_miss   = 0
    miss_samples = []

    icon_out_dir.mkdir(parents=True, exist_ok=True)

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
        # Match PNG from Texture2D by the asset id stem (e.g. 'autocrafter1')
        # then copy it renamed to the app's IconSlug format (e.g. 'auto_crafter_t1.png')
        # so that /icons/{slug}.png in the Razor view resolves correctly.
        icon_file  = None
        lookup_key = item_id.lower()
        png_path   = stem_to_png.get(lookup_key)

        if png_path:
            slug      = display_to_slug(display_name)   # e.g. 'animal_feeder_t1'
            icon_file = f"{slug}.png"
            icons_found += 1
            dest = icon_out_dir / icon_file
            if not dest.exists():
                shutil.copy2(png_path, dest)
        else:
            icons_miss += 1
            if len(miss_samples) < 10:
                miss_samples.append(f"'{lookup_key}' (asset: {asset_path.name})")

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

        # Resolve guids -> names, group and sum duplicates
        name_counts: dict = defaultdict(int)
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
    if miss_samples:
        print(f"  Sample unmatched keys (first {len(miss_samples)}):")
        for s in miss_samples:
            print(f"    {s}")

    return recipes


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract Planet Crafter recipes from AssetRipper export."
    )
    parser.add_argument("--mono-root",     default=str(MONO_ROOT),      help="Path to MonoBehaviour folder")
    parser.add_argument("--export-root",   default=str(EXPORT_ROOT),    help="Root of full AssetRipper export")
    parser.add_argument("--texture2d-dir", default=str(TEXTURE2D_DIR),  help="Path to Texture2D PNG folder")
    parser.add_argument("--extracted",     default=str(EXTRACTED_FILE), help="Output path for extracted_recipes.json")
    parser.add_argument("--recipes-json",  default=str(RECIPES_JSON),   help="Project recipes.json to overwrite")
    parser.add_argument("--icon-out-dir",  default=str(ICON_OUT_DIR),   help="wwwroot/icons folder")
    args = parser.parse_args()

    mono_root     = Path(args.mono_root)
    export_root   = Path(args.export_root)
    texture2d_dir = Path(args.texture2d_dir)
    extracted     = Path(args.extracted)
    recipes_json  = Path(args.recipes_json)
    icon_out_dir  = Path(args.icon_out_dir)

    # Pass 1
    print(f"Pass 1: Building GUID map from {export_root} ...")
    guid_to_id = build_guid_map(export_root)
    print(f"  {len(guid_to_id)} GUID -> id entries indexed.")

    # Pass 1b
    print(f"Pass 1b: Indexing PNGs from {texture2d_dir} ...")
    stem_to_png = build_texture_map(texture2d_dir)

    # Pass 2
    print(f"Pass 2: Scanning {mono_root} for craftable assets ...")
    craftable = find_craftable_assets(mono_root)
    print(f"  {len(craftable)} craftable assets found.")

    # Pass 3
    print(f"Pass 3: Extracting recipes and copying matched icons to {icon_out_dir} ...")
    recipes = extract_recipes(craftable, guid_to_id, stem_to_png, icon_out_dir)

    # Write extracted_recipes.json (with helper fields for review)
    extracted.parent.mkdir(parents=True, exist_ok=True)
    with open(extracted, "w", encoding="utf-8") as f:
        json.dump(recipes, f, indent=4, ensure_ascii=False)
    print(f"\n  extracted_recipes.json -> {extracted}")

    # Write clean recipes.json directly into the project
    clean = [to_clean_recipe(r) for r in recipes]
    recipes_json.parent.mkdir(parents=True, exist_ok=True)
    with open(recipes_json, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=4, ensure_ascii=False)
    print(f"  recipes.json           -> {recipes_json}")

    print(f"\nDone. {len(recipes)} recipes written.")
    print(f"  Icons copied to: {icon_out_dir}")
    print("\nNext steps:")
    print("  1. Check 'Icons not found' count above — 0 is ideal")
    print("  2. Fill in 'description' fields in recipes.json as needed")
    print("  3. Run the app and verify icons appear on the Recipes page")


if __name__ == "__main__":
    main()
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

Craft station detection
-----------------------
The script resolves craftedIn in three passes, in priority order:

  1. crafterType field on the asset (integer -> station name via CRAFTER_TYPE_MAP)
  2. Asset id keyword heuristics (e.g. 'Biolab', 'QuartzStation' in the id)
  3. groupCategory / equipableType fallback:
       - groupCategory 3 (Structure) -> "Build Menu"   (constructibles)
       - everything else with ingredients -> "Crafting Table"

Any unresolved crafterType integer triggers a WARNING so the map can be updated.

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
MONO_ROOT      = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v_2.004_4_6_2026_ExportedProject\ExportedProject\Assets\MonoBehaviour")
EXPORT_ROOT    = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v_2.004_4_6_2026_ExportedProject\ExportedProject")
TEXTURE2D_DIR  = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v_2.004_4_6_2026_ExportedProject\ExportedProject\Assets\Texture2D")
EXTRACTED_FILE = Path(r"D:\PlanetCrafterAssistant\Tools\extracted_recipes.json")
RECIPES_JSON   = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\data\recipes.json")
ICON_OUT_DIR   = Path(r"D:\PlanetCrafterAssistant\App\wwwroot\images\icons")  # matches /images/icons/ in the app

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "0": "Raw",       "1": "Resource",  "2": "Equipment",
    "3": "Structure", "4": "Machine",   "5": "Energy",
    "6": "Machine",   "7": "Rocket",    "8": "Automation",
    "9": "Toxicity",  "10": "Storage",
}

# Maps equipableType integer -> app category label for assets that have no
# groupCategory. Values confirmed from item names in scan_categories.py output.
EQUIP_TYPE_MAP = {
    "0":  "Consumable",     # seeds, growables, animal food
    "1":  "Equipment",      # OxygenTank
    "2":  "Equipment",      # Backpack
    "3":  "Equipment",      # EquipmentIncrease (inventory upgrades)
    "4":  "MultiTool Chip", # MultiToolLight, VehicleLights
    "5":  "MultiTool Chip", # MultiToolDeconstruct
    "6":  "MultiTool Chip", # MultiBuild
    "7":  "MultiTool Chip", # MultiToolMineSpeed
    "8":  "Speed",          # BootsSpeed, VehicleSpeed
    "9":  "HUD Chip",       # HudCompass
    "10": "Equipment",      # Jetpack
    "11": "Filter",         # AirFilter
    "12": "HUD Chip",       # HudChipCleanConstruction
    "13": "HUD Chip",       # MapChip, VehicleBeacon
    "14": "HUD Chip",       # PinChip
    "15": None,             # Cosmetic skins -- excluded from recipes
    "16": "Vehicle Chip",   # VehicleLogistic
    "17": "MultiTool Chip", # MultiToolCleaningGooChip
    "18": "Filter",         # ToxinsFilter
    "19": "HUD Chip",       # ToxicZoneHudDisplayer
}

WORLD_UNIT_MAP = {
    "1": "Heat",    "2": "Pressure", "3": "Oxygen",
    "4": "Biomass", "5": "Plants",   "6": "Insects", "7": "Animals", "8": "Humidity",
}

# ---------------------------------------------------------------------------
# Unit conversion: raw game float -> (display_value, display_unit)
# The game stores all values in base units. We scale to a human-readable
# range and pick the appropriate SI prefix / label.
# ---------------------------------------------------------------------------

def _pick_scale(value: float, tiers: list[tuple[float, str]]) -> tuple[float, str]:
    """
    Walk tiers largest-first and return (scaled_value, unit_label) for the
    first tier whose divisor is <= value.  Falls back to the smallest tier.
    """
    for divisor, label in tiers:
        if value >= divisor:
            return value / divisor, label
    return value / tiers[-1][0], tiers[-1][1]


# Each stage maps to an ordered list of (divisor, unit_label) from largest to smallest.
STAGE_UNIT_TIERS: dict[str, list[tuple[float, str]]] = {
    # Heat: stored in nK
    "Heat": [
        (1_000_000_000.0, "K"),
        (1_000_000.0,     "\u03bcK"),   # μK
        (1_000.0,         "mK"),
        (1.0,             "nK"),
    ],
    # Pressure: stored in μPa
    "Pressure": [
        (1_000_000.0, "Pa"),
        (1_000.0,     "mPa"),
        (1.0,         "\u03bcPa"),      # μPa
    ],
    # Oxygen: stored in ppm (no conversion needed; keep as ppm)
    "Oxygen": [
        (1.0, "ppm"),
    ],
    # Biomass: stored in grams
    "Biomass": [
        (1_000_000_000.0, "kt"),
        (1_000_000.0,     "t"),
        (1_000.0,         "kg"),
        (1.0,             "g"),
    ],
    # Plants / Insects / Animals / Humidity: raw counts
    "Plants":   [
        (1_000_000_000.0, "B"),
        (1_000_000.0,     "M"),
        (1_000.0,         "k"),
        (1.0,             "units"),
    ],
    "Insects":  [
        (1_000_000_000.0, "B"),
        (1_000_000.0,     "M"),
        (1_000.0,         "k"),
        (1.0,             "units"),
    ],
    "Animals":  [
        (1_000_000_000.0, "B"),
        (1_000_000.0,     "M"),
        (1_000.0,         "k"),
        (1.0,             "units"),
    ],
    "Humidity": [
        (1_000_000_000.0, "B"),
        (1_000_000.0,     "M"),
        (1_000.0,         "k"),
        (1.0,             "units"),
    ],
}


def convert_unlock_value(stage: str, raw_value: float) -> tuple[float, str]:
    """
    Convert a raw game unlock value to a (display_threshold, unit) pair.
    Returns (raw_value, 'units') for any unknown stage.
    """
    tiers = STAGE_UNIT_TIERS.get(stage)
    if not tiers:
        return raw_value, "units"
    display_val, unit = _pick_scale(raw_value, tiers)
    # Round to 2 decimal places; strip trailing zeros so '2.00' stays '2.00'
    # but '500.00k' doesn't become '500.0000k'.
    display_val = round(display_val, 2)
    return display_val, unit


# ---------------------------------------------------------------------------
# Craft station detection
# ---------------------------------------------------------------------------

# Maps the crafterType integer from .asset files -> craftedIn display name.
# The integer enum is defined in the game source as CrafterType.
# Add new entries here if a future game update introduces a new station and
# you see "WARNING: Unknown crafterType" in the script output.
CRAFTER_TYPE_MAP = {
    "0": "Crafting Table",       # Default player inventory crafter
    "1": "Biolab",               # Biological laboratory station
    "2": "Quartz Craft Station", # Quartz-specific crafting station
    "3": "DNA Manipulator",      # DNA/genetics station
    "4": "Incubator",            # Egg/larva incubation station
    # Add further entries as discovered from new asset exports
}

# Keyword fragments in the item id that strongly imply a specific station.
# Checked ONLY when crafterType is absent from the asset.
# Keys are lowercase substrings to match against item_id.lower().
# Ordered from most-specific to least-specific.
ID_KEYWORD_STATION_MAP = [
    ("quartz",    "Quartz Craft Station"),  # QuasarQuartz, SolarQuartz, etc.
    ("biolab",    "Biolab"),
    ("mutagen",   "Biolab"),
    ("larva",     "Biolab"),
    ("bacteria",  "Biolab"),
    ("fabric",    "Biolab"),                # Smart Fabric / Fabric
    ("fertilizer","Biolab"),
    ("explosive", "Biolab"),
    ("flare",     "Biolab"),
    ("pulsar",    "Biolab"),
    ("dna",       "DNA Manipulator"),
]

# groupCategory values that represent player-placed constructibles (Build Menu).
# groupCategory 3 = Structure in CATEGORY_MAP.
BUILD_MENU_CATEGORIES = {"3"}


def resolve_craft_station(text: str, item_id: str, group_cat: str) -> str | None:
    """
    Determine the craftedIn station for an asset.

    Priority:
      1. crafterType field on the asset  ->  CRAFTER_TYPE_MAP
      2. id keyword heuristics           ->  ID_KEYWORD_STATION_MAP
      3. groupCategory is a Structure    ->  "Build Menu"
      4. Has ingredients                 ->  "Crafting Table"  (safe fallback)
    """
    # --- Priority 1: explicit crafterType field ---
    crafter_type = get_field(text, "crafterType")
    if crafter_type is not None:
        station = CRAFTER_TYPE_MAP.get(crafter_type)
        if station:
            return station
        # Unknown integer -- warn and fall through so the item still gets a value
        print(
            f"  WARNING: Unknown crafterType '{crafter_type}' on item '{item_id}' "
            f"-- add to CRAFTER_TYPE_MAP. Falling back to heuristics."
        )

    # --- Priority 2: id keyword heuristics ---
    id_lower = item_id.lower()
    for keyword, station in ID_KEYWORD_STATION_MAP:
        if keyword in id_lower:
            return station

    # --- Priority 3: Structure groupCategory -> Build Menu ---
    if group_cat in BUILD_MENU_CATEGORIES:
        return "Build Menu"

    # --- Priority 4: safe fallback ---
    return "Crafting Table"


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
        except Exception:
            continue

        if "recipeIngredients:" not in text:
            continue

        has_category   = bool(get_field(text, "groupCategory"))
        has_equipable  = bool(get_field(text, "equipableType"))

        # Exclude pure seeds/growables: no groupCategory and no equipableType
        # means this asset's recipeIngredients is for farming/recycler, not
        # player crafting. These would otherwise appear as 445 ghost entries.
        if not has_category and not has_equipable:
            continue

        craftable.append(asset_path)
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

    # Tally how each station was assigned and which method resolved it,
    # printed at the end so you can spot-check the heuristics.
    station_tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

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
        if group_cat:
            if group_cat not in CATEGORY_MAP:
                print(f"  WARNING: Unknown groupCategory '{group_cat}' in {asset_path.name} -- update CATEGORY_MAP")
            category = CATEGORY_MAP.get(group_cat, f"Unknown({group_cat})")
        else:
            # No groupCategory -- resolve via equipableType instead
            equip_type = get_field(text, "equipableType") or ""
            if equip_type not in EQUIP_TYPE_MAP:
                print(f"  WARNING: Unknown equipableType '{equip_type}' in {asset_path.name} -- update EQUIP_TYPE_MAP")
            category = EQUIP_TYPE_MAP.get(equip_type, f"Unknown(equip={equip_type})")
            if category is None:
                # Explicitly excluded (e.g. cosmetic skins) -- skip this asset
                continue

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
                # Use pascal_to_display() so ingredient names exactly match
                # the display names written for the items themselves.
                # e.g. 'Bioplastic1' -> 'Bioplastic T1', not 'Bioplastic'
                name_counts[pascal_to_display(resolved_id)] += 1

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
            display_threshold, display_unit = convert_unlock_value(stage, world_value)
            unlock_condition = {
                "stage":     stage,
                "threshold": display_threshold,
                "unit":      display_unit,
            }

        # --- Craft station ---
        # Only assign a station when there are actual ingredients; raw/found
        # items that have no recipe get None.
        crafted_in     = None
        station_method = "none (no ingredients)"
        if ingredients:
            crafted_in     = resolve_craft_station(text, item_id, group_cat)
            # Determine which resolution path fired for the tally
            crafter_type = get_field(text, "crafterType")
            if crafter_type and crafter_type in CRAFTER_TYPE_MAP:
                station_method = f"crafterType={crafter_type}"
            elif any(kw in item_id.lower() for kw, _ in ID_KEYWORD_STATION_MAP):
                station_method = "id_keyword"
            elif group_cat in BUILD_MENU_CATEGORIES:
                station_method = "build_menu_category"
            else:
                station_method = "fallback"
            station_tally[crafted_in][station_method] += 1

        recipes.append({
            "name":            display_name,
            "category":        category,
            "description":     "",
            "ingredients":     ingredients,
            "unlockCondition": unlock_condition,
            "craftedIn":       crafted_in,
            "recyclerYields":  bool(ingredients),
            "_sourceAsset":    asset_path.name,
            "_iconFile":       icon_file,
            "_stationMethod":  station_method,   # review helper, stripped by to_clean_recipe
        })

    print(f"  Icons resolved: {icons_found}  |  Icons not found: {icons_miss}")
    if miss_samples:
        print(f"  Sample unmatched keys (first {len(miss_samples)}):")
        for s in miss_samples:
            print(f"    {s}")

    # Print station tally so you can validate coverage at a glance
    print("\n  Craft station assignment summary:")
    for station, methods in sorted(station_tally.items()):
        total = sum(methods.values())
        breakdown = ", ".join(f"{m}:{n}" for m, n in sorted(methods.items()))
        print(f"    {station:<28}  {total:>4} items  ({breakdown})")

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
    print("  1. Check WARNING lines above for unknown crafterType values")
    print("  2. Review the station assignment summary -- 'fallback' items may need keyword rules")
    print("  3. Check 'Icons not found' count above -- 0 is ideal")
    print("  4. Fill in 'description' fields in recipes.json as needed")
    print("  5. Run the app and verify stations appear correctly on the Recipes page")


if __name__ == "__main__":
    main()
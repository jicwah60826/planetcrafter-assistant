# -*- coding: utf-8 -*-
"""
scan_categories.py
------------------
Scans all craftable .asset files and prints every distinct groupCategory
integer found, along with a sample item for each. Run this after a new
AssetRipper export to detect any new category integers before updating
CATEGORY_MAP in parse_asset_recipes.py.

Usage:
    python Tools\\scan_categories.py
    python Tools\\scan_categories.py --dump-missing
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

MONO_ROOT = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v_2.004_4_6_2026_ExportedProject\ExportedProject\Assets\MonoBehaviour")


def read_asset(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw.decode("utf-16-le")
    return raw.decode("utf-8", errors="replace")


def get_field(text: str, field: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(field)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


KNOWN = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}

# equipableType integers seen in the wild - update as more are confirmed
EQUIP_TYPE_MAP = {
    "0":  "None",
    "1":  "Backpack",
    "2":  "Jetpack",
    "3":  "BootsJump",
    "4":  "BootsSpeed",
    "5":  "HelmetOxygen",
    "6":  "MultiTool",
    "7":  "Drill",
    "8":  "HelmetLight",
    "9":  "Chest",
    "10": "Legs",
    "11": "Consumable",
}

found: dict         = defaultdict(list)
missing_paths: list = []

parser = argparse.ArgumentParser()
parser.add_argument("--dump-missing", action="store_true",
                    help="Print raw scalar fields of the first 3 MISSING assets")
parser.add_argument("--mono-root", default=str(MONO_ROOT))
args = parser.parse_args()
mono_root = Path(args.mono_root)

for asset_path in mono_root.rglob("*.asset"):
    try:
        text = read_asset(asset_path)
    except Exception:
        continue
    if "recipeIngredients:" not in text:
        continue
    cat = get_field(text, "groupCategory") or "MISSING"
    found[cat].append(get_field(text, "id") or asset_path.stem)
    if cat == "MISSING":
        missing_paths.append(asset_path)

print(f"\n{'Integer':<10} {'Count':<8} {'Status':<10} Sample items")
print("-" * 60)
for cat in sorted(found, key=lambda x: int(x) if x.isdigit() else 999):
    status = "known" if cat in KNOWN else "*** NEW ***"
    samples = ", ".join(found[cat][:3])
    print(f"{cat:<10} {len(found[cat]):<8} {status:<10} {samples}")

# Break down MISSING assets by their equipableType value so we can decide
# whether to map them to a category label or exclude them entirely.
if missing_paths:
    equip_buckets: dict = defaultdict(list)
    for p in missing_paths:
        try:
            text = read_asset(p)
        except Exception:
            continue
        equip_val = get_field(text, "equipableType") or "ABSENT"
        item_id   = get_field(text, "id") or p.stem
        equip_buckets[equip_val].append(item_id)

    print(f"\nMISSING breakdown by equipableType:")
    print(f"  {'equipableType':<16} {'Count':<8} {'Label':<14} Sample items")
    print(f"  {'-'*70}")
    for val in sorted(equip_buckets, key=lambda x: int(x) if x.isdigit() else 999):
        label   = EQUIP_TYPE_MAP.get(val, "*** UNKNOWN ***")
        samples = ", ".join(equip_buckets[val][:4])
        print(f"  {val:<16} {len(equip_buckets[val]):<8} {label:<14} {samples}")

# --dump-missing: print every scalar field from the first 3 MISSING assets
if args.dump_missing and missing_paths:
    print(f"\n{'='*60}")
    print(f"Raw scalar fields from first {min(3, len(missing_paths))} MISSING assets:")
    print(f"{'='*60}")
    for asset_path in missing_paths[:3]:
        try:
            text = read_asset(asset_path)
        except Exception:
            continue
        print(f"\n--- {asset_path.name} ---")
        for line in text.splitlines():
            if re.match(r"^\s{0,4}\w[\w ]*:\s+[^{{\[].+$", line):
                print(f"  {line.strip()}")
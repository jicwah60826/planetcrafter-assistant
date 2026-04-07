# -*- coding: utf-8 -*-
"""
diagnose_new_rip.py
-------------------
Inspects the new AssetRipper export to find craftable item structure.

Usage:
    python Tools\\diagnose_new_rip.py
"""

from pathlib import Path

MONO_ROOT   = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v_2.004_4_6_2026\ExportedProject\Assets\MonoBehaviour")
EXPORT_ROOT = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v_2.004_4_6_2026\ExportedProject")

# Common ingredient-related field names across AssetRipper versions
INGREDIENT_CANDIDATES = [
    "recipeIngredients",
    "ingredients",
    "craftingIngredients",
    "recipe",
    "craftRecipe",
    "m_Ingredients",
    "m_Recipe",
    "buildIngredients",
    "constructIngredients",
    "groupRecipe",
]


def read_file(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw.decode("utf-16-le")
    return raw.decode("utf-8", errors="replace")


def main():
    all_assets = list(MONO_ROOT.rglob("*.asset"))
    print(f"Total .asset files: {len(all_assets)}\n")

    # --- Search for each candidate field name ---
    print("Searching for ingredient-related field names across all assets...")
    for candidate in INGREDIENT_CANDIDATES:
        hits = []
        for asset in all_assets:
            try:
                if candidate in read_file(asset):
                    hits.append(asset.name)
            except Exception:
                continue
        if hits:
            print(f"\n  FOUND '{candidate}' in {len(hits)} files:")
            for name in hits[:3]:
                print(f"    {name}")
        else:
            print(f"  not found: '{candidate}'")

    # --- Show full content of first file that has 'id:' field ---
    print("\n\nSearching for first asset with 'id:' field...")
    for asset in sorted(all_assets):
        try:
            text = read_file(asset)
            if "\n  id:" in text or "\r\n  id:" in text:
                print(f"\n--- Full content of: {asset.name} ---")
                for line in text.splitlines()[:60]:
                    print(f"  {line}")
                break
        except Exception:
            continue

    # --- Show the file most likely to be a craftable item ---
    # Look for files with both 'id:' and any list-like field
    print("\n\nFirst 5 assets containing 'id:' field:")
    count = 0
    for asset in sorted(all_assets):
        try:
            text = read_file(asset)
            if "\n  id:" in text or "\r\n  id:" in text:
                print(f"\n  [{asset.name}]")
                for line in text.splitlines()[:40]:
                    print(f"    {line}")
                count += 1
                if count >= 3:
                    break
        except Exception:
            continue


if __name__ == "__main__":
    main()
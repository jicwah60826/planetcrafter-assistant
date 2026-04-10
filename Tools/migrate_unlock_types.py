"""
One-time migration: adds "type": "terraformation" to every unlockCondition
in recipes.json that has a "stage" field but no "type" field.

Usage:
    python Tools/migrate_unlock_types.py
"""

import json
from pathlib import Path

RECIPES_PATH = Path(__file__).parent.parent / "wwwroot" / "data" / "recipes.json"


def migrate(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        recipes = json.load(f)

    updated = 0
    for recipe in recipes:
        uc = recipe.get("unlockCondition")
        if uc and "stage" in uc and "type" not in uc:
            uc["type"] = "terraformation"
            # Reorder so "type" is the first key for readability
            recipe["unlockCondition"] = {"type": "terraformation", **{k: v for k, v in uc.items() if k != "type"}}
            updated += 1

    with path.open("w", encoding="utf-8") as f:
        json.dump(recipes, f, indent=4, ensure_ascii=False)

    print(f"Done — {updated} unlock condition(s) updated in {path.name}")


if __name__ == "__main__":
    migrate(RECIPES_PATH)
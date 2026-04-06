# -*- coding: utf-8 -*-
"""
diagnose_icon_guid.py
---------------------
Searches the entire AssetRipper export for a specific GUID and prints
every .meta file that contains it, showing surrounding context.

Usage:
    python Tools\\diagnose_icon_guid.py
    python Tools\\diagnose_icon_guid.py --guid YOUR_GUID_HERE
"""

import argparse
import re
from pathlib import Path

EXPORT_ROOT  = Path(r"D:\PlanetCrafterAssistant\AssetRipper\v3\ExportedProject")
DEFAULT_GUID = "d05a4351810f9c14c9f8ee28cfe0f2c3"


def read_file(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw.decode("utf-16-le")
    return raw.decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guid",        default=DEFAULT_GUID, help="GUID to search for")
    parser.add_argument("--export-root", default=str(EXPORT_ROOT))
    args = parser.parse_args()
    guid = args.guid.lower()
    root = Path(args.export_root)

    print(f"Searching for GUID: {guid}")
    print(f"Under: {root}\n")

    found = 0
    for meta in root.rglob("*.meta"):
        try:
            text = read_file(meta)
        except Exception:
            continue

        if guid in text.lower():
            found += 1
            print(f"FOUND in: {meta}")
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if guid in line.lower():
                    start = max(0, i - 2)
                    end   = min(len(lines), i + 5)
                    for ctx in lines[start:end]:
                        print(f"  {ctx}")
                    print()
            if found >= 5:
                print("(Stopping after 5 matches - run with a specific --guid to see all)")
                break

    if found == 0:
        print("GUID not found in any .meta file.")
        print("\nThis means the icon GUID is a sub-asset spriteID embedded inside a PNG meta.")
        print("The main script will need to scan spriteSheet entries to resolve it.")
    else:
        print(f"\nTotal matches: {found}")


if __name__ == "__main__":
    main()
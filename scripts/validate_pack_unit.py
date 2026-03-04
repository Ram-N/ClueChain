#!/usr/bin/env python3
"""
Pack Unit JSON Validator

Validates a pack unit JSON file produced by generate_pack_unit.py.

Usage:
    uv run python scripts/validate_pack_unit.py assets/data/units/literature/tale-of-two-cities.json
    uv run python scripts/validate_pack_unit.py assets/data/units/news/2026/03/04.json
"""

import json
import sys
from pathlib import Path

REQUIRED_TOP_KEYS = {"schema_version", "unit_id", "unit_type", "title", "items"}
REQUIRED_ITEM_KEYS = {"item_id", "title", "text", "authored_variants"}
VALID_CLUE_TYPES = {"Indirect", "Suggestive", "Straight"}
VALID_POINTS = {
    "Indirect":   {5, 6, 7},
    "Suggestive": {3, 4},
    "Straight":   {1, 2},
}


def validate(path: Path) -> list[str]:
    """Return a list of error strings; empty list means the file is valid."""
    errors = []

    # ---- Load ----
    try:
        with path.open(encoding="utf-8") as f:
            unit = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"]
    except OSError as e:
        return [f"Cannot read file: {e}"]

    # ---- Top-level keys ----
    missing_top = REQUIRED_TOP_KEYS - set(unit.keys())
    if missing_top:
        errors.append(f"Missing top-level keys: {missing_top}")

    # ---- Items ----
    items = unit.get("items")
    if not isinstance(items, list) or len(items) == 0:
        errors.append("'items' must be a non-empty list")
        return errors  # nothing more to validate

    for item_idx, item in enumerate(items, 1):
        prefix = f"Item {item_idx} ('{item.get('item_id', '?')}')"

        missing_item = REQUIRED_ITEM_KEYS - set(item.keys())
        if missing_item:
            errors.append(f"{prefix}: missing keys {missing_item}")

        item_text = item.get("text", "")

        authored = item.get("authored_variants", [])
        if not isinstance(authored, list) or len(authored) == 0:
            errors.append(f"{prefix}: 'authored_variants' must be a non-empty list")
            continue

        for v_idx, variant in enumerate(authored, 1):
            v_prefix = f"{prefix}, variant {v_idx}"

            blanks = variant.get("blanks")
            if not isinstance(blanks, list):
                errors.append(f"{v_prefix}: 'blanks' must be a list")
                continue

            if not (4 <= len(blanks) <= 10):
                errors.append(f"{v_prefix}: expected 4–10 blanks, got {len(blanks)}")

            for b_idx, blank in enumerate(blanks, 1):
                b_prefix = f"{v_prefix}, blank {b_idx}"

                word = blank.get("word", "")
                if not word:
                    errors.append(f"{b_prefix}: missing 'word'")
                    continue

                if word.lower() not in item_text.lower():
                    errors.append(f"{b_prefix}: word '{word}' not found in item text")

                clues = blank.get("clues")
                if not isinstance(clues, list):
                    errors.append(f"{b_prefix} ('{word}'): 'clues' must be a list")
                    continue

                if len(clues) != 3:
                    errors.append(
                        f"{b_prefix} ('{word}'): must have exactly 3 clues, got {len(clues)}"
                    )

                seen_types: set = set()
                for c_idx, clue_obj in enumerate(clues, 1):
                    c_prefix = f"{b_prefix} ('{word}'), clue {c_idx}"

                    clue_type = clue_obj.get("type", "")
                    clue_text = clue_obj.get("clue", "")
                    points    = clue_obj.get("points")

                    if clue_type not in VALID_CLUE_TYPES:
                        errors.append(
                            f"{c_prefix}: invalid type '{clue_type}', "
                            f"must be one of {VALID_CLUE_TYPES}"
                        )
                        continue

                    if clue_type in seen_types:
                        errors.append(f"{c_prefix}: duplicate clue type '{clue_type}'")
                    seen_types.add(clue_type)

                    if not clue_text.strip():
                        errors.append(f"{c_prefix}: empty clue text")

                    if word.lower() in clue_text.lower():
                        errors.append(
                            f"{c_prefix}: clue text contains the answer word '{word}'"
                        )

                    if points not in VALID_POINTS.get(clue_type, set()):
                        errors.append(
                            f"{c_prefix}: invalid points {points} for type '{clue_type}', "
                            f"must be one of {VALID_POINTS.get(clue_type)}"
                        )

                missing_types = VALID_CLUE_TYPES - seen_types
                if missing_types:
                    errors.append(
                        f"{b_prefix} ('{word}'): missing clue types {missing_types}"
                    )

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/validate_pack_unit.py <path-to-unit.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)

    print(f"🔍 Validating: {path}")
    errors = validate(path)

    if not errors:
        # Quick summary
        with path.open(encoding="utf-8") as f:
            unit = json.load(f)
        total_blanks = sum(
            len(v.get("blanks", []))
            for item in unit.get("items", [])
            for v in item.get("authored_variants", [])
        )
        print(f"✅ Valid — {len(unit['items'])} items, {total_blanks} blanks total")
        print(f"   Unit ID:   {unit.get('unit_id')}")
        print(f"   Unit type: {unit.get('unit_type')}")
        print(f"   Title:     {unit.get('title')}")
    else:
        print(f"❌ Found {len(errors)} error(s):\n")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Rebuild mmdd_slot_scores.csv from paragraph_scores.json and old_new_mapping.csv.

Usage:
    python scripts/regenerate_slot_scores.py
"""

import csv
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SCORES_FILE = SCRIPT_DIR / "output" / "paragraph_scores.json"
SLOT_SCORES_CSV = SCRIPT_DIR / "output" / "mmdd_slot_scores.csv"
MAPPING_CSV = SCRIPT_DIR.parent / "assets" / "data" / "old_new_mapping.csv"


def load_mapping(mapping_file: Path) -> dict:
    """Load old_new_mapping.csv into {mmdd: {score_file, title}} dict.

    CSV columns: mmdd, new_file, new_title, old_file, old_title, match
    - new_file: MMDD-style filename (e.g. 0101.json)
    - old_file: current filename in assets/data/ (e.g. 01-01-invisible.json)
    We try old_file first (current name), then fall back to new_file (MMDD name).
    """
    mapping = {}
    with open(mapping_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mmdd = row["mmdd"]
            mapping[mmdd] = {
                "new_file": row.get("new_file", "").strip(),
                "old_file": row.get("old_file", "").strip(),
                "new_title": row.get("new_title", ""),
            }
    return mapping


def regenerate_slot_scores(all_scores: dict, mapping: dict, output_path: Path):
    """Rebuild mmdd_slot_scores.csv from current scores and mapping."""
    rows = []
    for mmdd in sorted(mapping.keys()):
        entry = mapping[mmdd]
        date_str = f"{mmdd[:2]}-{mmdd[2:]}"
        old_file = entry.get("old_file", "").strip()

        new_file = entry.get("new_file", "").strip()

        score_key = ""
        total_score = 0.0
        rating = ""

        # Try old_file (current name in assets/data), then new_file (MMDD name)
        if old_file and old_file in all_scores:
            score_key = old_file
        elif new_file and new_file in all_scores:
            score_key = new_file
        elif f"{mmdd}.json" in all_scores:
            score_key = f"{mmdd}.json"

        if score_key and score_key in all_scores:
            total_score = all_scores[score_key].get("total_score", 0)
            rating = all_scores[score_key].get("overall_rating", "")

        rows.append({
            "mmdd": mmdd,
            "date": date_str,
            "score_key": score_key,
            "total_score": total_score,
            "rating": rating,
            "title": entry.get("new_title", ""),
        })

    rows.sort(key=lambda r: r["total_score"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["mmdd", "date", "score_key", "total_score", "rating", "title"]
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main():
    if not SCORES_FILE.exists():
        print(f"Error: {SCORES_FILE} not found. Run score_paragraphs.py first.")
        raise SystemExit(1)
    if not MAPPING_CSV.exists():
        print(f"Error: {MAPPING_CSV} not found.")
        raise SystemExit(1)

    all_scores = json.load(open(SCORES_FILE, encoding="utf-8"))
    mapping = load_mapping(MAPPING_CSV)

    rows = regenerate_slot_scores(all_scores, mapping, SLOT_SCORES_CSV)

    good = sum(1 for r in rows if r["rating"] == "good")
    okay = sum(1 for r in rows if r["rating"] == "okay")
    poor = sum(1 for r in rows if r["rating"] == "poor")
    unscored = sum(1 for r in rows if not r["score_key"])

    print(f"Regenerated {len(rows)} slot scores → {SLOT_SCORES_CSV}")
    print(f"  Good: {good}  Okay: {okay}  Poor: {poor}  Unscored: {unscored}")


if __name__ == "__main__":
    main()

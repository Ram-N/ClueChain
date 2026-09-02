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
CHRONO_SCORES_CSV = SCRIPT_DIR / "output" / "chrono_mmdd_slot_scores.csv"
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


MMDD_DIR = SCRIPT_DIR.parent / "assets" / "data" / "puzzles" / "daily" / "mmdd"

# Sub-score dimensions to pull from paragraph_scores.json
_SCORE_DIMS = [
    "word_quality", "variety", "readability",
    "connectivity", "clueability", "discovery_curve", "narrative_interest",
]
_PENALTY_DIMS = ["title_spoiler", "clue_leaks", "length_penalty", "catalog_penalty",
                 "technical_notation_penalty"]


def _load_puzzle_stats(mmdd: str) -> dict:
    """Load word_count and num_hidden_words from the puzzle JSON file."""
    puzzle_path = MMDD_DIR / f"{mmdd}.json"
    if not puzzle_path.exists():
        return {"word_count": "", "num_hidden_words": ""}
    try:
        with open(puzzle_path, encoding="utf-8") as f:
            data = json.load(f)
        word_count = len(data.get("text", "").split())
        num_hidden = len(data.get("hiddenWords", []))
        return {"word_count": word_count, "num_hidden_words": num_hidden}
    except (json.JSONDecodeError, KeyError):
        return {"word_count": "", "num_hidden_words": ""}


_FIELDNAMES = [
    "mmdd", "date", "score_key", "total_score", "rating", "title",
    "word_count", "num_hidden_words",
    *_SCORE_DIMS,
    *_PENALTY_DIMS,
]


def _build_rows(all_scores: dict, mapping: dict) -> list:
    """Build row dicts from scores and mapping (unsorted)."""
    rows = []
    for mmdd in mapping:
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

        # Extract scores and sub-dimensions
        scores_dict = {}
        if score_key and score_key in all_scores:
            score_entry = all_scores[score_key]
            total_score = score_entry.get("total_score", 0)
            rating = score_entry.get("overall_rating", "")
            scores_dict = score_entry.get("scores", {})

        # Get word count and hidden word count from the puzzle file
        puzzle_stats = _load_puzzle_stats(mmdd)

        row = {
            "mmdd": mmdd,
            "date": date_str,
            "score_key": score_key,
            "total_score": total_score,
            "rating": rating,
            "title": entry.get("new_title", ""),
            "word_count": puzzle_stats["word_count"],
            "num_hidden_words": puzzle_stats["num_hidden_words"],
        }

        for dim in _SCORE_DIMS:
            row[dim] = scores_dict.get(dim, "")
        for dim in _PENALTY_DIMS:
            row[dim] = scores_dict.get(dim, "")

        rows.append(row)

    return rows


def _write_csv(rows: list, output_path: Path):
    """Write rows to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def regenerate_slot_scores(all_scores: dict, mapping: dict,
                           score_path: Path, chrono_path: Path):
    """Rebuild both CSV files: score-sorted and chronologically-sorted."""
    rows = _build_rows(all_scores, mapping)

    # Score-sorted (ascending — worst first)
    by_score = sorted(rows, key=lambda r: r["total_score"])
    _write_csv(by_score, score_path)

    # Chronologically sorted (Jan 1 → Dec 31)
    by_date = sorted(rows, key=lambda r: r["mmdd"])
    _write_csv(by_date, chrono_path)

    return by_score


def main():
    if not SCORES_FILE.exists():
        print(f"Error: {SCORES_FILE} not found. Run score_paragraphs.py first.")
        raise SystemExit(1)
    if not MAPPING_CSV.exists():
        print(f"Error: {MAPPING_CSV} not found.")
        raise SystemExit(1)

    all_scores = json.load(open(SCORES_FILE, encoding="utf-8"))
    mapping = load_mapping(MAPPING_CSV)

    rows = regenerate_slot_scores(all_scores, mapping, SLOT_SCORES_CSV, CHRONO_SCORES_CSV)

    good = sum(1 for r in rows if r["rating"] == "good")
    okay = sum(1 for r in rows if r["rating"] == "okay")
    poor = sum(1 for r in rows if r["rating"] == "poor")
    unscored = sum(1 for r in rows if not r["score_key"])

    print(f"Regenerated {len(rows)} slot scores:")
    print(f"  By score (worst first): {SLOT_SCORES_CSV}")
    print(f"  By date (Jan→Dec):      {CHRONO_SCORES_CSV}")
    print(f"  Good: {good}  Okay: {okay}  Poor: {poor}  Unscored: {unscored}")


if __name__ == "__main__":
    main()

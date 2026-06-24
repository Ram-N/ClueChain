#!/usr/bin/env python3
"""
Replace lowest-scoring ClueChain puzzles with higher-scoring staged files.

Workflow:
    1. Place new puzzle JSONs in assets/data/staging/
    2. Run: python scripts/replace_lowest.py --dry-run    (preview)
    3. Run: python scripts/replace_lowest.py              (execute)

The script:
    - Scores each staged file (calls score_paragraphs.py)
    - Reads mmdd_slot_scores.csv to find the lowest-scoring slots
    - Replaces worst slots with best new files (only if new > old)
    - Archives old files, updates scores, mapping, and mmdd copies
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "assets" / "data"
STAGING_DIR = DATA_DIR / "staging"
ARCHIVE_DIR = DATA_DIR / "archive"
MMDD_DIR = DATA_DIR / "puzzles" / "daily" / "mmdd"
SCORES_FILE = SCRIPT_DIR / "output" / "paragraph_scores.json"
SLOT_SCORES_CSV = SCRIPT_DIR / "output" / "mmdd_slot_scores.csv"
MAPPING_CSV = DATA_DIR / "old_new_mapping.csv"
SCORE_SCRIPT = SCRIPT_DIR / "score_paragraphs.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Add trailing newline
    with open(path, "a") as f:
        f.write("\n")


def load_scores():
    return load_json(SCORES_FILE)


def save_scores(data):
    save_json(SCORES_FILE, data)


def load_slot_scores():
    """Load mmdd_slot_scores.csv → list of dicts, sorted by total_score ascending."""
    with open(SLOT_SCORES_CSV) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["total_score"] = float(r["total_score"]) if r["total_score"] else 0.0
    rows.sort(key=lambda r: r["total_score"])
    return rows


def load_mapping():
    """Load old_new_mapping.csv → dict keyed by mmdd."""
    with open(MAPPING_CSV) as f:
        rows = list(csv.DictReader(f))
    return {r["mmdd"]: r for r in rows}


def save_mapping(mapping):
    """Write old_new_mapping.csv from dict keyed by mmdd."""
    fieldnames = ["mmdd", "new_file", "new_title", "old_file", "old_title", "match"]
    rows = [mapping[m] for m in sorted(mapping.keys())]
    with open(MAPPING_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def slugify(text):
    """Convert text to a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")



def score_staged_file(filepath):
    """
    Score a single file via score_paragraphs.py --file.
    Returns total_score or None on failure.
    """
    result = subprocess.run(
        [sys.executable, str(SCORE_SCRIPT), "--file", str(filepath)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ERROR scoring {filepath.name}:")
        for line in result.stderr.strip().split("\n")[-3:]:
            print(f"    {line}")
        return None

    scores = load_scores()
    entry = scores.get(filepath.name)
    if entry:
        return entry.get("total_score", 0)
    return None


def archive_file(src_path, archive_name):
    """Move a file to the archive directory."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dst = ARCHIVE_DIR / archive_name
    # Avoid overwriting existing archives
    if dst.exists():
        base, ext = os.path.splitext(archive_name)
        i = 1
        while dst.exists():
            dst = ARCHIVE_DIR / f"{base}_{i}{ext}"
            i += 1
    shutil.move(str(src_path), str(dst))
    return dst.name


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Replace lowest-scoring puzzles with staged files"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview replacements without making changes",
    )
    args = parser.parse_args()

    # --- 1. Discover staged files ---
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    staged_files = sorted(STAGING_DIR.glob("*.json"))

    if not staged_files:
        print("No JSON files in assets/data/staging/. Nothing to do.")
        return

    print(f"Found {len(staged_files)} staged file(s):\n")
    for sf in staged_files:
        print(f"  {sf.name}")

    # --- 2. Score each staged file ---
    print("\n--- Scoring staged files ---\n")
    staged_scores = []  # (path, total_score)

    for sf in staged_files:
        # Check if already scored (from a previous run)
        all_scores = load_scores()
        if sf.name in all_scores:
            score = all_scores[sf.name]["total_score"]
            print(f"  {sf.name}: {score:.1f} (already scored)")
        else:
            print(f"  Scoring {sf.name}...", end=" ", flush=True)
            score = score_staged_file(sf)
            if score is None:
                print("FAILED — skipping")
                continue
            print(f"{score:.1f}")

        staged_scores.append((sf, score))

    if not staged_scores:
        print("\nNo staged files could be scored. Exiting.")
        return

    # Sort best first
    staged_scores.sort(key=lambda x: x[1], reverse=True)

    # --- 3. Load slot scores and find lowest ---
    slot_scores = load_slot_scores()  # sorted worst-first
    n = len(staged_scores)

    # --- 4. Pair and filter ---
    replacements = []
    for i, (staged_path, staged_score) in enumerate(staged_scores):
        if i >= len(slot_scores):
            break
        slot = slot_scores[i]
        if staged_score > slot["total_score"]:
            replacements.append((staged_path, staged_score, slot))
        else:
            print(
                f"\nSkipping {staged_path.name} (score {staged_score:.1f}) — "
                f"not higher than slot {slot['mmdd']} ({slot['total_score']:.1f})"
            )

    if not replacements:
        print("\nNo staged files score higher than existing slots. Nothing replaced.")
        return

    # --- 5. Print replacement table ---
    hdr_new = "New File"
    hdr_rep = "Replaces (slot)"
    hdr_old_title = "Old Title"
    print(f"\n{'=' * 90}")
    print(f"{'REPLACEMENT PLAN':^90}")
    print(f"{'=' * 90}")
    print(
        f"  {'Slot':<6} {'New Score':>9} {'Old Score':>9}  "
        f"{'New File':<30} {'Replaces':<30}"
    )
    print(f"  {'-' * 6} {'-' * 9} {'-' * 9}  {'-' * 30} {'-' * 30}")
    for staged_path, staged_score, slot in replacements:
        old_title = slot["title"][:28]
        new_title_short = staged_path.stem[:28]
        print(
            f"  {slot['mmdd']:<6} {staged_score:>9.1f} {slot['total_score']:>9.1f}  "
            f"{staged_path.name:<30} {old_title:<30}"
        )

    print(f"\n  {len(replacements)} replacement(s) planned.\n")

    if args.dry_run:
        print("[DRY RUN] No changes made.")
        return

    # --- 6. Execute replacements ---
    all_scores = load_scores()
    mapping = load_mapping()

    for staged_path, staged_score, slot in replacements:
        mmdd = slot["mmdd"]
        date_str = slot["date"]  # MM-DD
        score_key = slot["score_key"]

        print(f"\n--- Replacing slot {mmdd} ({date_str}) ---")

        # 6a. Archive old mmdd file
        mmdd_path = MMDD_DIR / f"{mmdd}.json"
        if mmdd_path.exists():
            old_slug = slugify(slot["title"])[:30]
            archive_name = f"{mmdd}_{old_slug}.json"
            archived_as = archive_file(mmdd_path, archive_name)
            print(f"  Archived mmdd: {mmdd}.json -> archive/{archived_as}")

        # 6b. Archive old root file (if it exists)
        if score_key and (DATA_DIR / score_key).exists():
            archived_as = archive_file(DATA_DIR / score_key, score_key)
            print(f"  Archived root: {score_key} -> archive/{archived_as}")

        # 6c. Load staged JSON, update date, write to mmdd
        puzzle_data = load_json(staged_path)
        puzzle_data["date"] = date_str

        save_json(mmdd_path, puzzle_data)
        print(f"  Written mmdd:  {mmdd}.json")

        # 6d. Update paragraph_scores.json (keyed by mmdd filename)
        #     Build the new entry from the staged file's score data, then
        #     write it under mmdd_key. Never pop by staged_basename — it may
        #     collide with an unrelated mmdd slot's key and clobber it.
        mmdd_key = f"{mmdd}.json"
        staged_basename = staged_path.name

        # Remove the OLD slot's score entry (the one being replaced)
        if score_key and score_key in all_scores and score_key != mmdd_key:
            del all_scores[score_key]

        # Build new entry from staged score data (if available)
        if staged_basename in all_scores and staged_basename != mmdd_key:
            # Staged file has a different name — copy its data, don't pop
            entry = dict(all_scores[staged_basename])
            entry["date"] = date_str
            all_scores[mmdd_key] = entry
            # Clean up the staging-only key
            del all_scores[staged_basename]
        elif staged_basename in all_scores and staged_basename == mmdd_key:
            # Staged file already named for the target slot — update in place
            all_scores[mmdd_key]["date"] = date_str
        else:
            new_title = puzzle_data.get("title", staged_path.stem)
            all_scores[mmdd_key] = {
                "title": new_title,
                "date": date_str,
                "total_score": staged_score,
                "overall_rating": "good" if staged_score >= 75 else "okay" if staged_score >= 50 else "poor",
                "scores": {},
                "has_llm_scores": False,
            }

        # 6e. Update old_new_mapping.csv
        new_title = puzzle_data.get("title", staged_path.stem)
        mapping[mmdd] = {
            "mmdd": mmdd,
            "new_file": f"{mmdd}.json",
            "new_title": new_title,
            "old_file": f"{mmdd}.json",
            "old_title": new_title,
            "match": "identical",
        }

        # 6g. Remove staged file
        staged_path.unlink()
        print(f"  Removed staged: {staged_path.name}")

    # --- 7. Save updated files ---
    save_scores(all_scores)
    print("\nUpdated paragraph_scores.json")

    save_mapping(mapping)
    print("Updated old_new_mapping.csv")

    # --- 8. Regenerate slot scores CSV ---
    print("Regenerating mmdd_slot_scores.csv...")
    regenerate_slot_scores(all_scores, mapping)

    # --- 9. Regenerate rankings ---
    print("Regenerating rankings...")
    subprocess.run(
        [sys.executable, str(SCORE_SCRIPT), "--batch-size", "0"],
        capture_output=True, text=True,
    )
    print("Rankings regenerated.")

    # --- 10. Summary ---
    print(f"\n{'=' * 90}")
    print(f"  DONE: {len(replacements)} puzzle(s) replaced.")
    print(f"{'=' * 90}")


def regenerate_slot_scores(all_scores, mapping):
    """Rebuild mmdd_slot_scores.csv from current scores and mapping."""
    from regenerate_slot_scores import regenerate_slot_scores as _regen
    _regen(all_scores, mapping, SLOT_SCORES_CSV)


if __name__ == "__main__":
    main()

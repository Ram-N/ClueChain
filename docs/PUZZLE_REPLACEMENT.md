# Puzzle Replacement Workflow

ClueChain has 366 daily puzzle slots (one per MM-DD). As new, higher-quality paragraphs are created, the replacement workflow swaps them into the lowest-scoring slots.

## Overview

```
New puzzle JSON  →  assets/data/staging/  →  replace_lowest.py  →  replaces worst slot
```

The workflow relies on three data files that track slot assignments and scores:

| File | Purpose |
|------|---------|
| `scripts/output/mmdd_slot_scores.csv` | Every MMDD slot with its score key and total score, sorted worst-first |
| `scripts/output/paragraph_scores.json` | Detailed scores for every scored puzzle (keyed by filename) |
| `assets/data/old_new_mapping.csv` | Maps each MMDD slot to its root-level file |

## Scripts

### `scripts/replace_lowest.py`

Replaces the lowest-scoring puzzle slots with higher-scoring staged files.

```bash
# 1. Place new puzzle JSON(s) into staging
cp my-new-puzzle.json assets/data/staging/

# 2. Preview replacements
python scripts/replace_lowest.py --dry-run

# 3. Execute
python scripts/replace_lowest.py
```

**What it does per replacement:**

1. Scores each staged file (calls `score_paragraphs.py --file`)
2. Reads `mmdd_slot_scores.csv` to find the lowest-scoring slots
3. Pairs best new → worst slot (only replaces if new score > old score)
4. Archives old files to `assets/data/replaced-puzzles/`
5. Writes new puzzle to both `assets/data/MM-DD-slug.json` and `puzzles/daily/mmdd/MMDD.json`
6. Updates `paragraph_scores.json`, `old_new_mapping.csv`, and `mmdd_slot_scores.csv`
7. Regenerates `paragraph_rankings.csv`

**Flags:**

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would be replaced without making changes |

### `scripts/show_score.py`

Look up scores for any puzzle file by name or partial match.

```bash
# Exact filename
python scripts/show_score.py 07-04.json

# Partial match on filename or title
python scripts/show_score.py tale

# MMDD key
python scripts/show_score.py 0527
```

Displays: title, date, total score, rating, all dimension scores, and LLM reasoning.

## Data Files

### `scripts/output/mmdd_slot_scores.csv`

One row per MMDD slot (366 rows), sorted by `total_score` ascending (worst first).

| Column | Description |
|--------|-------------|
| `mmdd` | Slot identifier (e.g., `0527`) |
| `date` | MM-DD format (e.g., `05-27`) |
| `score_key` | Filename key in `paragraph_scores.json` |
| `total_score` | Score out of 100 |
| `rating` | `good` (≥75) / `okay` (50-74) / `poor` (<50) |
| `title` | Current puzzle title |

### `assets/data/old_new_mapping.csv`

One row per MMDD slot (366 rows). Maps each slot to its root-level source file.

| Column | Description |
|--------|-------------|
| `mmdd` | Slot identifier |
| `new_file` | Filename in `puzzles/daily/mmdd/` (always `MMDD.json`) |
| `new_title` | Title of the puzzle currently in the mmdd slot |
| `old_file` | Root-level filename in `assets/data/` (empty if mmdd-only) |
| `old_title` | Title of the root-level file |
| `match` | `identical` (mmdd matches root), `different` (mmdd was replaced), or empty |

### `assets/data/replaced-puzzles/`

Replaced puzzle files are moved here. Named as `MMDD_slugified-title.json`.

### `assets/data/staging/`

Drop new puzzle JSONs here before running `replace_lowest.py`.

## Typical Session

```bash
# Check current bottom scores
head -20 scripts/output/mmdd_slot_scores.csv

# Look up a specific puzzle's score
python scripts/show_score.py 0527

# Stage new puzzles
cp new-puzzles/*.json assets/data/staging/

# Preview
python scripts/replace_lowest.py --dry-run

# Execute
python scripts/replace_lowest.py

# Verify coverage is still 366/366
./scripts/dashboard.sh
```

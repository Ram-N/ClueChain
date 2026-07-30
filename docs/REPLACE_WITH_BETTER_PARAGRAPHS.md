# Puzzle Replacement Workflow

End-to-end steps for generating new puzzles and replacing low-scoring slots.

The staging directory should start empty each session. New puzzles are generated
into staging, scored, then paired against the worst active slots automatically.

---

## Step 1 — Gather source paragraphs

Collect paragraph text into a plain `.txt` file in `scripts/input/`.
For batch runs, separate paragraphs with `===`. Each paragraph should
have a `Title: ...` line before its text.

```
scripts/input/my_paragraphs.txt
```

---

## Step 2 — Generate puzzle JSONs into staging

Generate directly into `assets/data/staging/` so live puzzles are never touched.
The `--day` and `--category` values are only used for temporary filenames —
`replace_lowest.py` reassigns the actual date when it slots them in.

**Dry-run first** to verify parsing:
```bash
python scripts/batch_generate_cluechain_json.py \
  --file scripts/input/my_paragraphs.txt \
  --category MYTOPIC \
  --day 1 \
  --output-dir assets/data/staging \
  --dry-run
```

**Generate for real:**
```bash
python scripts/batch_generate_cluechain_json.py \
  --file scripts/input/my_paragraphs.txt \
  --category MYTOPIC \
  --day 1 \
  --output-dir assets/data/staging \
  --continue-on-error \
  --delay 15
```

**Single paragraph** (alternative):
```bash
python scripts/generate_cluechain_json.py \
  --file scripts/input/single.txt \
  --title "My Title" \
  --date 01-01 \
  --output-dir assets/data/staging
```

---

## Step 3 — Score the staged files

Score using `--file` to target only the staged files, and `--groq` for LLM scoring:

```bash
# Rule-based + LLM scoring
python scripts/score_paragraphs.py --file assets/data/staging/*.json --groq

# Rule-based only (no API calls, faster but partial scores)
python scripts/score_paragraphs.py --file assets/data/staging/*.json --batch-size 0
```

Check individual scores:
```bash
python scripts/show_score.py <filename>
```

**Review scores and remove any low-scoring files from staging before proceeding.**
Only files in `staging/` are candidates for replacement — delete anything you
don't want used.

---

## Step 4 — Preview and execute replacements

```bash
# Always dry-run first
python scripts/replace_lowest.py --dry-run

# If the plan looks good, run for real
python scripts/replace_lowest.py
```

This automatically:
- Pairs staged files (best first) against worst-scoring active slots
- Only replaces if the new score > old score
- Archives old puzzles to `assets/data/replaced-puzzles/`
- Reassigns the date in the new puzzle JSON to match the slot
- Updates scores, rankings, mapping, and slot scores

---

## Step 5 — Verify and commit

```bash
# Check updated rankings
cat scripts/output/paragraph_rankings.md

# Verify slot scores — new puzzles should appear, replaced ones should be gone
head -20 scripts/output/mmdd_slot_scores.csv

# Commit and push
git add -A && git commit -m "feat(puzzles): replace N low-scoring puzzles"
git push
```

`replace_lowest.py` automatically regenerates `mmdd_slot_scores.csv` —
new puzzles are added with their scores and archived puzzles are removed.

---

## Key files

| File | Purpose |
|------|---------|
| `scripts/input/` | Source text files (input paragraphs) |
| `assets/data/staging/` | Generated puzzles waiting to replace slots |
| `assets/data/replaced-puzzles/` | Archived old puzzles that were replaced |
| `scripts/output/mmdd_slot_scores.csv` | All slots sorted worst-first |
| `scripts/output/paragraph_scores.json` | Scoring checkpoint (resumable) |
| `scripts/output/paragraph_rankings.md` | Human-readable ranked list |
| `assets/data/old_new_mapping.csv` | Maps MMDD slots to current files |

## Related docs

- `docs/PUZZLE_REPLACEMENT.md` — Deep dive on `replace_lowest.py`
- `docs/PARAGRAPH_SCORING.md` — Scoring dimensions and weights
- `scripts/README_BATCH_GENERATOR.md` — Batch generation options

---
allowed-tools: Bash(python scripts/score_paragraphs.py*), Bash(python scripts/replace_lowest.py*), Bash(python scripts/show_score.py*), Bash(python assets/data/json_validator.py*), Bash(ls*), Bash(head*), Bash(tail*), Bash(rm*), Bash(git add*), Bash(git commit*), Bash(git push*), Bash(git status*), Bash(git diff*), Bash(git log*), Read(scripts/input/*), Read(assets/data/staging/*), Read(scripts/output/*), Write(assets/data/staging/*)
---

# replace-puzzles

Read paragraphs from an input text file, generate puzzle JSONs directly (no Groq/API calls), score them, compare against the lowest-scoring existing slots, and replace if improvements are found. Pauses for user approval before any destructive step.

## Usage

```
/replace-puzzles 0812.txt
/replace-puzzles 0812.txt --dry-run
```

- Input file is always in `scripts/input/`
- `--dry-run` stops after showing parsed paragraphs (no JSON written, no replacements)

## Parameters

- `$ARGUMENTS` contains the input filename (required) and optional `--dry-run` flag

---

## Implementation Instructions

### Step 0: Parse Arguments & Pre-checks

1. Parse `$ARGUMENTS` to extract the input filename and check for `--dry-run` flag.
2. If no filename provided, list files in `scripts/input/` and ask the user to pick one. Stop until they respond.
3. Verify `scripts/input/{filename}` exists. If not, list available files in `scripts/input/` and stop.
4. Check if `assets/data/staging/` contains any files. If it does:
   - Warn the user: "Staging directory is not empty. Clear it before proceeding?"
   - If user says yes, delete the files. If no, abort.
   - Alternatively, offer to inspect and score existing staged files if they appear to be from this same input (titles match).

---

### Stage 1 — Generate (Claude writes the JSON directly)

5. Read `scripts/input/{filename}`. Paragraphs are separated by `===` lines. Each starts with `Title: <title>`.

6. Show the user the list of parsed titles and paragraph count.
   - If `--dry-run` was passed, **stop here**.

7. For **each paragraph**, generate a complete, valid ClueChain puzzle JSON and write it to `assets/data/staging/NN-01_Title.json` where `NN` is the 1-based index zero-padded (01, 02, 03...).

#### JSON Generation Rules

Follow `assets/data/JSON_FORMAT_SPEC.md` exactly. Key requirements:

**Hidden words — selection:**
- Exactly 10 words per puzzle
- Difficulty distribution: 3–4 Easy, 4–5 Intermediate, 2–3 Hard
- Words must appear verbatim in the paragraph text (case-insensitive)
- No proper nouns, no hyphenated words, no contractions/apostrophes
- Avoid words that appear in the title (title spoiler penalty)
- Prefer words with interesting double meanings or lateral-thinking potential
- Identify 1–2 thematic clusters (2–3 words that share a theme); list them in `related_words` reciprocally
- Order words roughly Easy → Intermediate → Hard for a good discovery curve

**Clues — quality guidelines:**
- Each word gets exactly 3 clues: Indirect → Suggestive → Straight
- **Indirect** (5–7 pts): Lateral, evocative, poetic — requires an "aha!" moment. Never a direct definition. Exploit double meanings, metaphors, analogies. Max 2 sentences.
- **Suggestive** (3–4 pts): Describes function, association, or characteristic. Requires simple deduction. Clear and concise. Max 2 sentences.
- **Straight** (1–2 pts): Direct definition or synonym. Dictionary-style. Max 1 sentence.
- Clues must NOT contain the hidden word itself
- Avoid generic clues like "Something found only once" or "A lengthy fictional tale bound in covers" — these are too literal and hurt clueability scores

**Staging filename format:**
- `01-01_Title_With_Underscores.json` for the first paragraph
- `02-01_...`, `03-01_...` etc. (temp dates, replaced during the replace step)
- `date` field inside JSON should match the filename date (e.g. `"01-01"`)

8. After writing all files, validate each with:
   ```bash
   python assets/data/json_validator.py assets/data/staging/{filename}
   ```
   Fix any validation errors before proceeding.

9. Show a summary: N files written, N validated successfully.

---

### Stage 2 — Score & Compare

10. **Score** the staged files:
    ```bash
    python scripts/score_paragraphs.py --file assets/data/staging/*.json
    ```

11. Show new puzzle scores in a table (title, score, rating).

12. Read `scripts/output/mmdd_slot_scores.csv` to find the **bottom N slots** (where N = number of staged files). Show these as a comparison:
    ```
    | New Puzzle (Score) | vs | Current Lowest Slot (Score) | Delta |
    ```
    Sort new puzzles by score descending and pair with lowest slots ascending so the best new puzzle replaces the worst existing slot.

13. If all new scores are lower than all existing bottom slots, report "No improvements found — all new puzzles score lower than existing slots." and stop.

14. If some puzzles score low, offer to review and fix their clues/difficulty before proceeding (as done interactively during the session).

---

### Stage 3 — Replace (requires user approval)

15. Ask the user: "Ready to replace? I'll do a dry-run first to show the plan."

16. Run the dry-run replacement:
    ```bash
    python scripts/replace_lowest.py --dry-run
    ```
    Show the output (which files would be replaced, score deltas).

17. Ask the user: "Proceed with actual replacement?"

18. If user confirms, run the actual replacement:
    ```bash
    python scripts/replace_lowest.py
    ```

19. Show the results summary.

20. Ask the user: "Commit and push these changes?"

21. If user confirms:
    - Run `git status` to see changed files
    - `git add` the changed puzzle files, any replaced-puzzles archive files, mapping files, and score files
    - `git commit` with message: `fix(puzzles): replace N lowest-scoring puzzles`
    - `git push`
    - Show the commit result

---

## Error Handling

- **Missing input file**: List available files in `scripts/input/` and stop
- **Non-empty staging dir**: Warn and ask to clear, or offer to reuse if files match the input
- **Validation errors**: Fix before proceeding to Stage 2
- **All new scores lower than existing**: Report and stop after Stage 2
- **Replace script failures**: Show error output and stop

---

## File Paths

All paths relative to project root `/home/ram/projects/ClueChain/`:

- Input files: `scripts/input/{file}`
- Staging: `assets/data/staging/` (temporary, cleared before each run)
- Scores: `scripts/output/mmdd_slot_scores.csv`
- JSON spec: `assets/data/JSON_FORMAT_SPEC.md`
- Validator: `assets/data/json_validator.py`
- Scripts: `scripts/score_paragraphs.py`, `scripts/replace_lowest.py`

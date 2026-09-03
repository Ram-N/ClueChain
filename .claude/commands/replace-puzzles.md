---
allowed-tools: Bash(python scripts/batch_generate_cluechain_json.py*), Bash(python scripts/score_paragraphs.py*), Bash(python scripts/replace_lowest.py*), Bash(python scripts/show_score.py*), Bash(ls*), Bash(head*), Bash(tail*), Bash(git add*), Bash(git commit*), Bash(git push*), Bash(git status*), Bash(git diff*), Bash(git log*), Read(scripts/input/*), Read(assets/data/staging/*), Read(scripts/output/*)
---

# replace-puzzles

Generate new puzzles from an input text file, score them, compare against the lowest-scoring existing slots, and replace if improvements are found. Pauses for user approval before any destructive step.

## Usage

```
/replace-puzzles 0812.txt
/replace-puzzles 0812.txt --dry-run
```

- Input file is always in `scripts/input/`
- `--dry-run` stops after Stage 1 dry-run (no API calls, no replacements)

## Parameters

- `$ARGUMENTS` contains the input filename (required) and optional `--dry-run` flag
- `--category` and `--day` default to `REPLACE` and `1` (used only for temp staging filenames)

## Implementation Instructions

### Step 0: Parse Arguments & Pre-checks

1. Parse `$ARGUMENTS` to extract the input filename and check for `--dry-run` flag.
2. If no filename provided, list files in `scripts/input/` and ask the user to pick one. Stop until they respond.
3. Verify `scripts/input/{filename}` exists. If not, list available files in `scripts/input/` and stop.
4. Check if `assets/data/staging/` contains any files. If it does:
   - Warn the user: "Staging directory is not empty. Clear it before proceeding?"
   - If user says yes, delete the files. If no, abort.

---

### Stage 1 — Generate

5. **Dry-run** the batch generator to show parsed paragraphs:
   ```bash
   python scripts/batch_generate_cluechain_json.py \
     --file scripts/input/{filename} \
     --category REPLACE --day 1 \
     --output-dir assets/data/staging \
     --dry-run
   ```

6. Show the user the paragraph count and titles from the dry-run output. If `--dry-run` was passed in `$ARGUMENTS`, stop here.

7. Tell the user the paragraph count from the dry-run and give them the generation command to run themselves:

   ```
   Found N paragraphs. Run this command to generate (makes Groq API calls):

   python scripts/batch_generate_cluechain_json.py \
     --file scripts/input/{filename} \
     --category REPLACE --day 1 \
     --output-dir assets/data/staging \
     --continue-on-error --delay 15

   Let me know when it's done (paste the output or just say "done").
   ```

   **Stop and wait for the user to run it and report back.**

8. Once the user confirms completion, ask them for the success/failure counts if not already clear from their output. If any failed, warn but continue to Stage 2 if at least one file was generated. If zero files generated, stop.

---

### Stage 2 — Score & Compare

10. **Score** the staged files:
    ```bash
    python scripts/score_paragraphs.py --file assets/data/staging/*.json
    ```

11. Show new puzzle scores in a table (title, score).

12. Read `scripts/output/mmdd_slot_scores.csv` to find the **bottom N slots** (where N = number of staged files). Show these as a comparison:
    ```
    | New Puzzle (Score) | vs | Current Lowest Slot (Score) | Delta |
    ```
    Sort new puzzles by score descending and pair with lowest slots ascending so the best new puzzle replaces the worst existing slot.

13. If all new scores are lower than all existing bottom slots, report "No improvements found — all new puzzles score lower than existing slots." and stop.

---

### Stage 3 — Replace (requires user approval)

14. Ask the user: "Ready to replace? I'll do a dry-run first to show the plan."

15. Run the dry-run replacement:
    ```bash
    python scripts/replace_lowest.py --dry-run
    ```
    Show the output (which files would be replaced, score deltas).

16. Ask the user: "Proceed with actual replacement?"

17. If user confirms, run the actual replacement:
    ```bash
    python scripts/replace_lowest.py
    ```

18. Show the results summary.

19. Ask the user: "Commit and push these changes?"

20. If user confirms:
    - Run `git status` to see changed files
    - `git add` the changed puzzle files, any replaced-puzzles archive files, mapping files, and score files
    - `git commit` with message: `fix(puzzles): replace N lowest-scoring puzzles`
    - `git push`
    - Show the commit result

## Error Handling

- **Missing input file**: List available files in `scripts/input/` and stop
- **Non-empty staging dir**: Warn and ask to clear before proceeding
- **Zero successful generations**: Stop after Stage 1 with error summary
- **All new scores lower than existing**: Report and stop after Stage 2
- **API failures during generation**: `--continue-on-error` keeps going; report failures in summary
- **Replace script failures**: Show error output and stop

## File Paths

All paths relative to project root `/home/ram/projects/ClueChain/`:

- Input files: `scripts/input/{file}`
- Staging: `assets/data/staging/` (temporary, cleared before each run)
- Scores: `scripts/output/mmdd_slot_scores.csv`
- Scripts: `scripts/batch_generate_cluechain_json.py`, `scripts/score_paragraphs.py`, `scripts/replace_lowest.py`

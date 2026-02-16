# batch-puzzles

Generate a batch of 12 ClueChain puzzle JSON files from a multi-paragraph text file, validate them, and add them to the game index.

## Usage

```
/batch-puzzles --file paragraphs_food.txt --category FOOD --day 13
```

Or naturally:
```
batch generator paragraphs_food.txt FOOD 13
generate batch puzzles from paragraphs_food.txt, category COLORS, day 18
```

## Parameters

- `file` (required): Filename in `assets/data/library/` (e.g., `paragraphs_food.txt`)
- `category` (required): Category name in UPPERCASE (e.g., FOOD, COLORS, GEOGRAPHY)
- `day` (required): Day of month (1-31)

## What This Skill Does

1. **Parse & Generate** - Processes the multi-paragraph file and generates 12 JSON files (one per month)
   - Shows hidden words (Easy/Intermediate/Hard) for each paragraph as it's generated
   - Applies rate limiting (3s delay between API calls)

2. **Validate** - Runs JSON validator on each generated file
   - Reports validation errors but continues processing

3. **Update Index** - Automatically adds validated files to `assets/data/index.json`

4. **Resume Support** - If generation fails midway, asks which paragraph to resume from

## Implementation Instructions

### Step 1: Check for existing files (Resume Detection)

Check if any files matching the pattern `*-{day}-{CATEGORY}-*.json` already exist in `assets/data/`.

If files exist:
- Count how many are already present
- Ask the user: "Found {count} existing files for day {day}, category {CATEGORY}. Resume from paragraph {count+1}? (yes/no/start over)"
- If "yes": Start from paragraph {count+1}
- If "no" or "start over": Delete existing files and start from paragraph 1

### Step 2: Run Batch Generator

Execute the batch generator script:

```bash
python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/{file} \
  --category {CATEGORY} \
  --day {day} \
  --output assets/data \
  --delay 3 \
  --continue-on-error
```

**Important**: The script already shows hidden words during generation (after validation), so no additional parsing needed.

Monitor the output for:
- Generation progress (1/12, 2/12, etc.)
- Hidden words display for each paragraph (Easy/Intermediate/Hard)
- Any errors or failures

### Step 3: Validate Generated Files

After all files are generated, run validation on each:

```bash
./scripts/validate_batch.sh "*-{day}-{CATEGORY}-*.json"
```

This will:
- Show ✅/❌ for each file
- Report total passed/failed count

If any files fail validation:
- Display the list of failed files
- Note: Files will still be added to index, but user should be warned

### Step 4: Update Index

For each successfully generated file (validation pass or fail):

1. Read `assets/data/index.json`
2. Find the correct position to insert each file (sorted by MM-DD)
3. Add entries in format: `"./assets/data/{filename}.json"`
4. Write updated index back

Example: For file `01-13-FOOD-kulfi.json`, insert after `01-12-*` and before `01-14-*` or `02-*` entries.

**Sorting rules**:
- Sort by month (01-12)
- Then by day (01-31)
- Files with same MM-DD are sorted alphabetically by filename

### Step 5: Final Summary

Display a completion summary:

```
════════════════════════════════════════════════════════════
🎉 BATCH PUZZLE GENERATION COMPLETE
════════════════════════════════════════════════════════════
Category: {CATEGORY}
Day: {day}

📊 Results:
   Generated: 12/12 files
   Validated: X passed, Y failed
   Index: Updated with 12 new entries

📁 Files created:
   01-{day}-{CATEGORY}-{slug}.json
   02-{day}-{CATEGORY}-{slug}.json
   ...
   12-{day}-{CATEGORY}-{slug}.json

✅ All puzzles are now available in the game!

{If any validation failures:}
⚠️  Warning: {Y} file(s) failed validation. Please review:
   - {failed_file_1}
   - {failed_file_2}
```

## Error Handling

### Missing File
If `assets/data/library/{file}` doesn't exist:
- Show error: "File not found: assets/data/library/{file}"
- List available files in that directory
- Exit

### Invalid Category/Day
- Category must be UPPERCASE letters/numbers/hyphens only
- Day must be 1-31
- Show error and exit if invalid

### API Failures
- The batch generator has `--continue-on-error` flag, so it will skip failed paragraphs
- Report which paragraphs failed in the final summary
- Still update index with successfully generated files

### Validation Failures
- Continue with index update even if validation fails
- Warn user about failed validations
- User can manually fix issues later

## File Paths

All paths relative to project root `/home/ram/projects/ClueChain/`:

- Input files: `assets/data/library/{file}`
- Output files: `assets/data/{MM-DD-CATEGORY-slug}.json`
- Index: `assets/data/index.json`
- Scripts: `scripts/batch_generate_cluechain_json.py`, `scripts/validate_batch.sh`

## Notes

- Total time: ~6-10 minutes for 12 paragraphs (depends on API speed)
- Rate limiting: 3 seconds between API calls (prevents rate limit errors)
- The generator script already handles delimiter detection (===, #, ---)
- Validation is informational - files are added to index regardless
- Index updates preserve existing entries, only adds new ones

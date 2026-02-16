# Batch ClueChain JSON Generator

Automate the generation of ClueChain puzzles for multiple months from a single text file.

## Overview

The batch generator (`batch_generate_cluechain_json.py`) processes multi-paragraph text files and generates ClueChain JSON files for each paragraph, automatically assigning them to sequential months.

## Quick Start

```bash
# Generate 12 monthly puzzles for the 13th of each month
python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --category FOOD \
  --day 13
```

## Input File Format

Paragraphs should be separated by delimiters (`===`, `#`, or `---`). Each paragraph follows this structure:

```
===

Title of the Paragraph
Author or Source

Paragraph text goes here. Can be multiple sentences
or even multiple paragraphs.

===

Next Title
Next Author

Next paragraph text...
```

### Example

```
====

Fancy a Kulfi? From Granita to Queso Helado
Smithsonian magazine

The colorful streets of Chandni Chowk, a shopping area in India's Old Delhi...

===

The Unified Theory of Deliciousness
Chef David Chang | Wired

My first restaurant, Momofuku Noodle Bar, had an open kitchen...
```

## Command-Line Options

### Required Arguments

- `--file PATH` - Path to multi-paragraph text file
- `--category NAME` - Category name (e.g., FOOD, GEOGRAPHY, HISTORY)
- `--day NUMBER` - Day of month (1-31)

### Optional Arguments

- `--delimiter PATTERN` - Paragraph separator (default: `===`)
- `--delay SECONDS` - Seconds between API calls (default: 3.0)
- `--output DIR` - Output directory (default: `./assets/data`)
- `--continue-on-error` - Continue processing if one paragraph fails
- `--dry-run` - Preview parsing without making API calls

## Output Format

Files are named: `MM-DD-CATEGORY-title-slug.json`

**Examples:**
- `01-13-FOOD-fancy-a-kulfi-from-granita-to-queso-helado.json`
- `02-13-FOOD-the-unified-theory-of-deliciousness.json`
- `03-13-GEOGRAPHY-the-silk-road.json`

## Usage Examples

### Basic Usage

```bash
python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --category FOOD \
  --day 13
```

### Test Parsing First (Dry Run)

```bash
python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --category FOOD \
  --day 13 \
  --dry-run
```

### Custom Rate Limiting

For slower API rate limits, increase the delay:

```bash
python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --category FOOD \
  --day 13 \
  --delay 5
```

### Continue on Error

If some paragraphs fail but you want to process the rest:

```bash
python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --category FOOD \
  --day 13 \
  --continue-on-error
```

### Different Delimiter

If your file uses `#` instead of `===`:

```bash
python scripts/batch_generate_cluechain_json.py \
  --file my_paragraphs.txt \
  --category SCIENCE \
  --day 20 \
  --delimiter "#"
```

## Workflow

The batch generator follows this process:

1. **Parse Input File** - Splits file by delimiter into individual paragraphs
2. **Assign Months** - Assigns months 1-12 sequentially to paragraphs
3. **For Each Paragraph:**
   - Creates temporary file with paragraph text
   - Calls `generate_cluechain_json.py` via subprocess
   - Waits for API response
   - Renames output to new naming convention
   - Waits for rate-limiting delay
4. **Report Results** - Displays summary of successful and failed generations

## Rate Limiting

**Default:** 3 seconds between API calls

**Why?** Groq's free tier allows ~30 requests/minute. With 3 seconds between calls (20 requests/minute), we stay well within limits.

**Time Estimates:**
- 12 paragraphs with 3s delay: ~6-10 minutes
- 12 paragraphs with 5s delay: ~8-12 minutes

## Error Handling

### Common Errors

**Missing API Key:**
```
❌ Error: GROQ_API_KEY not found in environment variables
```
**Solution:** Add `GROQ_API_KEY=your_key_here` to `.env` file

**Invalid Day:**
```
❌ Error: Invalid day: 32 (must be 1-31)
```
**Solution:** Use a day between 1 and 31

**File Not Found:**
```
❌ Error: Input file not found: paragraphs.txt
```
**Solution:** Check file path is correct

**Rate Limit Exceeded:**
```
❌ [5/12] FAILED: Paragraph Title
   Error: Rate limit exceeded
```
**Solution:** Increase `--delay` value (e.g., `--delay 5`)

### Continue on Error

By default, the script stops on the first error. Use `--continue-on-error` to process all paragraphs even if some fail:

```bash
python scripts/batch_generate_cluechain_json.py \
  --file paragraphs.txt \
  --category FOOD \
  --day 13 \
  --continue-on-error
```

## Progress Output

The script provides real-time progress updates:

```
🚀 Starting Batch Generation
   Category: FOOD
   Day: 13
   Paragraphs: 12
   Delay: 3.0s between calls
════════════════════════════════════════════════════════════

[1/12] Processing: Fancy a Kulfi? From Granita to Queso Helado
       Date: 01-13
       Calling Groq API...
✅     Generated: 01-13-FOOD-fancy-a-kulfi-from-granita-to-queso-helado.json (4.2s)

[2/12] Processing: The Unified Theory of Deliciousness
       Date: 02-13
       Calling Groq API...
✅     Generated: 02-13-FOOD-the-unified-theory-of-deliciousness.json (3.8s)

...

════════════════════════════════════════════════════════════
📊 BATCH GENERATION SUMMARY
════════════════════════════════════════════════════════════
Total Paragraphs: 12
Successful: 12
Failed: 0
Total Time: 8m 32s
Average Time per Paragraph: 42.7s

✅ All files generated successfully!
```

## Validation

After generation, validate the JSON files:

```bash
# Validate all generated files
for file in assets/data/01-13-FOOD-*.json; do
    python assets/data/json_validator.py "$file"
done
```

## Tips

1. **Always dry-run first** - Use `--dry-run` to verify parsing before making API calls
2. **Start small** - Test with a file containing 1-2 paragraphs first
3. **Check API quota** - Monitor your Groq API usage to avoid hitting limits
4. **Validate outputs** - Always validate generated JSON files before using in production
5. **Batch by day** - Generate all puzzles for the same day across months (easier to organize)

## Troubleshooting

### Script Can't Find generate_cluechain_json.py

The batch generator looks for `generate_cluechain_json.py` in the same directory (`scripts/`). Ensure both files are in the same location:

```
ClueChain/
└── scripts/
    ├── generate_cluechain_json.py
    └── batch_generate_cluechain_json.py
```

### Paragraphs Not Parsing Correctly

Use `--dry-run` to see how the file is being parsed:

```bash
python scripts/batch_generate_cluechain_json.py \
  --file your_file.txt \
  --category TEST \
  --day 1 \
  --dry-run
```

Check that your delimiters match the expected format (`===`, `#`, or `---`).

### API Calls Timing Out

If API calls consistently timeout (>5 minutes), there may be an issue with:
- Internet connection
- Groq API service status
- Overly long paragraphs (>2000 characters)

## Architecture

The batch generator is a **wrapper** around the existing `generate_cluechain_json.py` script:

- **Separation of concerns** - Single-file generator remains unchanged
- **Subprocess execution** - Each paragraph processed independently
- **File renaming** - Converts old format (`MM-DD_Title.json`) to new format (`MM-DD-CATEGORY-slug.json`)
- **No code duplication** - All API logic, validation, and JSON generation remain in the original script

## Dependencies

Same as the single-file generator:

```
groq
python-dotenv
```

Install via:
```bash
pip install -r requirements.txt
```

## See Also

- `generate_cluechain_json.py` - Single-paragraph generator
- `docs/JSON_FORMAT_SPEC.md` - JSON format specification
- `assets/data/json_validator.py` - JSON validation tool

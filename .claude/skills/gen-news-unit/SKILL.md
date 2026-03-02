---
name: gen-news-unit
description: Generate a ClueChain news unit JSON from a source text file using the Groq LLM. Use when the user wants to process a news file into a practice unit.
allowed-tools: Bash, Read, Glob
---

Generate a ClueChain news unit from a source file.

Arguments provided: $ARGUMENTS

## Steps

1. Parse $ARGUMENTS to extract:
   - `--file` (required): path to the source .txt file
   - `--date` (optional, default today in YYYY-MM-DD): output date
   - `--title` (optional, default "Today's News"): unit title
   - `--delay` (optional, default 5): seconds between Groq calls
   - `--dry-run` (optional flag): preview without calling API

   If no arguments were given, ask the user for the `--file` path before proceeding.

2. First do a dry run to confirm article count:
   ```
   uv run python scripts/generate_news_unit.py --file <file> [--date <date>] [--title <title>] --dry-run
   ```
   Show the user the article count and previews, then confirm before calling the API.

3. If the user confirms (or `--dry-run` was not explicitly requested), run without `--dry-run`:
   ```
   uv run python scripts/generate_news_unit.py --file <file> [--date <date>] [--title <title>] [--delay <delay>]
   ```

4. Report the output file path and blank count from the summary.


## Running the App

To run this app, simply serve the pages locally.

```bash
python3 -m http.server
```

Then visit http://localhost:8000 in your browser.

### Troubleshooting: Puzzle Not Showing

If a puzzle doesn't appear in the calendar:

1. **Check index.json** - Make sure the puzzle file is listed:
   ```bash
   cat assets/data/index.json
   ```

2. **Verify JSON file exists** - Confirm the file path is correct:
   ```bash
   ls -la assets/data/02-15*.json
   ```

3. **Clear browser cache** - Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)

4. **Check browser console** - Look for errors in the developer tools console

## Activating Python Virtual Environment

Before running Python scripts (like the JSON validator), activate the virtual environment:

```bash
# From the ClueChain root directory
source .venv/bin/activate
```

## Creating New Puzzles

### 1. Write the Paragraph
- Store raw paragraphs in `assets/data/library/`
- Format: Title, source, and paragraph text

### 2. Generate JSON with AI
Use the generator script to create the puzzle JSON:
```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/p1.txt \
  --title "Puzzle Title" \
  --date MM-DD
```

### 3. Validate the JSON
Always validate before using in the game:
```bash
python assets/data/json_validator.py assets/data/MM-DD_Title.json
```

### 4. Update index.json
Add the new puzzle to `assets/data/index.json` so the game can find it.

**Note:** The JSON format is year-agnostic (MM-DD), so each puzzle repeats annually.


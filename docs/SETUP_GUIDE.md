# ClueChain JSON Generator - Setup and Usage Guide

Quick reference guide for setting up and using the ClueChain JSON generator script.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `groq` - Groq API client
- `python-dotenv` - Environment variable management

## Step 2: Set Up Your API Key

1. Get your Groq API key from [console.groq.com/keys](https://console.groq.com/keys)

2. Copy the example environment file:
```bash
cp .env.example .env
```

3. Edit the `.env` file and add your API key:
```bash
# Open .env in your editor
nano .env
# or
vim .env
# or
code .env
```

4. Add your key:
```
GROQ_API_KEY=your_actual_groq_api_key_here
```

## Step 3: Run the Script

### Basic Usage
```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --title "Food Science"
```

### With All Options
```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --title "Food Science" \
  --date 11-18 \
  --output ./assets/data
```

### Test with Sample Paragraph
```bash
python scripts/generate_cluechain_json.py \
  --file scripts/test_paragraph.txt \
  --title "The Dawn of AI"
```

## Step 4: Validate Output (Optional)

```bash
python assets/data/json_validator.py assets/data/11-18_Food_Science.json
```

## Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--file` | **Yes** | - | Path to text file with paragraph |
| `--title` | No | "ClueChain Challenge" | Title for JSON |
| `--date` | No | Today's MM-DD | Date (MM-DD, year-agnostic) |
| `--output` | No | `./assets/data` | Output directory |

## Common Commands

### Process existing library files
```bash
# Food paragraphs
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --title "Culinary Delights"

# Indian cities paragraphs
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_Indian_cities.txt \
  --title "Indian Cities"
```

### Process with specific date
```bash
python scripts/generate_cluechain_json.py \
  --file my_paragraph.txt \
  --title "My Topic" \
  --date 07-20
```

## Troubleshooting

### Error: "GROQ_API_KEY not found"
- Make sure `.env` file exists in project root
- Check that your API key is correctly added
- Don't include quotes around the API key in `.env`

### Error: "File not found"
- Check the file path is correct
- Use `ls` to verify the file exists
- Try using absolute path: `/full/path/to/file.txt`

### Error: "Missing required package"
- Run: `pip install -r requirements.txt`
- Make sure you're in the project directory

### Validation fails
- Try running the script again (LLM may generate better output)
- Check that your paragraph has enough diverse words
- Ensure paragraph is at least 3-5 sentences

## Quick Reference

```bash
# 1. One-time setup
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API key

# 2. Generate JSON
python scripts/generate_cluechain_json.py --file YOUR_FILE.txt --title "YOUR_TITLE"

# 3. Validate (optional)
python assets/data/json_validator.py assets/data/YOUR_OUTPUT.json
```

## Getting Help

View all available options:
```bash
python scripts/generate_cluechain_json.py --help
```

For detailed documentation, see:
- `scripts/README.md` - Full usage guide
- `docs/JSON_Creation_PRD.md` - Requirements specification
- `docs/SCRIPT_IMPLEMENTATION.md` - Implementation details

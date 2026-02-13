# ClueChain JSON Generator

Python script to automatically generate ClueChain game JSON files from paragraph text using the Groq API.

## Features

- Automatically selects 10 hidden words from a paragraph following PRD rules
- Generates 3 types of clues per word (Indirect, Suggestive, Straight)
- Detects thematically related words and links them
- Validates output against ClueChain JSON schema
- Command-line interface for easy batch processing

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `groq` - Groq API client
- `python-dotenv` - Environment variable management

### 2. Configure API Key

1. Get your Groq API key from [console.groq.com/keys](https://console.groq.com/keys)
2. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

3. Edit `.env` and add your API key:

```
GROQ_API_KEY=your_actual_api_key_here
```

## Usage

### Basic Usage

Generate JSON from a paragraph file:

```bash
python scripts/generate_cluechain_json.py --file path/to/paragraph.txt
```

### With Custom Title

```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --title "Food Science"
```

### Specify Date and Output Directory

```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --title "Indian Cities" \
  --date 11-20 \
  --output ./assets/data
```

### Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--file` | Yes | - | Path to text file containing the paragraph |
| `--title` | No | "ClueChain Challenge" | Title for the JSON output |
| `--date` | No | Today's MM-DD | Date in MM-DD format (year-agnostic) |
| `--output` | No | `./assets/data` | Output directory for JSON file |

## Input Format

The script accepts plain text files containing paragraphs. The paragraph should be:

- In English
- At least a few sentences long
- Rich enough to contain 10 meaningful words of varying difficulty

Example input file (`example.txt`):
```
The ancient observatory, perched high upon the mountain peak, offered a profound
and breathtaking vista. Astronomers utilize powerful telescopes to study distant
galaxies and nebulae, meticulously recording their brightness and spectral shifts.
```

## Output Format

The script generates JSON files following the ClueChain schema:

```json
{
  "title": "Astronomical Wonders",
  "date": "2025-11-18",
  "hiddenWords": [
    {
      "word": "telescope",
      "difficulty": "Intermediate",
      "related_words": ["galaxy", "astronomer"],
      "clues": [
        {
          "clue": "An eye that pierces the cosmic veil...",
          "type": "Indirect",
          "points": 6
        },
        {
          "clue": "An instrument used to observe distant celestial objects",
          "type": "Suggestive",
          "points": 3
        },
        {
          "clue": "An optical instrument for viewing distant objects",
          "type": "Straight",
          "points": 1
        }
      ]
    }
    // ... 9 more words
  ]
}
```

### Validation

The script automatically validates:
- Exactly 10 hidden words
- 3 clues per word (Indirect, Suggestive, Straight)
- Point values within valid ranges (Indirect: 5-7, Suggestive: 3-4, Straight: 1-2)
- Proper difficulty distribution
- Thematic word linking (2-3 word groups only)

For additional validation, run the existing validator:

```bash
python assets/data/json_validator.py assets/data/2025-11-18_Food_Science.json
```

## Examples

### Example 1: Process a paragraph about food

```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraphs_food.txt \
  --title "Culinary Delights"
```

Output: `assets/data/2025-11-18_Culinary_Delights.json`

### Example 2: Batch process with specific dates

```bash
# Process multiple files with different dates
python scripts/generate_cluechain_json.py \
  --file paragraphs_july_20.txt \
  --date 2025-07-20

python scripts/generate_cluechain_json.py \
  --file paragraphs_july_21.txt \
  --date 2025-07-21
```

## Word Selection Rules

The LLM follows these rules when selecting the 10 hidden words:

### ✅ INCLUDE
- Single words present in the paragraph
- Mix of difficulty levels (Easy, Intermediate, Hard)
- Meaningful content words (nouns, verbs, adjectives)

### ❌ EXCLUDE
- Proper nouns (names, places, capitalized words)
- Compound words (e.g., "spaceship")
- Words with punctuation (hyphens, apostrophes)
- Common articles and prepositions

### Difficulty Distribution
- **Easy**: 3-4 words (common, simple vocabulary)
- **Intermediate**: 3-4 words (moderate complexity)
- **Hard**: 2-3 words (advanced, specialized vocabulary)

## Clue Generation

Each word gets exactly 3 clues:

### Indirect Clue (5-7 points)
- Style: Riddle-like, lateral thinking required
- Characteristics: Wordplay, puns, poetic language
- Length: Max 2 sentences

### Suggestive Clue (3-4 points)
- Style: Describes characteristics or associations
- Characteristics: Requires simple deduction
- Length: Max 2 sentences

### Straight Clue (1-2 points)
- Style: Dictionary definition or synonym
- Characteristics: Direct and unambiguous
- Length: Max 1 sentence

## Thematic Linking

The script automatically identifies groups of 2-3 thematically related words:

Example: `["telescope", "galaxy", "astronomer"]` are space-related

Each word in the group will have its `related_words` array populated with the OTHER words in the group.

## Troubleshooting

### "GROQ_API_KEY not found"
- Make sure you created a `.env` file in the project root
- Check that your API key is correctly formatted
- Verify the `.env` file is not named `.env.txt` or similar

### "File not found"
- Check the file path is correct (use absolute or relative paths)
- Ensure the file exists and is readable

### "Expected exactly 10 hidden words"
- The LLM occasionally generates fewer/more words
- Try running again (may need 1-2 retries)
- Consider simplifying or enriching the input paragraph

### Validation Errors
- The script performs strict validation
- If validation fails, check the error message for specifics
- Re-run to get a fresh LLM generation

## Cost Considerations

- Uses Groq's `llama-3.3-70b-versatile` model
- Groq offers generous free tier limits
- Each generation uses ~1000-2000 tokens
- Cost is minimal for typical usage

## Advanced Usage

### Custom Model Selection

Edit the script to use a different Groq model:

```python
# In ClueChainGenerator class
self.model = "mixtral-8x7b-32768"  # Alternative model
```

Available models: See [Groq documentation](https://console.groq.com/docs/models)

### Adjust Temperature

For more creative/varied outputs, modify the temperature:

```python
# In generate_json method
temperature=0.7,  # Default (balanced)
temperature=0.9,  # More creative
temperature=0.5,  # More deterministic
```

## License

Part of the ClueChain project.

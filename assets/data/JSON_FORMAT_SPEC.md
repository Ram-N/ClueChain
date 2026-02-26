# ClueChain Puzzle JSON Format Specification

**Version:** 2.1
**Last Updated:** 2026-02-26
**Status:** Canonical Format

This document defines the authoritative JSON structure for ClueChain puzzle files. All puzzle JSON files MUST conform to this specification.

---

## File Naming Convention

```
MM-DD_Title.json
```

**Examples:**
- `02-15_The_Success_of_Ordinary_Indians.json`
- `07-04.json` (title optional in filename)
- `12-25_Christmas_Traditions.json`

**Rules:**
- Date format: `MM-DD` (year-agnostic, repeats annually)
- Underscore separates date from title
- Title should match the JSON `title` field (spaces replaced with underscores)
- No year in filename (puzzles repeat annually)

---

## JSON Structure

### Top-Level Required Fields

```json
{
  "title": "string",
  "date": "MM-DD",
  "text": "string",
  "hiddenWords": [...]
}
```

### Top-Level Optional Fields

```json
{
  "id": "string",        // Legacy field, ignored by game
  "topic": "string",     // Primary category (controlled vocab)
  "themes": ["string"],  // Specific sub-themes (free-form, 1–4 items)
  "source": {
    "name": "string",    // Publication or origin (e.g. "New York Times")
    "url": "string",     // Optional link to original article/page
    "notes": "string"    // Optional free text (e.g. "Adapted from a 2014 column")
  },
  "summary": "string"    // 1–2 sentence description of what the puzzle is about
}
```

---

## Field Specifications

### `title` (string, required)

The display title of the puzzle.

**Rules:**
- Must be a non-empty string
- Displayed in the game UI
- Should be descriptive and engaging

**Example:**
```json
"title": "The Success of Ordinary Indians"
```

---

### `date` (string, required)

The date this puzzle is associated with, in `MM-DD` format (year-agnostic).

**Rules:**
- Format: `MM-DD` (two-digit month, two-digit day)
- Must match the date in the filename
- No year component (puzzle repeats annually)
- Must be a valid calendar date (e.g., `02-30` is invalid)
- Leap year dates (`02-29`) are valid but skipped on non-leap years

**Examples:**
```json
"date": "02-15"
"date": "07-04"
"date": "12-25"
```

---

### `text` (string, required)

The complete paragraph text from which hidden words are drawn.

**Rules:**
- Must be a non-empty string
- All words in `hiddenWords[].word` MUST appear in this text
- Preserves original formatting (newlines, punctuation, etc.)
- Used by the game to:
  - Display the paragraph with masked words
  - Verify hidden words exist
  - Calculate word positions for masking

**Example:**
```json
"text": "PONDICHERRY, India — I spent the start of this decade in the same place that I spent the start of the last: outside the town of Pondicherry, in the countryside, amid the sound of firecrackers and the glow of oil lamps from surrounding villages.\n\nApart from my location, though, little else remains the same. Over the last 10 years, the countryside has been transformed. Villages have become towns. Mud huts have given way to concrete structures. Fields have been replaced by shopping complexes."
```

---

### `hiddenWords` (array, required)

An array of exactly 10 word objects representing the hidden words in the puzzle.

**Rules:**
- Must contain exactly 10 word objects
- Each word must appear in the `text` field
- Must have a balanced difficulty distribution (see below)

---

## Metadata Field Specifications

### `topic` (string, optional)

The primary subject category of the puzzle.

**Rules:**
- Single string from controlled vocabulary
- Allowed values: `History`, `Science`, `Literature`, `Culture`, `Geography`, `Politics`, `Technology`, `Nature`, `Sports`, `Arts`, `Economics`, `Philosophy`, `Society`
- List is extensible — add new values by updating this spec

**Example:**
```json
"topic": "Society"
```

---

### `themes` (array, optional)

More specific angles or sub-themes within the topic.

**Rules:**
- Array of free-form strings
- 0–4 items
- More specific than `topic`

**Example:**
```json
"themes": ["British India", "Empire", "Colonialism"]
```

---

### `source` (object, optional)

Provenance information about where the puzzle text originated.

**Fields:**
- `name` (string, required if source present) — publication or origin name
- `url` (string, optional) — URL to original article or page
- `notes` (string, optional) — any other provenance info

**Example:**
```json
"source": {
  "name": "New York Times",
  "url": "https://example.com/article",
  "notes": "Column about economic change in India"
}
```

---

### `summary` (string, optional)

A brief description of what the puzzle is about, written for a player who just finished playing.

**Rules:**
- 1–2 sentences
- Not the same as the title — provides context and insight
- Describes the subject matter, not the gameplay

**Example:**
```json
"summary": "A journalist revisits Pondicherry after a decade and reflects on the dramatic transformation of rural India through economic growth."
```

---

## Hidden Word Object Structure

Each word object in `hiddenWords` must have the following structure:

```json
{
  "word": "string",
  "difficulty": "Easy | Intermediate | Hard",
  "related_words": ["string", "string", ...],
  "clues": [
    {
      "clue": "string",
      "type": "Indirect",
      "points": 5 | 6 | 7
    },
    {
      "clue": "string",
      "type": "Suggestive",
      "points": 3 | 4
    },
    {
      "clue": "string",
      "type": "Straight",
      "points": 1 | 2
    }
  ]
}
```

---

## Hidden Word Field Specifications

### `word` (string, required)

The hidden word to be guessed.

**Rules:**
- Must be a single word (no spaces)
- No hyphens, apostrophes, or punctuation
- No proper nouns or capitalized words (except when starting a sentence)
- No compound words (e.g., "spaceship")
- Case-insensitive matching in game
- Must appear in the `text` field (case-insensitive)

**Valid Examples:**
```json
"word": "countryside"
"word": "villages"
"word": "growth"
```

**Invalid Examples:**
```json
"word": "New York"        // Contains space
"word": "eco-friendly"    // Contains hyphen
"word": "India"           // Proper noun
"word": "it's"            // Contains apostrophe
```

---

### `difficulty` (string, required)

The difficulty level of the word.

**Rules:**
- Must be one of: `"Easy"`, `"Intermediate"`, `"Hard"`
- Difficulty distribution across all 10 words:
  - Easy: 3-4 words
  - Intermediate: 3-4 words
  - Hard: 2-3 words

**Example:**
```json
"difficulty": "Intermediate"
```

---

### `related_words` (array, required)

An array of other hidden words thematically related to this word.

**Rules:**
- Must be an array (can be empty `[]`)
- If 2-3 words share a theme, list the OTHER words in the group
- Each word in a related group must list all other words in that group
- Maximum of 3 words in a related group (including the current word)
- Related words must exist in the `hiddenWords` array

**Example (3 related words):**
```json
// For word "villages"
"related_words": ["towns", "countryside"]

// For word "towns"
"related_words": ["villages", "countryside"]

// For word "countryside"
"related_words": ["villages", "towns"]

// For unrelated words
"related_words": []
```

---

### `clues` (array, required)

An array of exactly 3 clue objects, one for each clue type.

**Rules:**
- Must contain exactly 3 clue objects
- Must have one of each type: `Indirect`, `Suggestive`, `Straight`
- Order should be: Indirect, Suggestive, Straight

---

## Clue Object Structure

Each clue must have the following fields:

```json
{
  "clue": "string",
  "type": "Indirect | Suggestive | Straight",
  "points": 1 | 2 | 3 | 4 | 5 | 6 | 7
}
```

---

## Clue Field Specifications

### `clue` (string, required)

The clue text presented to the player.

**Rules:**
- Must be a non-empty string
- Length constraints:
  - Indirect: Max 2 sentences
  - Suggestive: Max 2 sentences
  - Straight: Max 1 sentence
- Must not contain the hidden word itself
- Should follow the style guidelines for its type (see below)

---

### `type` (string, required)

The type/difficulty of the clue.

**Values:**

#### `"Indirect"` (Hard Clue)
- Style: Lateral thinking, wordplay, riddles, puns
- Poetic, humorous, or multi-layered
- Requires an "aha!" moment
- Points: 5-7

**Example:**
```json
{
  "clue": "Where community comes together, smaller than a town but larger than a hamlet.",
  "type": "Indirect",
  "points": 6
}
```

#### `"Suggestive"` (Intermediate Clue)
- Style: Describes characteristics, associations, or functions
- Requires simple deduction
- Clear and concise
- Points: 3-4

**Example:**
```json
{
  "clue": "Small settlements of houses in rural areas.",
  "type": "Suggestive",
  "points": 3
}
```

#### `"Straight"` (Easy Clue)
- Style: Direct definition or synonym
- Dictionary-style, unambiguous
- For immediate recognition
- Points: 1-2

**Example:**
```json
{
  "clue": "Small rural communities.",
  "type": "Straight",
  "points": 1
}
```

---

### `points` (integer, required)

The point value awarded for solving with this clue.

**Rules:**
- Must be an integer
- Valid ranges by type:
  - Indirect: 5, 6, or 7
  - Suggestive: 3 or 4
  - Straight: 1 or 2
- Higher points = harder clue

---

## Complete Example

```json
{
  "title": "The Success of Ordinary Indians",
  "date": "02-15",
  "topic": "Society",
  "themes": ["India", "Rural Development", "Economic Growth"],
  "source": {
    "name": "New York Times",
    "notes": "Column about economic change in India"
  },
  "summary": "A journalist revisits Pondicherry after a decade and reflects on the dramatic transformation of rural India through economic growth.",
  "text": "PONDICHERRY, India — I spent the start of this decade in the same place that I spent the start of the last: outside the town of Pondicherry, in the countryside, amid the sound of firecrackers and the glow of oil lamps from surrounding villages.\n\nApart from my location, though, little else remains the same. Over the last 10 years, the countryside has been transformed. Villages have become towns. Mud huts have given way to concrete structures. Fields have been replaced by shopping complexes.\n\nThis has been a momentous decade for India. Economically, in particular, the nation has made huge strides. Although its revitalization began in the 1980s and '90s, the last decade has been marked by a noticeable acceleration of growth rates.",
  "hiddenWords": [
    {
      "word": "villages",
      "difficulty": "Easy",
      "related_words": ["towns", "countryside"],
      "clues": [
        {
          "clue": "Where community comes together, smaller than a town but larger than a hamlet.",
          "type": "Indirect",
          "points": 6
        },
        {
          "clue": "Small settlements of houses in rural areas.",
          "type": "Suggestive",
          "points": 3
        },
        {
          "clue": "Small rural communities.",
          "type": "Straight",
          "points": 1
        }
      ]
    },
    {
      "word": "growth",
      "difficulty": "Intermediate",
      "related_words": [],
      "clues": [
        {
          "clue": "What economies measure when they're doing well, or what plants do in spring.",
          "type": "Indirect",
          "points": 6
        },
        {
          "clue": "An increase or expansion over time.",
          "type": "Suggestive",
          "points": 3
        },
        {
          "clue": "Development or increase.",
          "type": "Straight",
          "points": 1
        }
      ]
    }
    // ... 8 more word objects (total 10)
  ]
}
```

---

## Validation Requirements

A valid ClueChain puzzle JSON must pass all of the following checks:

### Required Fields
- ✅ `title` exists and is non-empty string
- ✅ `date` exists and matches format `MM-DD`
- ✅ `text` exists and is non-empty string
- ✅ `hiddenWords` exists and is an array

### Date Validation
- ✅ Date in JSON matches date in filename
- ✅ Date is a valid calendar date

### Hidden Words Array
- ✅ Contains exactly 10 word objects
- ✅ Difficulty distribution is balanced (3-4 Easy, 3-4 Intermediate, 2-3 Hard)

### Each Hidden Word Object
- ✅ Has required fields: `word`, `difficulty`, `related_words`, `clues`
- ✅ `word` is a single word with no spaces, hyphens, or punctuation
- ✅ `word` appears in the `text` field (case-insensitive)
- ✅ `difficulty` is one of: Easy, Intermediate, Hard
- ✅ `related_words` is an array
- ✅ `clues` is an array of exactly 3 clue objects

### Each Clue Object
- ✅ Has required fields: `clue`, `type`, `points`
- ✅ `type` is one of: Indirect, Suggestive, Straight
- ✅ `points` is an integer in valid range for the type:
  - Indirect: 5-7
  - Suggestive: 3-4
  - Straight: 1-2
- ✅ Each word has exactly one clue of each type

### Thematic Linking
- ✅ If a word lists related words, those words exist in `hiddenWords`
- ✅ Related word links are reciprocal (if A lists B, B must list A)

### Optional Metadata
Optional metadata fields (`topic`, `themes`, `source`, `summary`) are ignored by game logic and require no validation beyond type checks.

---

## Migration from Legacy Format

**Legacy Format (Pre-2.0):** Used `YYYY-MM-DD` dates and included an `id` field.

**Changes in 2.0:**
- Date format changed to `MM-DD` (year-agnostic)
- `text` field is now required
- `id` field is optional (ignored by game)

**Backward Compatibility:**
- Old format files with `id` will still validate
- Date format in existing files should be updated to `MM-DD`

See `docs/DATE_FORMAT_MIGRATION.md` for migration details.

---

## Tools

### Validation
```bash
python assets/data/json_validator.py assets/data/MM-DD_Title.json
```

### Generation
```bash
python scripts/generate_cluechain_json.py \
  --file assets/data/library/paragraph.txt \
  --title "Puzzle Title" \
  --date MM-DD
```

---

## Version History

| Version | Date       | Changes                                                      |
|---------|------------|--------------------------------------------------------------|
| 2.1     | 2026-02-26 | Added optional metadata fields: `topic`, `themes`, `source`, `summary` |
| 2.0     | 2026-02-14 | Year-agnostic format, `text` required                        |
| 1.0     | 2025-07-01 | Initial format with YYYY-MM-DD dates                         |

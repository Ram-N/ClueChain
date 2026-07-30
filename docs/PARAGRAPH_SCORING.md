# Paragraph Quality Scoring

ClueChain includes a scoring pipeline that evaluates every puzzle paragraph across multiple quality dimensions. It produces a **total score out of 100** and an overall **good / okay / poor** rating so you can review paragraph quality at a glance.

## How It Works

The scorer uses a **hybrid approach** with two phases:

### Phase 1 -- Rule-Based Scores (fast, free)

These run locally using [spaCy](https://spacy.io/) NLP and require no API calls.

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| **Word Quality** | 30% | Are the hidden words nouns, verbs, adjectives (good) or function words like "the", "of", "is" (bad)? Bonus for concrete, visual words (animals, tools, food, etc.) and longer words. |
| **Variety** | 15% | Do the hidden words vary in part-of-speech, word length, and grouping? A paragraph with 10 nouns of similar length scores lower than one mixing nouns, verbs, and adjectives of different lengths. |

**How word quality scoring works:**

Each hidden word gets a raw score based on:
- **POS tag**: Nouns/proper nouns (+2), verbs/adjectives (+1), adverbs (0), function words like determiners, prepositions, pronouns (-5)
- **Word length**: Words shorter than 4 characters get a -1 penalty
- **Concreteness**: Words from built-in concrete-word lists (animals, tools, buildings, food, body parts, weather, vehicles, instruments) get a +1 bonus

The raw total is normalized to a 0-10 scale.

**How variety scoring works:**

Three sub-metrics combined (40/30/30 weighting):
- **POS diversity**: How many different parts of speech appear among hidden words
- **Length spread**: Standard deviation of word lengths (more variation = higher score)
- **Group independence**: How many independent word groups exist (vs. all words being related to each other)

### Phase 2 -- LLM Scores (one API call per paragraph)

An LLM (Llama 3.3 70B) evaluates subjective quality dimensions that can't be computed with rules alone.

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| **Connectivity** | 20% | How integral are the hidden words to the paragraph's theme? Do they feel essential, or randomly picked from the text? |
| **Clueability** | 15% | Are the three clue tiers (Indirect, Suggestive, Straight) distinct, creative, and progressively helpful? |
| **Discovery Curve** | 10% | Does solving some words help guess others? A good paragraph has cascade/momentum effects. |
| **Narrative Interest** | 10% | Is the prose engaging and interesting to read, or dry and encyclopedic? |
| **Catalog Penalty** | raw -3 to 0 | Deduction for list-like, encyclopedic writing. Natural prose = 0, pure catalog = -3. |

Each LLM dimension is scored 0-10 with a written reason.

### Final Score Calculation

```
final_score (0-10) = word_quality * 0.30
                   + variety      * 0.15
                   + connectivity * 0.20
                   + clueability  * 0.15
                   + discovery_curve    * 0.10
                   + narrative_interest * 0.10
                   + catalog_penalty        (raw deduction)

total_score (0-100) = final_score * 10    (clamped to 0-100)
```

### Overall Rating

| Rating | Total Score | Meaning |
|--------|-------------|---------|
| **good** | 75-100 | Strong paragraph, ready to ship |
| **okay** | 50-74 | Playable but could be improved |
| **poor** | < 50 | Needs rework -- weak words, bad clues, or catalog-style writing |

### Partial Scores

If a paragraph only has rule-based scores (no LLM pass yet), the scorer estimates a full score proportionally from the available 45% weight. These are marked as `partial (45%)` in the output. Run the script again to fill in LLM scores for remaining paragraphs.

## Running the Script

```bash
python scripts/score_paragraphs.py
```

### Prerequisites

1. **Python packages** -- `spacy`, `python-dotenv`, `openai` (for NIM), `groq` (for Groq)
2. **spaCy model** -- `python -m spacy download en_core_web_sm`
3. **API key** -- at least one of these in your `.env` file:
   - `NIM_API_KEY` (NVIDIA NIM -- default)
   - `GROQ_API_KEY` (Groq -- fallback, or use `--groq` flag)

### Common Commands

```bash
# Score all unscored paragraphs (resumes from last checkpoint)
python scripts/score_paragraphs.py

# Score a batch of 50 instead of the default 20
python scripts/score_paragraphs.py --batch-size 50

# Force Groq instead of NIM
python scripts/score_paragraphs.py --groq

# Re-score everything from scratch (ignores checkpoint)
python scripts/score_paragraphs.py --force

# Score a single file
python scripts/score_paragraphs.py --file assets/data/07-15_Example.json

# Preview what would be scored without calling any APIs
python scripts/score_paragraphs.py --dry-run

# Slow down API calls (default is 2s between calls)
python scripts/score_paragraphs.py --delay 5.0
```

### LLM Provider Selection

| Condition | Provider used |
|-----------|--------------|
| `NIM_API_KEY` set (no `--groq` flag) | NVIDIA NIM (default) |
| `--groq` flag passed | Groq (errors if `GROQ_API_KEY` not set) |
| Only `GROQ_API_KEY` set (no NIM key) | Groq (automatic fallback) |
| Neither key set | Rule-based scores only, LLM phase skipped |

### Resumable Batching

The script saves a checkpoint after every successfully scored paragraph. If it gets rate-limited or interrupted, just run it again -- it picks up where it left off. Use `--batch-size` to control how many LLM calls per run.

## Output Files

All output goes to `scripts/output/`:

| File | Format | Contents |
|------|--------|----------|
| `paragraph_scores.json` | JSON | Complete scoring data for every paragraph -- scores, reasons, total_score, overall_rating |
| `paragraph_rankings.csv` | CSV | Ranked spreadsheet with all dimensions, sortable in any tool |
| `paragraph_rankings.md` | Markdown | Human-readable tier report with summary table |

### paragraph_scores.json Structure

```json
{
  "07-15_Example.json": {
    "title": "Example Paragraph",
    "date": "07-15",
    "scores": {
      "word_quality": 8.5,
      "variety": 6.2,
      "connectivity": 7,
      "clueability": 8,
      "discovery_curve": 6,
      "narrative_interest": 7,
      "catalog_penalty": -1
    },
    "reasons": {
      "word_quality": "8 nouns, 0 function words",
      "variety": "3 POS types, 8 word groups, length std=2.1",
      "connectivity": "Most words are thematically connected...",
      "clueability": "Good tier separation across all words...",
      "discovery_curve": "Moderate cascade between related words...",
      "narrative_interest": "Engaging prose with vivid descriptions...",
      "catalog_penalty": "Some enumeration but mostly narrative"
    },
    "has_llm_scores": true,
    "llm_provider": "NIM",
    "total_score": 67.2,
    "overall_rating": "okay"
  }
}
```

## Tips for Reviewing Paragraphs

- **Sort by `total_score`** in the CSV to find the worst paragraphs first
- **Filter by `overall_rating == "poor"`** to find paragraphs that need rework
- **Check `catalog_penalty`** -- a -2 or -3 means the paragraph reads like a list and should be rewritten as natural prose
- **Check `word_quality`** -- a low score means too many function words (the, of, is) are hidden instead of content words
- **Partial scores** (no LLM pass) are rough estimates; run the script to completion for accurate ratings

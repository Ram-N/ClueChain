# fetch_paragraphs.py — Reference Guide

Fetches copyright-free paragraphs from Wikipedia, Project Gutenberg, or The Guardian on any topic, scores them for puzzle suitability, and writes a numbered library file ready to pipe into `batch_generate_cluechain_json.py`.

---

## Setup

Install dependencies (one time):

```bash
uv pip install -r requirements.txt

# spaCy model must be installed via wheel (uv venvs don't include pip)
uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

---

## Sources

Three sources are available, each with different strengths:

| Source | `--source` value | Prose style | API key? |
|--------|-----------------|-------------|----------|
| Wikipedia | `wikipedia` *(default)* | Encyclopedic, fact-dense | No |
| Project Gutenberg | `gutenberg` | Literary — classic novels, essays | No |
| The Guardian | `guardian` | Journalistic — news, culture, science | Free key required |

---

## Basic Usage

```bash
# Wikipedia (default — no flag needed)
uv run python scripts/fetch_paragraphs.py --topic "ancient rome"

# Project Gutenberg — literary prose, no signup
uv run python scripts/fetch_paragraphs.py --topic "adventure" --source gutenberg

# The Guardian — journalistic prose (see Guardian setup below)
uv run python scripts/fetch_paragraphs.py --topic "climate" --source guardian --guardian-key YOUR_KEY
```

---

## Wikipedia

Wikipedia is the default source. It searches for a matching article and pulls prose paragraphs from its sections. Good for topics that map to a well-known article (history, science, geography, culture).

```bash
# Fetch 12 paragraphs on a topic (default count)
uv run python scripts/fetch_paragraphs.py --topic "ancient rome"

# Preview without writing a file
uv run python scripts/fetch_paragraphs.py --topic "philosophy" --dry-run

# Fetch fewer paragraphs
uv run python scripts/fetch_paragraphs.py --topic "jazz music" --count 6

# Custom output path
uv run python scripts/fetch_paragraphs.py --topic "maps" --output assets/data/library/maps.txt
```

**When to use:** Topics that have long, well-written Wikipedia articles — history, science, geography, biographies, cultural movements.

**Limitation:** Prose tends to be encyclopedic and dry. Topics with thin or list-heavy Wikipedia articles may yield few paragraphs.

---

## Project Gutenberg

Gutenberg pulls from 60,000+ public-domain books via the [Gutendex API](https://gutendex.com). It produces richer, more literary prose — novels, essays, travelogues, memoirs. No signup or API key required.

```bash
# Literary adventure prose from classic novels
uv run python scripts/fetch_paragraphs.py --topic "adventure" --source gutenberg --count 10

# Victorian-era mystery writing
uv run python scripts/fetch_paragraphs.py --topic "mystery" --source gutenberg

# Dry-run preview
uv run python scripts/fetch_paragraphs.py --topic "romance" --source gutenberg --count 5 --dry-run
```

**How it works:** Searches Gutendex for books matching the topic (by title keywords), downloads plain text from Project Gutenberg, and splits into paragraphs. The top books by download count are tried first.

**When to use:** When you want richer narrative prose — puzzles about literature, history, travel, or any topic where "story-like" paragraphs are more interesting than encyclopedia entries.

**Tips:**
- Topic is matched against book *titles*, not content. `"adventure"`, `"mystery"`, `"romance"` find books in those genres. `"ancient rome"` is unlikely to match well — use `wikipedia` for that.
- Results naturally cluster around a few popular books. That's expected.
- If a topic yields 0 results, try a simpler or more common genre word.

---

## The Guardian

The Guardian API returns full article body text from one of the world's largest news archives. Produces contemporary journalistic prose — accessible, varied, and rich in named entities. Excellent for topics related to current events, culture, science, or social issues.

### One-time setup

1. Go to [open-platform.theguardian.com/access](https://open-platform.theguardian.com/access/)
2. Register for a **Developer** (free) key — takes about 2 minutes
3. You'll receive an API key by email immediately

Free tier limits: **5,000 calls/day**, **12 calls/second** — more than enough for this use case.

### Usage

```bash
# Science journalism
uv run python scripts/fetch_paragraphs.py --topic "space exploration" --source guardian

# Culture and arts writing
uv run python scripts/fetch_paragraphs.py --topic "jazz" --source guardian --guardian-key YOUR_KEY --count 10

# Dry-run preview
uv run python scripts/fetch_paragraphs.py --topic "climate" --source guardian --guardian-key YOUR_KEY --count 5 --dry-run
```

**When to use:** Contemporary topics where encyclopedic prose feels stale — technology, environment, social issues, arts and culture, sports. Also great for shorter, punchier paragraphs with strong sentence variety.

**Tips:**
- Topic is used as a full-text search query across article content. More specific topics (`"deep sea exploration"`) work as well as broad ones (`"science"`).
- Results come from multiple different articles, so you naturally get varied writing styles.

---

## All Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--topic` | *(required)* | Search string, e.g. `"philosophy"`, `"maps and cartography"` |
| `--source` | `wikipedia` | Paragraph source: `wikipedia`, `gutenberg`, or `guardian` |
| `--guardian-key` | — | Guardian API key (required when `--source guardian`) |
| `--count` | `12` | Number of paragraphs to fetch |
| `--output` | `assets/data/library/{slug}.txt` | Output file path |
| `--min-chars` | `450` | Minimum paragraph length in characters |
| `--max-chars` | `900` | Maximum paragraph length in characters |
| `--max-words` | `120` | Maximum paragraph length in words |
| `--min-score` | `40` | Discard paragraphs scoring below this threshold (0–100) |
| `--dry-run` | off | Print output to stdout instead of writing a file |
| `--append` | off | Append new paragraphs to an existing file instead of overwriting |

---

## Topping Up an Existing File

If you already have a library file and need a few extra paragraphs, use `--append` instead of re-fetching everything. Works with any source.

```bash
# Add 2 more paragraphs to an existing file
uv run python scripts/fetch_paragraphs.py --topic "neo-noir" --count 2 --append

# Append from Gutenberg instead of Wikipedia
uv run python scripts/fetch_paragraphs.py --topic "mystery" --source gutenberg --count 3 --append

# Preview what would be appended without writing
uv run python scripts/fetch_paragraphs.py --topic "neo-noir" --count 2 --append --dry-run
```

`--append` mode:
- Reads the existing file and fingerprints every paragraph already in it
- Fetches a larger candidate pool to absorb deduplication losses
- Filters out any candidate that duplicates existing content
- Appends only the top N new paragraphs to the end of the file

The existing paragraphs are never modified or overwritten.

---

## How Scoring Works

Every candidate paragraph is evaluated across seven dimensions regardless of source:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Word count | 20% | Peaks at ~125 words; penalizes very short or very long paragraphs |
| Readability | 20% | Flesch reading ease 50–70 is ideal (not too simple, not too academic) |
| Named entity density | 20% | Ratio of named entities (people, places, dates) to total words |
| Lexical diversity | 15% | Unique words ÷ total words; richer vocabulary scores higher |
| Sentence variety | 10% | Standard deviation of sentence lengths; varied rhythm scores higher |
| Topic relevance | 10% | Frequency of topic keywords per 100 words |
| Sentiment strength | 5% | Absolute VADER compound score; stronger emotion beats flat neutral |

Candidates below `--min-score` are discarded. The top `--count` by score are written to the output file.

### Preview table

Before writing, the script prints a ranked summary:

```
  #  Score  Words     FK     NE  Title
────────────────────────────────────────────────────────────────────────────────
  1   78.6     98   61.5  0.071  Alice's Adventures in Wonderland — Ca...
  2   76.1    116   80.5  0.095  Alice's Adventures in Wonderland — Ca...
  3   73.5     97   74.2  0.103  Alice's Adventures in Wonderland — Ca...
```

Columns: **Score** (0–100), **Words** (word count), **FK** (Flesch reading ease, 50–70 ideal), **NE** (named entity density), **Title** (source and section/author).

---

## Output Format

All sources produce the same numbered-delimiter format used by `batch_generate_cluechain_json.py`:

```
1.
Title: Alice's Adventures in Wonderland — Carroll, Lewis

Alice was not a bit hurt, and she jumped up on to her feet in a moment...

2.
Title: The Adventures of Sherlock Holmes — Doyle, Arthur Conan

It was a September evening, and not yet seven o'clock, but the day had...
```

For Wikipedia, the title line is `Article Title — Section Name`.
For Gutenberg, it is `Book Title — Author Name`.
For Guardian, it is `Article Headline — The Guardian`.

---

## Full Workflow

```bash
# Step 1: Fetch paragraphs (any source)
uv run python scripts/fetch_paragraphs.py --topic "ancient rome" --count 12
uv run python scripts/fetch_paragraphs.py --topic "mystery" --source gutenberg --count 12

# Step 2: Review assets/data/library/ancient-rome.txt
# Edit manually if any paragraph needs replacing

# Step 3: Generate puzzle JSONs
uv run python scripts/batch_generate_cluechain_json.py \
  --file assets/data/library/ancient-rome.txt \
  --category "ANCIENT-ROME" \
  --day 26
```

---

## Troubleshooting

**"No paragraphs found"**
- *Wikipedia:* The topic may be too obscure or spelled differently from a Wikipedia article title. Try a broader term or check the Wikipedia article name directly.
- *Gutenberg:* The topic doesn't match any book titles. Try a genre word (`"adventure"`, `"mystery"`, `"romance"`) rather than a subject.
- *All sources:* Try `--min-chars 300 --max-chars 1200` to widen the length filter.

**"Only N paragraphs available (requested 12)"**
Options:
- Lower `--min-score` (e.g. `--min-score 30`)
- Broaden char range (e.g. `--min-chars 400 --max-chars 1200`)
- Use a broader topic
- Try a different source — Guardian or Gutenberg may yield more for topics where Wikipedia is thin

**"spaCy model not found"**
Run: `uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl`
(The uv venv doesn't include pip, so `python -m spacy download` won't work.)

**Output skews to one book or article**
Normal when a topic maps to a single popular result. For more variety, use a broader topic or run the script twice with slightly different topics and use `--append` to combine results.

**`--append` finds fewer paragraphs than requested**
The source may not have enough sections/articles left after deduplication. Try lowering `--min-score`, broadening the char range, or using a slightly different but related topic.

**Paragraphs contain list-like text**
Some Wikipedia sections and Guardian articles render as short lists rather than prose. Raise `--min-chars` to filter out short items, or edit the output file manually to replace those entries.

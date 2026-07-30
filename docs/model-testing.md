# Model Testing Guide

`scripts/model_test.py` lets you benchmark any OpenRouter model (or Groq)
against a single paragraph and get a scored comparison.  Use it whenever you
want to try a new model before committing it to `model-config.json`.

---

## Quick start

```bash
# Test whatever model is currently set in model-config.json
uv run python scripts/model_test.py --file /tmp/my_para.txt

# Test a specific model
uv run python scripts/model_test.py --file /tmp/my_para.txt \
    --models "google/gemini-2.0-flash-lite-001"

# Compare two models side-by-side
uv run python scripts/model_test.py --file /tmp/my_para.txt \
    --models "google/gemini-2.0-flash-lite-001,meta-llama/llama-3.3-70b-instruct:free"

# Compare against Groq as a baseline
uv run python scripts/model_test.py --file /tmp/my_para.txt --include-groq
```

---

## Paragraph file format

The input file is plain text, identical to what `generate_cluechain_json.py`
accepts:

```
Title: General knowledge — Intelligence

High scorers on tests of general knowledge tend to also score highly on
intelligence tests. IQ has been found to robustly predict general knowledge
scores even after accounting for differences in age...
```

- First non-blank line must start with `Title:` (or just be the title).
- Everything after the title is the paragraph body.
- No special delimiters needed — this is a single-paragraph file.

A convenient place to keep test paragraphs is `/tmp/` or a local
`assets/data/library/test/` directory.

---

## Arguments

| Argument | Default | Description |
|---|---|---|
| `--file PATH` | *(required)* | Path to paragraph text file |
| `--models "a,b,c"` | model in `model-config.json` | Comma-separated OpenRouter model IDs |
| `--include-groq` | off | Also run Groq (`llama-3.3-70b-versatile`) as a baseline |
| `--delay SECS` | `6` | Pause between API calls to avoid rate limits |

---

## How it works

1. For each model, the script temporarily sets `openrouter_model` in
   `model-config.json`, calls `generate_cluechain_json.py`, then restores the
   original config — your settings are never permanently changed.
2. Each output is run through `assets/data/json_validator.py` (the same
   validator used in batch generation).
3. A quality score (0–100) is calculated on top of structural validation.
4. Results are printed as a detailed per-model breakdown followed by a
   ranked summary table.
5. Raw JSON output files are saved to a temp directory (path shown at the
   end of the run) so you can inspect them manually.

---

## Scoring

Total is out of **100 points** across five categories:

### Difficulty spread — 30 pts

Rewards hitting the target distribution of **3 Easy / 4 Intermediate / 3 Hard**.
Deducts 3 pts per word off-target per level, capped at 10 pts deducted per
level.  A perfect 3/4/3 spread scores the full 30.

### Clue length — 25 pts

Measures the average character length across all 30 clues (10 words × 3
clues each).  Scores 25 pts at an average of ≥ 80 characters, scaling down
linearly to 0 at an average of 20 characters.  Longer clues generally mean
more nuanced, less giveaway hints.

### Related words coverage — 20 pts

Each hidden word should have at least 2 `related_words` entries (used for
in-game highlighting).  Score = fraction of words meeting that threshold × 20.
Full 20 pts requires all 10 words to have ≥ 2 related words.

### No giveaway clues — 15 pts

Penalises clues shorter than 20 characters (3 pts each), which tend to be
too direct or trivially obvious.  Full 15 pts if no short clues exist.

### Word uniqueness — 10 pts

Full 10 pts if all 10 hidden words are distinct; 5 pts if any duplicates
are found (the validator will also flag this as an error).

---

## Reading the output

```
══════════════════════════════════════════════════════════════════════
  MODEL TEST RESULTS
══════════════════════════════════════════════════════════════════════

▶ google/gemini-2.0-flash-lite-001
  Backend    : openrouter
  Validation : ✅ PASS
  Quality    : 74/100
    Difficulty spread : 24/30
    Clue length       : 22/25
    Related words     : 16/20
    No giveaways      : 15/15
    Word uniqueness   : 10/10
    → Difficulty dist: {'Easy': 4, 'Intermediate': 4, 'Hard': 2}
    → Avg clue length: 73 chars
    → Words with ≥2 related: 8/10
  Time       : 11.3s

▶ meta-llama/llama-3.3-70b-instruct:free
  Backend    : openrouter
  Validation : ❌ FAIL (2 errors)
    - hiddenWords[3]: word 'knowledge' appears in the title and must not be hidden
    - hiddenWords[7].clues[1]: clue text contains the hidden word 'semantic'
  Quality    : 61/100
    ...
  Time       : 8.7s

══════════════════════════════════════════════════════════════════════
  SUMMARY
══════════════════════════════════════════════════════════════════════
  Model                                      Valid   Quality    Time
  ------------------------------------------ ------  --------  ------
  google/gemini-2.0-flash-lite-001             PASS        74   11.3s
  meta-llama/llama-3.3-70b-instruct:free       FAIL        61    8.7s
```

The summary table is sorted by quality score (highest first), so the best
model is always at the top.

---

## Workflow: trying a new model

1. **Write a test paragraph** (or reuse one from `assets/data/library/`):
   ```bash
   cp assets/data/library/general-knowledge.txt /tmp/gk_test.txt
   # Edit to keep just one paragraph
   ```

2. **Run the test** against the candidate model:
   ```bash
   uv run python scripts/model_test.py \
       --file /tmp/gk_test.txt \
       --models "qwen/qwen3-next-80b-a3b-instruct:free" \
       --include-groq
   ```

3. **Check the score**.  A model is generally good enough for batch generation
   if it:
   - Passes validation (0 errors)
   - Scores ≥ 65/100 on quality
   - Completes in < 30s

4. **Promote the model** by editing `model-config.json`:
   ```bash
   # Edit scripts/model-config.json and set "openrouter_model"
   ```
   Or set `--model openrouter` in the generator directly.

---

## Available models reference

The `available_models` list in `model-config.json` is just a reminder — you
can pass any valid OpenRouter model ID to `--models`.  Free-tier models are
marked `:free` in their ID.

```json
{
  "openrouter_model": "google/gemini-2.0-flash-lite-001",
  "available_models": [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemini-2.0-flash-lite-001",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct:free"
  ]
}
```

Find more models at [openrouter.ai/models](https://openrouter.ai/models).
Filter by "Free" to find zero-cost options.

---

## Tips

- **Rate limits**: Free-tier OpenRouter models can return 429 errors.
  Increase `--delay` to 10–15s if you see failures:
  ```bash
  uv run python scripts/model_test.py --file /tmp/para.txt --delay 12
  ```

- **Inspect raw output**: The temp directory printed at the end of each run
  contains the actual JSON files.  Open them to read the clues and judge
  quality beyond the numeric score.

- **Groq as a sanity check**: `--include-groq` is useful to confirm that a
  poor score is genuinely the model's fault and not a problem with the
  paragraph or prompt.

- **Reuse the same paragraph**: The scoring is deterministic for a given
  output file, so you can compare models fairly as long as you use the
  same paragraph.

- **Token budget**: Each test call consumes roughly the same tokens as one
  batch-generate paragraph (~800–1000 tokens in, ~1500 out).  Running
  four models = ~4× that.  Stay mindful of daily Groq limits if using
  `--include-groq` heavily.

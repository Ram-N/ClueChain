## Modal UI flow

### A. Read page layout

Each item block (news item, lesson paragraph, poem stanza) shows:

* Title (optional)
* Plain text (never masked in Read mode)
* Footer row:

  * **Practice** button (opens modal)
  * Difficulty selector (or a pill): `Easy | Standard | Advanced`
  * Small metadata: `5–8 blanks` (estimated)

On the page header:

* Toggle: `Read | Practice`
* Global difficulty (optional): `Easy | Standard | Advanced` (sets default for all items)

### B. Open modal

User clicks **Practice** on item #3.

Modal opens (full-screen on mobile, centered on desktop):

* Top bar:

  * `Back` (closes modal, returns to same scroll position)
  * Title: “Practice: Item 3”
  * Progress: `1/1` (for a single item) or `3/7` (if practicing sequentially)
* Mode strip:

  * `This item` | `All items` (if you want to chain through 7 news items without closing)

Body:

* Masked text rendered inline.
* Each blank is an interactive token.

Right/Bottom panel (responsive):

* Score: `0 / 100` (or points earned so far)
* Attempts remaining per blank (optional)
* Buttons:

  * **Hint 1** (easy/definition)
  * **Hint 2** (medium/context)
  * **Hint 3** (hard/indirect)
  * **Reveal word**
  * **Reveal all** (confirm)
* Input:

  * A single input box that applies to the currently selected blank
  * Or click blank → input appears

### C. Solve loop (per blank)

1. User clicks a blank token (highlighted).
2. Panel shows:

   * blank number (e.g., Blank 4 of 6)
   * word length (optional)
   * part of speech (optional)
   * Difficulty-adjusted hint ordering
3. User types guess → Submit
4. Feedback:

   * Correct: token fills in, points awarded, auto-advance to next blank
   * Incorrect: gentle feedback, reduce points potential for that blank, keep focus

### D. Finish state

When all blanks solved or revealed:

* Summary screen inside modal:

  * Score earned
  * Time spent (optional)
  * Breakdown: solved vs revealed
* Buttons:

  * **Return to reading** (closes modal)
  * **Practice next item** (goes to next item in the same content page)
  * **Retry (new mask)** (optional, if you generate variants)

On close:

* The original item block now shows:

  * a checkmark + score: `Completed (82)`
  * a small “Practice again” link

### E. Practice mode (page-level)

If user toggles page to `Practice`:

* The page becomes a list of the same items, but each item shows:

  * a mini “Start” button or auto-starts when scrolled into view
* Still use the modal for the actual solving, but practice mode:

  * encourages doing all items in sequence

### Difficulty behavior (key)

Difficulty should change:

* number of blanks (range)
* which words get blanked (rarer vs common)
* hint strength and order

Suggested defaults:

* Easy: 4–6 blanks, direct hints first
* Standard: 6–8 blanks, mixed hints
* Advanced: 8–12 blanks, indirect first, fewer freebies

So you are no longer locked to “exactly 10”.

---

## Unified JSON schema

Design goal: one schema that supports:

* Daily puzzle (single item)
* Today’s news (multi-item content page)
* Learning pack lesson (multi-item)
* Optional pre-authored blanks and hints, OR auto-generated blanks/hints

### Top-level object: a “content unit”

Call it `content_unit`. It can contain 1+ items.

**File examples**

* Daily: `assets/data/units/daily/mmdd/0225.json`
* News: `assets/data/units/news/yyyy/2026/02/25.json`
* Pack lesson: `assets/data/units/packs/ai/basics/lesson-03.json`

### Schema (minimal but complete)

```json
{
  "schema_version": 1,
  "unit_id": "daily-0225",
  "unit_type": "daily",
  "title": "Daily ClueChain",
  "date": "2026-02-25",
  "topic": "general",
  "source": {
    "name": "Wikipedia",
    "url": "https://example.com",
    "license": "CC BY-SA"
  },

  "items": [
    {
      "item_id": "daily-0225-01",
      "title": "Optional item title",
      "text": "Full readable text shown in Read mode.",

      "practice": {
        "enabled": true,

        "blanking": {
          "mode": "auto",
          "targets": {
            "easy": { "min_blanks": 4, "max_blanks": 6 },
            "standard": { "min_blanks": 6, "max_blanks": 8 },
            "advanced": { "min_blanks": 8, "max_blanks": 12 }
          },
          "avoid": {
            "stopwords": true,
            "numbers": true,
            "very_short_words_max_len": 3
          }
        },

        "hints": {
          "layers": ["direct", "intermediate", "indirect"],
          "difficulty_hint_order": {
            "easy": ["direct", "intermediate", "indirect"],
            "standard": ["intermediate", "direct", "indirect"],
            "advanced": ["indirect", "intermediate", "direct"]
          }
        },

        "scoring": {
          "max_points": 100,
          "per_blank": "proportional",
          "penalties": {
            "wrong_guess": 1,
            "hint_used": { "direct": 2, "intermediate": 4, "indirect": 6 },
            "reveal_word": 10
          }
        }
      },

      "authored_variants": [
        {
          "variant_id": "v1",
          "difficulty": "standard",
          "blanks": [
            {
              "blank_id": "b1",
              "answer": "inflation",
              "occurrence": 1,
              "hints": {
                "direct": "A general rise in prices over time.",
                "intermediate": "Measured in indexes like CPI.",
                "indirect": "When money buys less than it used to."
              }
            }
          ]
        }
      ]
    }
  ],

  "navigation": {
    "collection": "news",
    "sequence": {
      "prev_unit_id": "news-2026-02-24",
      "next_unit_id": "news-2026-02-26"
    }
  },

  "tags": ["vocabulary", "current-events"],
  "reading_level": "adult",
  "estimated_minutes": 5
}
```

### Why this schema works

* A daily puzzle is just a unit with one item.
* Today’s news is a unit with 7 items.
* A learning lesson is a unit with N items.
* Practice can be:

  * fully auto (blanking + hints generated at runtime)
  * fully authored (exact blanks and hints stored)
  * mixed (store blanks, generate hints)

### Key fields to notice

* `unit_type`: `daily | news | lesson | poem | story` etc.
* `items[]`: everything becomes item-based
* `practice.blanking.targets`: solves your “not always 10 blanks” requirement cleanly
* `authored_variants`: lets you lock down specific high-quality clue chains when you want

---

## How the modal chooses what to do

When user clicks “Practice (Advanced)” on item 3:

1. If an authored variant exists for that item + difficulty, use it.
2. Else generate blanks using `practice.blanking.targets[advanced]`.
3. Generate hints (or fetch from cached LLM output if you store them later).
4. Run scoring using `practice.scoring`.

---

## Next step (so you can build without rewriting everything)

You can implement this without migrating all files immediately:

* Keep your current daily `mmdd.json` files as-is
* Add a thin “adapter” in code that loads old format and produces this unified object in memory

Then you migrate gradually.

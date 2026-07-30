
# CLUECHAIN PARAGRAPH IMPROVEMENT PROJECT

The challenge is "generate 366 paragraphs that are fun puzzle substrates."

A paragraph that is perfectly good prose may still be terrible for Clue Chain. Likewise, a mediocre paragraph can produce excellent puzzle words.

I would treat this as a ranking problem.

For every paragraph, calculate a quality score based on several dimensions.

## 1. Word Quality Score

This is probably the most important metric.

Ask:

* Are the hidden words concrete?
* Are they recognizable?
* Are they guessable from clues?
* Are they interesting?

Good hidden words:

* telescope
* volcano
* detective
* orchestra
* migration
* emerald

Bad hidden words:

* therefore
* within
* despite
* catalog
* approximately
* several

You could score words using:

| Feature            | Score |
| ------------------ | ----- |
| Noun               | +2    |
| Verb               | +1    |
| Adjective          | +1    |
| Proper noun        | +1    |
| Function word      | -5    |
| Rare obscure word  | -3    |
| Highly visual word | +2    |

Then average across all 10 hidden words.

---

## 2. Variety Score

A common failure mode is:

* tiger
* lion
* leopard
* cheetah
* panther

All related, but repetitive.

Instead:

* volcano
* violin
* astronaut
* bamboo
* eclipse
* detective

The puzzle feels richer.

Measure:

* number of semantic categories represented
* diversity of parts of speech
* diversity of word lengths

Example:

| Category  | Count |
| --------- | ----- |
| Animals   | 3     |
| Science   | 2     |
| Geography | 2     |
| Music     | 1     |
| History   | 2     |

Higher spread = higher score.

---

## 3. Connectivity Score

This is unique to Clue Chain.

The words should feel like they belong to the paragraph.

Bad:

> The museum displayed ancient artifacts. Hidden words:
>
> volcano
> squirrel
> spaceship
> pancake

No relationship.

Good:

> The museum displayed ancient artifacts from lost civilizations...

Hidden words:

* artifact
* archaeologist
* excavation
* pottery
* dynasty

The paragraph naturally supports the words.

You could ask an LLM:

> For each hidden word, how strongly is it supported by the surrounding paragraph?
>
> Score 1-10.

Then average.

---

## 4. Clueability Score

Some words naturally generate clues.

Example:

### Easy

telescope

Possible clues:

* Used by astronomers
* Makes distant objects appear closer
* Starts with T

### Hard

therefore

Possible clues:

* Transition word

Not much fun.

You could score:

* number of dictionary definitions
* number of synonyms
* number of related concepts
* number of clue types possible

Words with many clue paths get higher scores.

---

## 5. Discovery Curve Score

A good puzzle has a cascade effect.

Guessing one word helps you guess others.

Example:

Paragraph about ancient Egypt.

Once you solve:

* pyramid

you can more easily solve:

* pharaoh
* mummy
* Nile
* hieroglyph

The puzzle develops momentum.

An LLM can estimate:

> If a player solves three random words, how much easier do the remaining words become?

Score 1-10.

---

## 6. Narrative Interest Score

This is where many generated paragraphs fail.

Bad:

> The catalog contains information about products. The inventory is updated annually...

Instant boredom.

Good:

> As the storm approached the lighthouse, the keeper noticed strange lights moving across the sea...

Even before solving anything, the player is curious.

An LLM is actually very good at scoring this.

Prompt:

> Rate this paragraph's intrinsic reader interest from 1-10.
>
> Penalize encyclopedic, catalog-like, repetitive, or list-like writing.

---

## 7. Catalog Detector

This is worth making a dedicated rule.

Strong penalties for:

* long enumerations
* comma-separated lists
* encyclopedia style
* dictionary style
* textbook summaries

For example:

> Bears live in forests. Tigers live in jungles. Whales live in oceans...

This should automatically get a huge deduction.

---

## 8. The Overall Formula

Something like:

```
Final Score =
30% Word Quality
20% Connectivity
15% Variety
15% Clueability
10% Discovery Curve
10% Narrative Interest
- Catalog Penalty
```

---

## What I would do today

Since you already have 366 paragraphs, I would not regenerate anything yet.

I would build an evaluation pipeline:

1. Extract paragraph.
2. Extract the 10 hidden words.
3. Send both to an LLM.
4. Have the LLM return:

```json
{
  "word_quality": 8.4,
  "variety": 7.2,
  "connectivity": 9.1,
  "clueability": 8.8,
  "discovery_curve": 7.5,
  "narrative_interest": 6.3,
  "catalog_penalty": 0,
  "final_score": 8.1
}
```

Then rank all 366 puzzles.

My guess is you'll discover:

* Top 50 are excellent and worth keeping forever.
* Middle 200 need light editing.
* Bottom 100 should simply be replaced.

That ranking alone would probably improve Clue Chain more than generating another year's worth of puzzles.

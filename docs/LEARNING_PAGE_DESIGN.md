This related to the /learning pages

# The Mental Model Shift

Instead of:

> A pack = list of puzzles

Think:

> A pack = learning content
> Each paragraph inside it can optionally be “clue-chained”

That subtle difference changes the UX.

---

# The Concrete Example: “Today’s News – 7 Items”

User lands on:

`/learning/news/today`

They see:

### Page Layout

**Header**

* Title: Today’s News
* Date: February 25, 2026
* Short intro

---

## Below that: 7 clean content blocks

Each news item is shown normally, readable, not masked.

Example:

---

### 1. Federal Reserve Signals Rate Pause

Two or three sentences of clean text.

Under it:

* `ClueChain this`
* Maybe a small lock icon
* Maybe a subtle badge: 5 masked words (actual number to mask depends on the paragraph length)

---

### 2. Major Earthquake in Chile

(same structure)

---

This is important:
The content is readable first.
ClueChain is optional reinforcement.

---

# What Happens When User Clicks “ClueChain this”

Two design paths:

---

## (Best UX): Modal Overlay

User clicks “ClueChain this”.

Instead of navigating away, you:

* Darken the background
* Open a full-screen modal
* Load the clue-chain UI inside it
* Mask words
* Hints, scoring, reveal, etc.

When finished:

* Close modal
* Return to same scroll position
* Mark that paragraph as completed
* Maybe show a small checkmark

This feels seamless.

No page reload.
No context loss.
No mental friction.

This is the cleanest long-term design.

---


# Data Architecture for This

Right now you have:

`mmdd.json`

For learning/news, we could do this instead:

```
assets/data/content/news/2026-02-25.json
```

Structure:

```json
{
  "date": "2026-02-25",
  "title": "Today's News",
  "items": [
    {
      "id": "news-20260225-01",
      "title": "Federal Reserve Signals Rate Pause",
      "text": "The Federal Reserve indicated it may pause interest rate hikes...",
      "maskable": true,
      "cluechain": {
        "masked_words": 5,
        "difficulty": "medium"
      }
    },
    {
      "id": "news-20260225-02",
      "title": "Major Earthquake in Chile",
      "text": "...",
      "maskable": true
    }
  ]
}
```

Notice:

* Content is primary
* ClueChain metadata is secondary

This keeps it flexible.

---

# UI Design Pattern That Feels Premium

For each paragraph card:

```
-----------------------------------
Title
Paragraph text...

[ Practice with ClueChain ]
-----------------------------------
```

When completed:

* Button becomes:
  [ ✓ Completed – Score 82 ]

You are now gamifying reading, not forcing testing.

That is psychologically powerful.

---

# Very Important UX Detail

Do not auto-mask.

Let them read first.

Then choose to test themselves.

This keeps it learning-oriented, not game-oriented.

---

# Scaling This Beyond News

Same structure works for:

* AI mini-lessons
* Geography essays
* Short poems
* Algebra concepts
* Chemistry reactions
* Children’s book pages

Every content page is:

Content → optional ClueChain.

---

# Navigation Structure Suggestion

```
/learning/news/today
/learning/ai/basics/lesson-3
/learning/geography/neighbors/france
```

Each page:

* Is readable
* Has multiple ClueChain triggers

ClueChain becomes a reusable engine, not the primary container.

---

# Even Better: Dual Mode Toggle

At top of page:

[ Read Mode ]  |  [ Practice Mode ]

Read Mode:

* Clean text
* Optional practice buttons

Practice Mode:

* All paragraphs auto-masked
* Scroll and solve inline

Now you have:

* Casual learner mode
* Serious quiz mode

---

# My Strong Recommendation

For long-term elegance:

1. Keep content and puzzle separate.
2. Launch ClueChain inside a modal overlay.
3. Track completion per paragraph in localStorage.
4. Show visual completion markers.

That gives you:

* Netflix feel
* Duolingo reinforcement feel
* Newspaper reading feel
* Clean architecture


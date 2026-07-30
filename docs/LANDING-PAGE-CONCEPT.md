Here’s a clean landing page concept for `/cluechain/learningpacks` that stays slick even when you have 50+ packs. 
Think “Netflix rows” plus a simple filter bar.

## Page goal

Get a player into a learning pack in under 10 seconds, without making them think about your backend.

---

## Layout

### 1) Header

* Title: **Learning Packs**
* Subtext (one line): “Practice vocabulary through real paragraphs, news, poems, and mini-lessons.”
* Two buttons:

  * **Continue** (if they have progress in any pack)
  * **Browse all packs**

### 2) Filter bar (sticky)

Keep it minimal, with pills and one search box.

* Search: `Search packs...`
* Pills (multi-select):

  * Topic: AI, Geography, History, Literature, Poetry, Math, News
  * Level: Kids, Middle, High, Adult
  * Length: 3–5 min, 5–10 min, 10–20 min
  * Style: News bullets, Paragraph, Poem, Story
* Sort dropdown: Popular, New, Shortest, Easiest

### 3) Three primary sections (top of page)

These make the page feel curated, not like a dump of content.

#### A. Continue learning

A horizontal row of 1–5 cards, only if user has progress.

* Card shows:

  * Pack title
  * Progress bar (e.g., 6/20)
  * “Resume” button

#### B. Featured packs

Another row, hand-picked by you. 6 cards max.

Suggested featured starters:

* “News in 7 bullets (Daily)”
* “AI Foundations”
* “World Neighbors”
* “Poem a day”
* “Short Stories”
* “Algebra Vocabulary”

#### C. Quick start

Three big tiles (very clickable):

* **Start with News (5 min)**
* **Start with AI Basics (10 min)**
* **Start with Geography (10 min)**

### 4) Topic rows (the “Netflix” part)

Each topic gets a row with sideways scrolling cards.

* AI
* Geography
* History
* Literature & Short Stories
* Poetry
* Math

Each row shows 8 cards with a “See all” link.

### 5) Footer

* Link back to Daily puzzle
* “Suggest a pack” (just a mailto or GitHub issue link)

---

## Pack card design (what each card shows)

Keep it consistent and information-dense, but not cluttered.

**Card elements:**

* Title
* One-line description
* Badges: `Beginner` `5–10 min` `Poems` (max 3 badges)
* Progress (if started): “6/20”
* CTA button: **Start** or **Resume**

Optional but powerful:

* A small “streak” marker inside the card if someone is doing it daily.

---

## Information architecture (how you organize packs so the page works)

Every pack should have:

* `title`
* `slug`
* `topic`
* `level`
* `estimated_minutes`
* `style`
* `puzzle_count`
* `is_featured` (boolean)
* `updated_at` (for “New” sort)

This lets you build the whole page from `indexes/packs.json`.

---

## Two concrete homepage variants

### Variant 1: “Curated first” (best for polish)

Top half: Continue + Featured + Quick start
Bottom: topic rows

This feels premium and intentional.

### Variant 2: “Search first” (best when you have many packs)

Top half: Search + filters + “Popular now” row
Bottom: grid of results

This is more utilitarian.

My vote: Variant 1 now, and add Variant 2 later once you have lots of packs.

---

## Suggested URL structure

* `/` → Today’s Daily puzzle
* `/learningpacks` → landing page above
* `/learningpacks/:slug` → pack detail page (overview + Start/Resume + outline)


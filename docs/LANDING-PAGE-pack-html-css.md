Below is a minimal `packs.json` that can power the whole landing page (rows, filters, featured, sorting), plus a drop-in `learningpacks.html` + `learningpacks.css` layout (Netflix rows, sticky filter bar, cards, mobile-first).

## 1) Minimal `assets/data/indexes/packs.json`

```json
{
  "version": 1,
  "updated_at": "2026-02-25",
  "topics": [
    { "key": "news", "label": "News" },
    { "key": "ai", "label": "AI" },
    { "key": "geography", "label": "Geography" },
    { "key": "history", "label": "History" },
    { "key": "literature", "label": "Literature" },
    { "key": "poetry", "label": "Poetry" },
    { "key": "math", "label": "Math" }
  ],
  "levels": [
    { "key": "kids", "label": "Kids" },
    { "key": "middle", "label": "Middle" },
    { "key": "high", "label": "High" },
    { "key": "adult", "label": "Adult" }
  ],
  "packs": [
    {
      "slug": "news-7-bullets",
      "title": "News in 7 Bullets",
      "description": "Daily news bullets with masked vocabulary.",
      "topic": "news",
      "level": "adult",
      "style": "bullets",
      "minutes": 5,
      "puzzle_count": 30,
      "featured": true,
      "updated_at": "2026-02-25",
      "manifest_path": "assets/data/indexes/packs/news-7-bullets.json"
    },
    {
      "slug": "ai-basics",
      "title": "AI Foundations",
      "description": "Core AI and ML vocabulary through short paragraphs.",
      "topic": "ai",
      "level": "adult",
      "style": "paragraph",
      "minutes": 10,
      "puzzle_count": 20,
      "featured": true,
      "updated_at": "2026-02-20",
      "manifest_path": "assets/data/indexes/packs/ai-basics.json"
    },
    {
      "slug": "geography-neighbors",
      "title": "World Neighbors",
      "description": "Country and map vocabulary through border-based prompts.",
      "topic": "geography",
      "level": "high",
      "style": "paragraph",
      "minutes": 10,
      "puzzle_count": 25,
      "featured": true,
      "updated_at": "2026-02-18",
      "manifest_path": "assets/data/indexes/packs/geography-neighbors.json"
    }
  ],
  "rows": [
    { "key": "continue", "label": "Continue learning", "type": "continue" },
    { "key": "featured", "label": "Featured", "type": "featured" },
    { "key": "news", "label": "News", "type": "topic", "topic": "news" },
    { "key": "ai", "label": "AI", "type": "topic", "topic": "ai" },
    { "key": "geography", "label": "Geography", "type": "topic", "topic": "geography" },
    { "key": "history", "label": "History", "type": "topic", "topic": "history" },
    { "key": "literature", "label": "Literature & Stories", "type": "topic", "topic": "literature" },
    { "key": "poetry", "label": "Poetry", "type": "topic", "topic": "poetry" },
    { "key": "math", "label": "Math", "type": "topic", "topic": "math" }
  ]
}
```

Notes:

* `rows` lets you control the homepage order without hardcoding it in HTML/JS.
* `manifest_path` points to the per-pack manifest you already wanted.

---

## 2) `learningpacks.html` (Netflix rows + sticky filters)

This is static HTML first. You can later generate cards from `packs.json` with a tiny JS file, but this already gives you the layout.

```html
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>ClueChain | Learning Packs</title>
  <link rel='stylesheet' href='learningpacks.css' />
</head>

<body>
  <header class='topbar'>
    <div class='topbar-inner'>
      <a class='brand' href='/cluechain/'>ClueChain</a>

      <nav class='topnav'>
        <a href='/cluechain/'>Daily</a>
        <a class='active' href='/cluechain/learningpacks'>Learning Packs</a>
      </nav>
    </div>
  </header>

  <main class='page'>
    <section class='hero'>
      <div class='hero-copy'>
        <h1>Learning Packs</h1>
        <p>Practice vocabulary through real paragraphs, news, poems, and mini-lessons.</p>

        <div class='hero-actions'>
          <a class='btn primary' href='#continue'>Continue</a>
          <a class='btn' href='#browse'>Browse all packs</a>
        </div>
      </div>

      <div class='quickstart'>
        <h2>Quick start</h2>
        <div class='quickstart-grid'>
          <a class='tile' href='/cluechain/learningpacks/news-7-bullets'>
            <div class='tile-title'>Start with News</div>
            <div class='tile-sub'>About 5 minutes</div>
          </a>
          <a class='tile' href='/cluechain/learningpacks/ai-basics'>
            <div class='tile-title'>Start with AI Basics</div>
            <div class='tile-sub'>About 10 minutes</div>
          </a>
          <a class='tile' href='/cluechain/learningpacks/geography-neighbors'>
            <div class='tile-title'>Start with Geography</div>
            <div class='tile-sub'>About 10 minutes</div>
          </a>
        </div>
      </div>
    </section>

    <section class='filters' id='browse'>
      <div class='filters-inner'>
        <input class='search' type='search' placeholder='Search packs...' />

        <div class='pillbar' aria-label='Filters'>
          <button class='pill' type='button'>AI</button>
          <button class='pill' type='button'>Geography</button>
          <button class='pill' type='button'>History</button>
          <button class='pill' type='button'>Literature</button>
          <button class='pill' type='button'>Poetry</button>
          <button class='pill' type='button'>Math</button>
          <button class='pill' type='button'>News</button>
        </div>

        <div class='sort'>
          <label for='sort'>Sort</label>
          <select id='sort'>
            <option>Popular</option>
            <option>New</option>
            <option>Shortest</option>
            <option>Easiest</option>
          </select>
        </div>
      </div>
    </section>

    <!-- Continue learning -->
    <section class='row' id='continue'>
      <div class='row-head'>
        <h2>Continue learning</h2>
        <a class='row-link' href='/cluechain/learningpacks/library'>See all</a>
      </div>

      <div class='rail'>
        <a class='card' href='/cluechain/learningpacks/ai-basics'>
          <div class='card-top'>
            <div class='card-title'>AI Foundations</div>
            <div class='badges'>
              <span class='badge'>Adult</span>
              <span class='badge'>10 min</span>
              <span class='badge'>Paragraph</span>
            </div>
          </div>
          <div class='card-desc'>Core AI and ML vocabulary through short paragraphs.</div>
          <div class='progress'>
            <div class='progress-bar' style='width: 30%'></div>
          </div>
          <div class='card-cta'>Resume (6/20)</div>
        </a>
      </div>
    </section>

    <!-- Featured -->
    <section class='row'>
      <div class='row-head'>
        <h2>Featured</h2>
        <a class='row-link' href='/cluechain/learningpacks/library?featured=1'>See all</a>
      </div>

      <div class='rail'>
        <a class='card' href='/cluechain/learningpacks/news-7-bullets'>
          <div class='card-top'>
            <div class='card-title'>News in 7 Bullets</div>
            <div class='badges'>
              <span class='badge'>Adult</span>
              <span class='badge'>5 min</span>
              <span class='badge'>Bullets</span>
            </div>
          </div>
          <div class='card-desc'>Daily news bullets with masked vocabulary.</div>
          <div class='card-cta'>Start</div>
        </a>

        <a class='card' href='/cluechain/learningpacks/geography-neighbors'>
          <div class='card-top'>
            <div class='card-title'>World Neighbors</div>
            <div class='badges'>
              <span class='badge'>High</span>
              <span class='badge'>10 min</span>
              <span class='badge'>Paragraph</span>
            </div>
          </div>
          <div class='card-desc'>Country and map vocabulary through border-based prompts.</div>
          <div class='card-cta'>Start</div>
        </a>

        <a class='card' href='/cluechain/learningpacks/ai-basics'>
          <div class='card-top'>
            <div class='card-title'>AI Foundations</div>
            <div class='badges'>
              <span class='badge'>Adult</span>
              <span class='badge'>10 min</span>
              <span class='badge'>Paragraph</span>
            </div>
          </div>
          <div class='card-desc'>Core AI and ML vocabulary through short paragraphs.</div>
          <div class='card-cta'>Start</div>
        </a>
      </div>
    </section>

    <!-- Topic rows -->
    <section class='row'>
      <div class='row-head'>
        <h2>AI</h2>
        <a class='row-link' href='/cluechain/learningpacks/library?topic=ai'>See all</a>
      </div>
      <div class='rail'>
        <a class='card' href='/cluechain/learningpacks/ai-basics'>
          <div class='card-top'>
            <div class='card-title'>AI Foundations</div>
            <div class='badges'>
              <span class='badge'>Adult</span>
              <span class='badge'>10 min</span>
            </div>
          </div>
          <div class='card-desc'>Core AI and ML vocabulary through short paragraphs.</div>
          <div class='card-cta'>Start</div>
        </a>
      </div>
    </section>

    <section class='row'>
      <div class='row-head'>
        <h2>Geography</h2>
        <a class='row-link' href='/cluechain/learningpacks/library?topic=geography'>See all</a>
      </div>
      <div class='rail'>
        <a class='card' href='/cluechain/learningpacks/geography-neighbors'>
          <div class='card-top'>
            <div class='card-title'>World Neighbors</div>
            <div class='badges'>
              <span class='badge'>High</span>
              <span class='badge'>10 min</span>
            </div>
          </div>
          <div class='card-desc'>Country and map vocabulary through border-based prompts.</div>
          <div class='card-cta'>Start</div>
        </a>
      </div>
    </section>

    <footer class='footer'>
      <a href='/cluechain/'>Back to Daily</a>
      <span class='dot'>•</span>
      <a href='https://github.com/yourname/cluechain/issues'>Suggest a pack</a>
    </footer>
  </main>
</body>
</html>
```

---

## 3) `learningpacks.css` (slick, clean, mobile-first)

```css
:root {
  --bg: #0b0c10;
  --panel: #12141c;
  --text: #e8e9ee;
  --muted: #a6a9b6;
  --stroke: rgba(255,255,255,0.08);
  --shadow: 0 10px 30px rgba(0,0,0,0.35);
  --radius: 14px;
}

* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji';
}

a { color: inherit; text-decoration: none; }
a:hover { text-decoration: underline; }

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(11,12,16,0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--stroke);
}

.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  max-width: 1100px;
  margin: 0 auto;
  padding: 14px 16px;
}

.brand {
  font-weight: 700;
  letter-spacing: 0.3px;
}

.topnav {
  display: flex;
  gap: 14px;
  color: var(--muted);
  font-size: 14px;
}
.topnav a.active { color: var(--text); }

.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px;
}

.hero {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.hero h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
}
.hero p {
  margin: 0 0 14px 0;
  color: var(--muted);
  line-height: 1.4;
}

.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.04);
  font-weight: 600;
  font-size: 14px;
}
.btn.primary {
  background: rgba(255,255,255,0.12);
}

.quickstart h2 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: var(--muted);
  font-weight: 700;
  letter-spacing: 0.2px;
}

.quickstart-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.tile {
  border: 1px solid var(--stroke);
  border-radius: 14px;
  padding: 14px;
  background: rgba(255,255,255,0.03);
}
.tile:hover {
  background: rgba(255,255,255,0.06);
  text-decoration: none;
}
.tile-title { font-weight: 800; }
.tile-sub { color: var(--muted); font-size: 13px; margin-top: 6px; }

.filters {
  position: sticky;
  top: 52px;
  z-index: 15;
  margin-top: 14px;
  padding: 10px 0;
  background: rgba(11,12,16,0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--stroke);
}

.filters-inner {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  align-items: center;
}

.search {
  width: 100%;
  padding: 12px 12px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: var(--text);
  outline: none;
}
.search::placeholder { color: rgba(232,233,238,0.55); }

.pillbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: var(--text);
  border-radius: 999px;
  padding: 8px 10px;
  font-size: 13px;
  cursor: pointer;
}
.pill:hover { background: rgba(255,255,255,0.06); }

.sort {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
}
.sort select {
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: var(--text);
}

.row {
  margin-top: 18px;
}

.row-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.row h2 {
  margin: 0;
  font-size: 18px;
}

.row-link {
  color: var(--muted);
  font-size: 13px;
}

.rail {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(240px, 280px);
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  scroll-snap-type: x mandatory;
}
.rail::-webkit-scrollbar { height: 10px; }
.rail::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 999px; }
.rail::-webkit-scrollbar-track { background: rgba(255,255,255,0.04); border-radius: 999px; }

.card {
  scroll-snap-align: start;
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 14px;
  background: rgba(255,255,255,0.03);
  box-shadow: 0 10px 24px rgba(0,0,0,0.22);
  min-height: 170px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card:hover { background: rgba(255,255,255,0.06); text-decoration: none; }

.card-title {
  font-weight: 900;
  font-size: 16px;
  letter-spacing: 0.2px;
}
.card-desc {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.35;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.badge {
  font-size: 12px;
  color: rgba(232,233,238,0.88);
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  border-radius: 999px;
  padding: 5px 8px;
}

.progress {
  height: 8px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: rgba(255,255,255,0.18);
}

.card-cta {
  margin-top: auto;
  font-weight: 800;
  font-size: 14px;
  color: rgba(232,233,238,0.95);
}

.footer {
  margin: 26px 0 10px 0;
  padding-top: 18px;
  border-top: 1px solid var(--stroke);
  color: var(--muted);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.footer .dot { opacity: 0.6; }

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.2fr 0.8fr;
    align-items: start;
  }
  .quickstart-grid {
    grid-template-columns: 1fr;
  }
  .filters-inner {
    grid-template-columns: 1.1fr 2fr 0.9fr;
    gap: 12px;
  }
}
```

---

## File placement suggestion (GitHub Pages)

* `cluechain/learningpacks/index.html` (or `learningpacks.html` and route it)
* `cluechain/learningpacks/learningpacks.css`
* `cluechain/assets/data/indexes/packs.json`

If you want the page to be exactly `/cluechain/learningpacks` (no `.html`), make it `learningpacks/index.html`.


With Jekyll, you can make this landing page almost entirely build-time (Liquid), and keep only a tiny bit of JS later for search and filters.

## 1) Put the data in Jekyll `_data/`

Create:

`_data/packs.json`

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
      "updated_at": "2026-02-25"
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
      "updated_at": "2026-02-20"
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
      "updated_at": "2026-02-18"
    }
  ],
  "rows": [
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

Jekyll will expose it at: `site.data.packs`

---

## 2) Add a reusable card include

Create:

`_includes/pack_card.html`

```html
{% assign p = include.pack %}
<a class='card'
   href='{{ "/learningpacks/" | append: p.slug | relative_url }}'
   data-topic='{{ p.topic }}'
   data-level='{{ p.level }}'
   data-style='{{ p.style }}'
   data-minutes='{{ p.minutes }}'
   data-title='{{ p.title | downcase }}'
   data-desc='{{ p.description | downcase }}'>

  <div class='card-top'>
    <div class='card-title'>{{ p.title }}</div>
    <div class='badges'>
      <span class='badge'>{{ p.level | capitalize }}</span>
      <span class='badge'>{{ p.minutes }} min</span>
      <span class='badge'>{{ p.style | capitalize }}</span>
    </div>
  </div>

  <div class='card-desc'>{{ p.description }}</div>
  <div class='card-cta'>Start</div>
</a>
```

Those `data-*` attributes are there so you can filter later with tiny JS.

---

## 3) Create the landing page

Create:

`learningpacks/index.html`

```html
---
layout: default
title: Learning Packs
permalink: /learningpacks/
---

<link rel='stylesheet' href='{{ "/assets/css/learningpacks.css" | relative_url }}' />

<main class='page'>
  <section class='hero'>
    <div class='hero-copy'>
      <h1>Learning Packs</h1>
      <p>Practice vocabulary through real paragraphs, news, poems, and mini-lessons.</p>

      <div class='hero-actions'>
        <a class='btn primary' href='#featured'>Browse featured</a>
        <a class='btn' href='#browse'>Browse all</a>
      </div>
    </div>

    <div class='quickstart'>
      <h2>Quick start</h2>
      <div class='quickstart-grid'>
        <a class='tile' href='{{ "/learningpacks/news-7-bullets" | relative_url }}'>
          <div class='tile-title'>Start with News</div>
          <div class='tile-sub'>About 5 minutes</div>
        </a>
        <a class='tile' href='{{ "/learningpacks/ai-basics" | relative_url }}'>
          <div class='tile-title'>Start with AI Basics</div>
          <div class='tile-sub'>About 10 minutes</div>
        </a>
        <a class='tile' href='{{ "/learningpacks/geography-neighbors" | relative_url }}'>
          <div class='tile-title'>Start with Geography</div>
          <div class='tile-sub'>About 10 minutes</div>
        </a>
      </div>
    </div>
  </section>

  <section class='filters' id='browse'>
    <div class='filters-inner'>
      <input id='packSearch' class='search' type='search' placeholder='Search packs...' />

      <div class='pillbar' aria-label='Filters'>
        {% for t in site.data.packs.topics %}
          <button class='pill' type='button' data-filter-topic='{{ t.key }}'>{{ t.label }}</button>
        {% endfor %}
      </div>

      <div class='sort'>
        <label for='packSort'>Sort</label>
        <select id='packSort'>
          <option value='featured'>Featured</option>
          <option value='new'>New</option>
          <option value='short'>Shortest</option>
          <option value='easy'>Easiest</option>
        </select>
      </div>
    </div>
  </section>

  {% assign packs = site.data.packs.packs %}

  <!-- Featured row -->
  <section class='row' id='featured'>
    <div class='row-head'>
      <h2>Featured</h2>
    </div>

    <div class='rail' id='row-featured'>
      {% for p in packs %}
        {% if p.featured %}
          {% include pack_card.html pack=p %}
        {% endif %}
      {% endfor %}
    </div>
  </section>

  <!-- Topic rows defined by data -->
  {% for r in site.data.packs.rows %}
    {% if r.type == "topic" %}
      <section class='row' id='row-{{ r.key }}'>
        <div class='row-head'>
          <h2>{{ r.label }}</h2>
          <a class='row-link' href='{{ "/learningpacks/library?topic=" | append: r.topic | relative_url }}'>See all</a>
        </div>

        <div class='rail' data-row-topic='{{ r.topic }}'>
          {% for p in packs %}
            {% if p.topic == r.topic %}
              {% include pack_card.html pack=p %}
            {% endif %}
          {% endfor %}
        </div>
      </section>
    {% endif %}
  {% endfor %}

  <footer class='footer'>
    <a href='{{ "/" | relative_url }}'>Back to Daily</a>
    <span class='dot'>•</span>
    <a href='https://github.com/yourname/cluechain/issues'>Suggest a pack</a>
  </footer>
</main>

<script src='{{ "/assets/js/learningpacks.js" | relative_url }}'></script>
```

Note: `relative_url` is what keeps GitHub Pages `baseurl` safe.

---

## 4) CSS file

Create:

`assets/css/learningpacks.css`

Use the CSS I gave you earlier (it works as-is). If your `default` layout already sets global fonts/colors, you can keep only the classes that matter, but it’s fine to drop it in whole.

---

## 5) Tiny JS for search + topic filter (optional but nice)

Create:

`assets/js/learningpacks.js`

```js
(function () {
  const searchEl = document.getElementById('packSearch');
  const sortEl = document.getElementById('packSort');
  const pills = Array.from(document.querySelectorAll('.pill[data-filter-topic]'));

  let activeTopic = null;

  function matches(card, q) {
    const title = card.getAttribute('data-title') || '';
    const desc = card.getAttribute('data-desc') || '';
    return title.includes(q) || desc.includes(q);
  }

  function applyFilters() {
    const q = (searchEl?.value || '').trim().toLowerCase();

    const allCards = Array.from(document.querySelectorAll('.card'));
    allCards.forEach(card => {
      const topic = card.getAttribute('data-topic');
      const okTopic = !activeTopic || topic === activeTopic;
      const okSearch = !q || matches(card, q);
      card.style.display = (okTopic && okSearch) ? '' : 'none';
    });

    // Hide entire rails if everything inside is hidden
    const rails = Array.from(document.querySelectorAll('.rail'));
    rails.forEach(rail => {
      const anyVisible = Array.from(rail.querySelectorAll('.card')).some(c => c.style.display !== 'none');
      const row = rail.closest('.row');
      if (row) row.style.display = anyVisible ? '' : 'none';
    });
  }

  pills.forEach(p => {
    p.addEventListener('click', () => {
      const topic = p.getAttribute('data-filter-topic');
      activeTopic = (activeTopic === topic) ? null : topic;

      pills.forEach(x => x.classList.toggle('active', x.getAttribute('data-filter-topic') === activeTopic));
      applyFilters();
    });
  });

  if (searchEl) searchEl.addEventListener('input', applyFilters);

  // Sort is a placeholder hook. You can implement later when you add a grid/library page.
  if (sortEl) sortEl.addEventListener('change', () => applyFilters());

  applyFilters();
})();
```

Add one CSS rule to show active pill:

```css
.pill.active {
  background: rgba(255,255,255,0.12);
}
```

---

## 6) One more Jekyll-friendly improvement

If you want a pack detail page per slug later, do this:

* create a collection `_learningpacks/`
* each pack becomes a markdown file with front matter (`slug`, `title`, `description`, etc.)
* Jekyll generates `/learningpacks/<slug>/` pages automatically

But you don’t need that yet. The landing page above works today.

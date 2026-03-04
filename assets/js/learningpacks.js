/* learningpacks.js — powers learning/index.html */

(function () {
  // Resolve the correct path to packs.json regardless of nesting depth.
  // learning/index.html is one level deep from repo root, so ../assets/data/...
  const PACKS_URL = '../assets/data/indexes/packs.json';

  let allPacks = [];
  let activeTopics = new Set();
  let searchQuery = '';

  // ── Data loading ──────────────────────────────────────────────────────────

  async function loadPacks() {
    const res = await fetch(PACKS_URL);
    if (!res.ok) throw new Error('Failed to load packs.json: ' + res.status);
    return res.json();
  }

  // ── Card factory ──────────────────────────────────────────────────────────

  function makeCard(pack) {
    const a = document.createElement('a');
    a.className = 'card';
    a.href = pack.url ? pack.url : `../${pack.slug}/`;
    a.dataset.topic = pack.topic;
    a.dataset.title = pack.title.toLowerCase();
    a.dataset.desc = pack.description.toLowerCase();

    const levelLabel = pack.level.charAt(0).toUpperCase() + pack.level.slice(1);
    const styleLabel = pack.style.charAt(0).toUpperCase() + pack.style.slice(1);

    a.innerHTML = `
      <div class="card-top">
        <div class="card-title">${escHtml(pack.title)}</div>
        <div class="badges">
          <span class="badge">${escHtml(levelLabel)}</span>
          <span class="badge">${pack.minutes} min</span>
          <span class="badge">${escHtml(styleLabel)}</span>
        </div>
      </div>
      <div class="card-desc">${escHtml(pack.description)}</div>
      <div class="card-cta">Start</div>
    `;
    return a;
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Row builder ───────────────────────────────────────────────────────────

  function buildRows(data) {
    const rowsContainer = document.getElementById('rows-container');
    if (!rowsContainer) return;

    data.rows.forEach(rowDef => {
      // "continue" row requires localStorage — skip for now
      if (rowDef.type === 'continue') return;

      let packs;
      if (rowDef.type === 'featured') {
        packs = data.packs.filter(p => p.featured);
      } else if (rowDef.type === 'topic') {
        packs = data.packs.filter(p => p.topic === rowDef.topic);
      } else {
        return;
      }

      if (packs.length === 0) return;

      const section = document.createElement('section');
      section.className = 'row';
      section.dataset.rowType = rowDef.type;
      section.dataset.rowTopic = rowDef.topic || '';

      const headDiv = document.createElement('div');
      headDiv.className = 'row-head';
      headDiv.innerHTML = `<h2>${escHtml(rowDef.label)}</h2>`;
      section.appendChild(headDiv);

      const rail = document.createElement('div');
      rail.className = 'rail';
      packs.forEach(p => rail.appendChild(makeCard(p)));
      section.appendChild(rail);

      rowsContainer.appendChild(section);
    });
  }

  // ── Quick-start tiles ─────────────────────────────────────────────────────

  function buildQuickStart(packs) {
    const grid = document.getElementById('quickstart-grid');
    if (!grid) return;
    grid.innerHTML = '';
    const featured = packs.filter(p => p.featured).slice(0, 3);
    featured.forEach(p => {
      const a = document.createElement('a');
      a.className = 'tile';
      a.href = p.url ? p.url : `../${p.slug}/`;
      a.innerHTML = `
        <div class="tile-title">Start with ${escHtml(p.title)}</div>
        <div class="tile-sub">About ${p.minutes} minutes</div>
      `;
      grid.appendChild(a);
    });
  }

  // ── Topic pills ───────────────────────────────────────────────────────────

  function buildPills(topics) {
    const pillbar = document.getElementById('pillbar');
    if (!pillbar) return;
    pillbar.innerHTML = '';
    topics.forEach(t => {
      const btn = document.createElement('button');
      btn.className = 'pill';
      btn.type = 'button';
      btn.textContent = t.label;
      btn.dataset.topic = t.key;
      btn.addEventListener('click', () => toggleTopic(t.key, btn));
      pillbar.appendChild(btn);
    });
  }

  // ── Filtering ─────────────────────────────────────────────────────────────

  function toggleTopic(key, btn) {
    if (activeTopics.has(key)) {
      activeTopics.delete(key);
      btn.classList.remove('active');
    } else {
      activeTopics.add(key);
      btn.classList.add('active');
    }
    applyFilters();
  }

  function applyFilters() {
    const q = searchQuery.trim().toLowerCase();
    const rows = document.querySelectorAll('#rows-container .row');

    rows.forEach(row => {
      const cards = row.querySelectorAll('.card');
      let visibleCount = 0;

      cards.forEach(card => {
        const matchesTopic = activeTopics.size === 0 || activeTopics.has(card.dataset.topic);
        const matchesSearch = !q ||
          card.dataset.title.includes(q) ||
          card.dataset.desc.includes(q);

        const visible = matchesTopic && matchesSearch;
        card.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
      });

      // Hide entire row if nothing matches
      row.style.display = visibleCount === 0 ? 'none' : '';
    });
  }

  // ── Wire up search ────────────────────────────────────────────────────────

  function wireSearch() {
    const input = document.getElementById('search-input');
    if (!input) return;
    input.addEventListener('input', e => {
      searchQuery = e.target.value;
      applyFilters();
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      const data = await loadPacks();
      allPacks = data.packs;

      buildQuickStart(allPacks);
      buildPills(data.topics);
      buildRows(data);
      wireSearch();
    } catch (err) {
      console.error('ClueChain learning packs:', err);
    }
  });
})();

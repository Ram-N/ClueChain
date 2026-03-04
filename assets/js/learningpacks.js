/* learningpacks.js — powers learning/index.html */

(function () {
  const PACKS_URL = '../assets/data/indexes/packs.json';

  // Topic display names and icons
  const TOPIC_ICONS = {
    news: '📰',
    ai: '🤖',
    geography: '🌍',
    history: '📜',
    literature: '📚',
    poetry: '✍️',
    math: '🔢',
  };

  const TOPIC_LABELS = {
    news: 'News',
    ai: 'AI',
    geography: 'Geography',
    history: 'History',
    literature: 'Literature',
    poetry: 'Poetry',
    math: 'Math',
  };

  // ── Helpers ───────────────────────────────────────────────────────────────

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function fetchUnitCount(pack) {
    if (!pack.manifest_path) return null;
    try {
      const res = await fetch('../' + pack.manifest_path);
      if (!res.ok) return null;
      const data = await res.json();
      if (Array.isArray(data.units)) return data.units.length;
    } catch (_) {
      // fall through
    }
    return null;
  }

  // ── Card factory ──────────────────────────────────────────────────────────

  function makeCard(pack, unitCount) {
    const a = document.createElement('a');
    a.className = 'pack-card';
    a.href = pack.url ? pack.url : `../${pack.slug}/`;

    const icon = TOPIC_ICONS[pack.topic] || '📖';
    const topicLabel = TOPIC_LABELS[pack.topic] || pack.topic;

    const count = unitCount !== null ? unitCount : pack.puzzle_count;
    const countLabel = unitCount !== null
      ? `${count} unit${count !== 1 ? 's' : ''}`
      : `${count} puzzle${count !== 1 ? 's' : ''}`;

    a.innerHTML = `
      <div class="pack-icon">${icon}</div>
      <div class="pack-title">${escHtml(pack.title)}</div>
      <span class="pack-topic">${escHtml(topicLabel)}</span>
      <div class="pack-desc">${escHtml(pack.description)}</div>
      <div class="pack-footer">
        <span class="pack-count">${countLabel}</span>
        <span class="pack-cta">Start →</span>
      </div>
    `;
    return a;
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', async () => {
    const grid = document.getElementById('pack-grid');
    if (!grid) return;

    try {
      const res = await fetch(PACKS_URL);
      if (!res.ok) throw new Error('Failed to load packs.json: ' + res.status);
      const data = await res.json();
      const packs = data.packs || [];

      // Fetch unit counts for all packs in parallel
      const counts = await Promise.all(packs.map(fetchUnitCount));

      packs.forEach((pack, i) => {
        grid.appendChild(makeCard(pack, counts[i]));
      });
    } catch (err) {
      console.error('ClueChain learning packs:', err);
    }
  });
})();

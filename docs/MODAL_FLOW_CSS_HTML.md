Below is a practical modal state machine (states, events, transitions) plus a plain HTML/CSS/JS “news unit” page template that:

* loads a `content_unit` JSON (7 items)
* renders each item in Read mode
* opens a Practice modal for any item
* supports difficulty (Easy/Standard/Advanced)
* supports Read vs Practice mode toggle
* returns to the same scroll position and item anchor on close

Everything is plain HTML/CSS/JS. No Jekyll, no Liquid.

---

## 1) Modal state machine

### States

* `CLOSED`
* `OPENING` (optional animation)
* `READY` (masked text rendered, waiting for interaction)
* `FOCUS_BLANK` (a blank is selected)
* `CHECKING` (validating a guess)
* `FEEDBACK` (show correct/incorrect feedback briefly)
* `SUMMARY` (completed item)
* `ERROR`

### Core events

* `OPEN({ unit, itemIndex, difficulty, returnTo })`
* `CLOSE()`
* `SELECT_BLANK({ blankIndex })`
* `INPUT_CHANGE({ value })`
* `SUBMIT_GUESS()`
* `USE_HINT({ layer })`
* `REVEAL_WORD()`
* `REVEAL_ALL()`
* `NEXT_BLANK()`
* `PREV_BLANK()`
* `NEXT_ITEM()` (optional if you practice sequentially)
* `RETRY()` (optional)
* `COMPLETE()`
* `FAIL({ message })`

### Transition sketch

* `CLOSED --OPEN--> OPENING -> READY`
* `READY --SELECT_BLANK--> FOCUS_BLANK`
* `FOCUS_BLANK --SUBMIT_GUESS--> CHECKING -> FEEDBACK -> (FOCUS_BLANK or COMPLETE)`
* `READY/FOCUS_BLANK --USE_HINT/REVEAL_WORD--> FOCUS_BLANK`
* `READY/FOCUS_BLANK --REVEAL_ALL--> SUMMARY`
* `SUMMARY --CLOSE--> CLOSED`
* any state `--FAIL--> ERROR`
* `ERROR --CLOSE--> CLOSED`

---

## 2) Page template: `news.html`

Assume you open it like:

* `news.html?unit=assets/data/units/news/yyyy/2026/02/25.json`

```html
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>ClueChain News</title>
  <link rel='stylesheet' href='news.css' />
</head>

<body>
  <header class='topbar'>
    <div class='topbar-inner'>
      <a class='brand' href='./index.html'>ClueChain</a>

      <div class='toolbar'>
        <div class='segmented' role='tablist' aria-label='Mode'>
          <button id='modeRead' class='segbtn active' type='button'>Read</button>
          <button id='modePractice' class='segbtn' type='button'>Practice</button>
        </div>

        <div class='difficulty'>
          <label for='difficultySelect'>Difficulty</label>
          <select id='difficultySelect'>
            <option value='easy'>Easy</option>
            <option value='standard' selected>Standard</option>
            <option value='advanced'>Advanced</option>
          </select>
        </div>
      </div>
    </div>
  </header>

  <main class='page'>
    <section class='hero'>
      <h1 id='unitTitle'>Today&apos;s News</h1>
      <div class='meta'>
        <span id='unitDate'></span>
        <span class='dot'>•</span>
        <span id='unitSubtitle'>7 items</span>
      </div>
    </section>

    <section id='items' class='items'></section>
  </main>

  <!-- Modal -->
  <div id='modalRoot' class='modal-root' aria-hidden='true'>
    <div class='modal-backdrop' data-action='close'></div>

    <div class='modal' role='dialog' aria-modal='true' aria-label='Practice modal'>
      <div class='modal-top'>
        <button class='iconbtn' type='button' data-action='close'>Back</button>

        <div class='modal-top-center'>
          <div id='modalTitle' class='modal-title'>Practice</div>
          <div id='modalSub' class='modal-sub'>Item 1 of 7</div>
        </div>

        <div id='modalScore' class='modal-score'>0 / 100</div>
      </div>

      <div class='modal-body'>
        <div class='modal-text'>
          <div id='maskedText' class='masked-text'></div>
        </div>

        <aside class='modal-panel'>
          <div class='panel-row'>
            <div class='panel-label'>Blank</div>
            <div id='blankMeta' class='panel-meta'>Select a blank</div>
          </div>

          <div class='panel-row'>
            <input id='guessInput' class='guess' type='text' placeholder='Type your guess...' autocomplete='off' />
            <button id='submitGuess' class='btn primary' type='button'>Submit</button>
          </div>

          <div class='panel-row hints'>
            <button class='btn' type='button' data-hint='direct'>Hint 1</button>
            <button class='btn' type='button' data-hint='intermediate'>Hint 2</button>
            <button class='btn' type='button' data-hint='indirect'>Hint 3</button>
          </div>

          <div id='hintBox' class='hint-box' aria-live='polite'></div>

          <div class='panel-row'>
            <button id='revealWord' class='btn danger' type='button'>Reveal word</button>
            <button id='revealAll' class='btn danger' type='button'>Reveal all</button>
          </div>

          <div class='panel-row nav'>
            <button id='prevBlank' class='btn' type='button'>Prev</button>
            <button id='nextBlank' class='btn' type='button'>Next</button>
          </div>
        </aside>
      </div>

      <div id='summary' class='modal-summary hidden'>
        <div class='summary-title'>Completed</div>
        <div id='summaryDetail' class='summary-detail'></div>
        <div class='summary-actions'>
          <button id='summaryClose' class='btn primary' type='button'>Return to reading</button>
          <button id='summaryNextItem' class='btn' type='button'>Practice next item</button>
        </div>
      </div>
    </div>
  </div>

  <script src='news.js'></script>
</body>
</html>
```

---

## 3) Minimal CSS: `news.css`

This is intentionally small. You can blend it with your existing styling.

```css
:root {
  --bg: #0b0c10;
  --panel: #12141c;
  --text: #e8e9ee;
  --muted: #a6a9b6;
  --stroke: rgba(255,255,255,0.08);
  --radius: 14px;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
}
a { color: inherit; text-decoration: none; }
a:hover { text-decoration: underline; }

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(11,12,16,0.9);
  border-bottom: 1px solid var(--stroke);
  backdrop-filter: blur(10px);
}
.topbar-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.brand { font-weight: 800; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.segmented {
  display: inline-flex;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  overflow: hidden;
}
.segbtn {
  padding: 8px 10px;
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
}
.segbtn.active {
  background: rgba(255,255,255,0.12);
  color: var(--text);
}
.difficulty {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}
.difficulty select {
  background: rgba(255,255,255,0.03);
  color: var(--text);
  border: 1px solid var(--stroke);
  border-radius: 10px;
  padding: 8px 10px;
}

.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px;
}
.hero {
  padding: 14px 0 8px 0;
}
.hero h1 { margin: 0 0 6px 0; font-size: 26px; }
.meta { color: var(--muted); font-size: 13px; }
.dot { margin: 0 8px; opacity: 0.7; }

.items {
  display: grid;
  gap: 12px;
  margin-top: 10px;
}
.item {
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  background: rgba(255,255,255,0.03);
  padding: 14px;
}
.item h2 {
  margin: 0 0 8px 0;
  font-size: 16px;
}
.item p {
  margin: 0;
  color: rgba(232,233,238,0.92);
  line-height: 1.45;
}
.item-footer {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
}
.item-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.pill {
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: var(--text);
  border-radius: 999px;
  padding: 6px 10px;
  cursor: pointer;
}
.pill:hover { background: rgba(255,255,255,0.06); }

.modal-root {
  position: fixed;
  inset: 0;
  display: none;
  z-index: 50;
}
.modal-root.open { display: block; }
.modal-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.6);
}
.modal {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(1100px, calc(100vw - 24px));
  height: min(720px, calc(100vh - 24px));
  transform: translate(-50%, -50%);
  background: var(--panel);
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  overflow: hidden;
  display: grid;
  grid-template-rows: auto 1fr;
}
.modal-top {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid var(--stroke);
}
.iconbtn {
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--stroke);
  color: var(--text);
  border-radius: 10px;
  padding: 8px 10px;
  cursor: pointer;
}
.modal-title { font-weight: 800; }
.modal-sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
.modal-score { color: var(--muted); font-weight: 700; }

.modal-body {
  display: grid;
  grid-template-columns: 1.6fr 0.9fr;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
}
.modal-text {
  overflow: auto;
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 12px;
  background: rgba(255,255,255,0.02);
}
.masked-text { line-height: 1.6; }

.blank {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 10px;
  border: 1px dashed rgba(255,255,255,0.22);
  margin: 0 2px;
  cursor: pointer;
}
.blank.active {
  border-style: solid;
  background: rgba(255,255,255,0.12);
}
.blank.solved {
  border-style: solid;
  border-color: rgba(255,255,255,0.22);
  background: rgba(255,255,255,0.06);
  cursor: default;
}

.modal-panel {
  overflow: auto;
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 12px;
  background: rgba(255,255,255,0.02);
}
.panel-row { margin-bottom: 10px; }
.panel-label { color: var(--muted); font-size: 12px; }
.panel-meta { margin-top: 4px; }

.guess {
  width: 100%;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: var(--text);
  outline: none;
}
.btn {
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: var(--text);
  cursor: pointer;
}
.btn.primary { background: rgba(255,255,255,0.12); font-weight: 800; }
.btn.danger { background: rgba(255,255,255,0.06); }

.hints { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.hint-box {
  min-height: 44px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,0.03);
  color: rgba(232,233,238,0.92);
}

.nav { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

.modal-summary {
  position: absolute;
  inset: 56px 0 0 0;
  background: rgba(18,20,28,0.98);
  border-top: 1px solid var(--stroke);
  padding: 16px;
}
.hidden { display: none; }
.summary-title { font-weight: 900; font-size: 18px; }
.summary-detail { color: var(--muted); margin-top: 6px; }
.summary-actions { margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; }

@media (max-width: 900px) {
  .modal {
    left: 0;
    top: 0;
    transform: none;
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }
  .modal-body {
    grid-template-columns: 1fr;
  }
}
```

---

## 4) JavaScript: `news.js`

This includes:

* unit loading
* page render (items, practice buttons)
* modal state machine with reducer + effects
* a simple blanking engine (auto mode) so you can run this without authored variants

It’s long, but it’s meant to be copy-paste runnable and then refined.

```js
'use strict'

function qs(sel, root = document) {
  return root.querySelector(sel)
}

function qsa(sel, root = document) {
  return Array.from(root.querySelectorAll(sel))
}

function getParam(name) {
  const url = new URL(window.location.href)
  return url.searchParams.get(name)
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n))
}

function slugKey(s) {
  return String(s || '').trim().toLowerCase()
}

function nowISODate() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/* ---------------------------
   Minimal blanking engine
   - picks candidate words
   - replaces selected occurrences with blanks
   --------------------------- */

const STOPWORDS = new Set([
  'the','a','an','and','or','but','if','then','so','to','of','in','on','for','with','as','at','by','from',
  'is','are','was','were','be','been','being','it','this','that','these','those','their','there','here',
  'you','your','we','our','they','them','he','him','she','her','i','me','my','mine',
  'not','no','yes','do','does','did','doing','done','can','could','will','would','should','may','might','must'
])

function tokenizeWithSpans(text) {
  // Returns array of { t, isWord }
  // Keeps punctuation as separate tokens so we can re-join without losing formatting.
  const re = /([A-Za-z']+)|(\s+)|([^A-Za-z'\s]+)/g
  const out = []
  let m
  while ((m = re.exec(text)) !== null) {
    const word = m[1]
    const space = m[2]
    const other = m[3]
    if (word) out.push({ t: word, isWord: true })
    else if (space) out.push({ t: space, isWord: false })
    else out.push({ t: other, isWord: false })
  }
  return out
}

function chooseBlankTargets(text, difficulty, practiceCfg) {
  const targets = practiceCfg?.blanking?.targets || {}
  const t = targets[difficulty] || targets.standard || { min_blanks: 6, max_blanks: 8 }
  const minB = t.min_blanks ?? 6
  const maxB = t.max_blanks ?? 8
  const want = clamp(Math.floor((minB + maxB) / 2), 1, 20)

  const tokens = tokenizeWithSpans(text)
  const wordIdxs = []
  for (let i = 0; i < tokens.length; i += 1) {
    if (!tokens[i].isWord) continue
    const w = tokens[i].t
    const lw = w.toLowerCase()
    if (practiceCfg?.blanking?.avoid?.stopwords && STOPWORDS.has(lw)) continue
    if (practiceCfg?.blanking?.avoid?.very_short_words_max_len && w.length <= practiceCfg.blanking.avoid.very_short_words_max_len) continue
    if (practiceCfg?.blanking?.avoid?.numbers && /\d/.test(w)) continue
    wordIdxs.push(i)
  }

  // Prefer longer words on advanced
  wordIdxs.sort((a, b) => tokens[b].t.length - tokens[a].t.length)

  // Take a spread across the text
  const chosen = []
  if (wordIdxs.length === 0) return { tokens, blanks: [] }

  const step = Math.max(1, Math.floor(wordIdxs.length / want))
  for (let i = 0; i < wordIdxs.length && chosen.length < want; i += step) {
    chosen.push(wordIdxs[i])
  }

  // If still short, fill randomly from remaining
  const remaining = wordIdxs.filter(i => !chosen.includes(i))
  while (chosen.length < want && remaining.length > 0) {
    const j = Math.floor(Math.random() * remaining.length)
    chosen.push(remaining.splice(j, 1)[0])
  }

  chosen.sort((a, b) => a - b)

  const blanks = chosen.map((tokIndex, k) => {
    const answer = tokens[tokIndex].t
    return {
      blankIndex: k,
      tokIndex,
      answer,
      solved: false,
      revealed: false,
      usedHints: { direct: false, intermediate: false, indirect: false }
    }
  })

  return { tokens, blanks }
}

function renderMaskedHTML(tokens, blanks, activeBlankIndex) {
  const blankByTok = new Map()
  for (const b of blanks) blankByTok.set(b.tokIndex, b)

  const parts = []
  for (let i = 0; i < tokens.length; i += 1) {
    const tok = tokens[i]
    const b = blankByTok.get(i)
    if (!b) {
      parts.push(escapeHTML(tok.t))
      continue
    }

    const shown = b.solved || b.revealed ? b.answer : '____'
    const cls = [
      'blank',
      b.solved ? 'solved' : '',
      b.blankIndex === activeBlankIndex ? 'active' : ''
    ].join(' ').trim()

    parts.push(
      `<span class='${cls}' data-blank-index='${b.blankIndex}' role='button' tabindex='0'>${escapeHTML(shown)}</span>`
    )
  }

  return parts.join('')
}

function escapeHTML(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

/* ---------------------------
   Modal state machine
   --------------------------- */

const ModalStates = {
  CLOSED: 'CLOSED',
  OPENING: 'OPENING',
  READY: 'READY',
  FOCUS_BLANK: 'FOCUS_BLANK',
  CHECKING: 'CHECKING',
  FEEDBACK: 'FEEDBACK',
  SUMMARY: 'SUMMARY',
  ERROR: 'ERROR'
}

function initialModalState() {
  return {
    status: ModalStates.CLOSED,
    unit: null,
    itemIndex: -1,
    difficulty: 'standard',
    returnTo: { hash: '', scrollY: 0 },
    tokens: [],
    blanks: [],
    activeBlankIndex: -1,
    guess: '',
    score: 0,
    maxPoints: 100,
    lastFeedback: '',
    hintText: '',
    completed: false,
    error: ''
  }
}

function reducer(state, evt) {
  switch (evt.type) {
    case 'OPEN': {
      return {
        ...state,
        status: ModalStates.OPENING,
        unit: evt.payload.unit,
        itemIndex: evt.payload.itemIndex,
        difficulty: evt.payload.difficulty,
        returnTo: evt.payload.returnTo,
        tokens: [],
        blanks: [],
        activeBlankIndex: -1,
        guess: '',
        score: 0,
        lastFeedback: '',
        hintText: '',
        completed: false,
        error: ''
      }
    }

    case 'OPENED_READY': {
      return {
        ...state,
        status: ModalStates.READY,
        tokens: evt.payload.tokens,
        blanks: evt.payload.blanks,
        activeBlankIndex: evt.payload.blanks.length ? 0 : -1
      }
    }

    case 'SELECT_BLANK': {
      if (state.status === ModalStates.SUMMARY || state.status === ModalStates.ERROR) return state
      return {
        ...state,
        status: ModalStates.FOCUS_BLANK,
        activeBlankIndex: evt.payload.blankIndex,
        guess: '',
        lastFeedback: '',
        hintText: ''
      }
    }

    case 'INPUT_CHANGE': {
      return { ...state, guess: evt.payload.value }
    }

    case 'SUBMIT_GUESS': {
      if (state.activeBlankIndex < 0) return state
      return { ...state, status: ModalStates.CHECKING, lastFeedback: '' }
    }

    case 'GUESS_RESULT': {
      const { correct, newBlanks, deltaScore, feedback } = evt.payload
      const done = newBlanks.every(b => b.solved || b.revealed)

      return {
        ...state,
        status: done ? ModalStates.SUMMARY : ModalStates.FEEDBACK,
        blanks: newBlanks,
        score: clamp(state.score + deltaScore, 0, state.maxPoints),
        lastFeedback: feedback,
        completed: done
      }
    }

    case 'FEEDBACK_DONE': {
      if (state.completed) return { ...state, status: ModalStates.SUMMARY }
      const nextIndex = nextUnsolvedBlank(state.blanks, state.activeBlankIndex)
      return {
        ...state,
        status: ModalStates.FOCUS_BLANK,
        activeBlankIndex: nextIndex,
        guess: '',
        lastFeedback: ''
      }
    }

    case 'USE_HINT': {
      return { ...state, hintText: evt.payload.hintText }
    }

    case 'REVEAL_WORD': {
      const b = state.blanks[state.activeBlankIndex]
      if (!b) return state
      const newBlanks = state.blanks.map(x => {
        if (x.blankIndex !== b.blankIndex) return x
        return { ...x, revealed: true }
      })
      const done = newBlanks.every(x => x.solved || x.revealed)

      return {
        ...state,
        blanks: newBlanks,
        score: clamp(state.score - 10, 0, state.maxPoints),
        status: done ? ModalStates.SUMMARY : ModalStates.FOCUS_BLANK,
        completed: done
      }
    }

    case 'REVEAL_ALL': {
      const newBlanks = state.blanks.map(x => ({ ...x, revealed: true }))
      return {
        ...state,
        blanks: newBlanks,
        score: 0,
        status: ModalStates.SUMMARY,
        completed: true
      }
    }

    case 'NEXT_BLANK': {
      const idx = nextSelectableBlank(state.blanks, state.activeBlankIndex, +1)
      return { ...state, status: ModalStates.FOCUS_BLANK, activeBlankIndex: idx, guess: '', hintText: '' }
    }

    case 'PREV_BLANK': {
      const idx = nextSelectableBlank(state.blanks, state.activeBlankIndex, -1)
      return { ...state, status: ModalStates.FOCUS_BLANK, activeBlankIndex: idx, guess: '', hintText: '' }
    }

    case 'CLOSE': {
      return initialModalState()
    }

    case 'FAIL': {
      return { ...state, status: ModalStates.ERROR, error: evt.payload.message || 'Something went wrong' }
    }

    default:
      return state
  }
}

function nextUnsolvedBlank(blanks, from) {
  if (!blanks.length) return -1
  for (let i = from + 1; i < blanks.length; i += 1) {
    if (!blanks[i].solved && !blanks[i].revealed) return i
  }
  for (let i = 0; i < blanks.length; i += 1) {
    if (!blanks[i].solved && !blanks[i].revealed) return i
  }
  return clamp(from, 0, blanks.length - 1)
}

function nextSelectableBlank(blanks, from, dir) {
  if (!blanks.length) return -1
  let i = from
  for (let step = 0; step < blanks.length; step += 1) {
    i = (i + dir + blanks.length) % blanks.length
    return i
  }
  return from
}

/* ---------------------------
   App wiring
   --------------------------- */

const App = (function () {
  const state = {
    unit: null,
    mode: 'read',
    difficulty: 'standard',
    modal: initialModalState()
  }

  const els = {}

  function cacheEls() {
    els.items = qs('#items')
    els.unitTitle = qs('#unitTitle')
    els.unitDate = qs('#unitDate')
    els.unitSubtitle = qs('#unitSubtitle')

    els.modeRead = qs('#modeRead')
    els.modePractice = qs('#modePractice')
    els.difficultySelect = qs('#difficultySelect')

    els.modalRoot = qs('#modalRoot')
    els.maskedText = qs('#maskedText')
    els.modalTitle = qs('#modalTitle')
    els.modalSub = qs('#modalSub')
    els.modalScore = qs('#modalScore')
    els.blankMeta = qs('#blankMeta')
    els.guessInput = qs('#guessInput')
    els.submitGuess = qs('#submitGuess')
    els.hintBox = qs('#hintBox')
    els.revealWord = qs('#revealWord')
    els.revealAll = qs('#revealAll')
    els.prevBlank = qs('#prevBlank')
    els.nextBlank = qs('#nextBlank')

    els.summary = qs('#summary')
    els.summaryDetail = qs('#summaryDetail')
    els.summaryClose = qs('#summaryClose')
    els.summaryNextItem = qs('#summaryNextItem')
  }

  function setMode(mode) {
    state.mode = mode
    els.modeRead.classList.toggle('active', mode === 'read')
    els.modePractice.classList.toggle('active', mode === 'practice')

    // In practice mode, you could auto-highlight practice buttons
    renderItems()
  }

  function setDifficulty(diff) {
    state.difficulty = diff
  }

  function dispatch(evt) {
    const prev = state.modal
    state.modal = reducer(state.modal, evt)
    renderModal(prev, state.modal)
    runEffects(prev, state.modal, evt)
  }

  function runEffects(prev, next, evt) {
    if (evt.type === 'OPEN') {
      openModalDOM()
      buildPracticeModel(next).then(model => {
        dispatch({ type: 'OPENED_READY', payload: model })
      }).catch(err => {
        dispatch({ type: 'FAIL', payload: { message: String(err && err.message ? err.message : err) } })
      })
      return
    }

    if (evt.type === 'SUBMIT_GUESS') {
      const res = checkGuess(next)
      dispatch({ type: 'GUESS_RESULT', payload: res })

      if (!res.done) {
        window.setTimeout(() => dispatch({ type: 'FEEDBACK_DONE' }), 450)
      }
      return
    }
  }

  function openModalDOM() {
    els.modalRoot.classList.add('open')
    els.modalRoot.setAttribute('aria-hidden', 'false')
    document.body.style.overflow = 'hidden'
  }

  function closeModalDOM() {
    els.modalRoot.classList.remove('open')
    els.modalRoot.setAttribute('aria-hidden', 'true')
    document.body.style.overflow = ''
  }

  async function loadUnit() {
    const unitPath = getParam('unit')
    const fallback = 'assets/data/units/news/yyyy/2026/02/25.json'
    const path = unitPath || fallback

    const res = await fetch(path, { cache: 'no-store' })
    if (!res.ok) throw new Error(`Failed to load unit: ${path}`)
    const unit = await res.json()

    state.unit = unit
    renderUnitHeader()
    renderItems()
  }

  function renderUnitHeader() {
    const u = state.unit
    els.unitTitle.textContent = u.title || 'News'
    els.unitDate.textContent = u.date || nowISODate()
    els.unitSubtitle.textContent = `${(u.items || []).length} items`
  }

  function renderItems() {
    const u = state.unit
    const items = u.items || []
    const html = items.map((it, idx) => {
      const anchor = `item-${idx + 1}`
      const title = it.title ? escapeHTML(it.title) : `Item ${idx + 1}`
      const text = escapeHTML(it.text || '')

      const completed = readCompletion(u.unit_id, it.item_id, state.difficulty)
      const completedText = completed ? `Completed (${completed.score})` : 'Practice'

      const btnLabel = state.mode === 'practice' ? 'Practice now' : completedText
      const hint = estimateBlanksHint(it, state.difficulty)

      return `
        <article class='item' id='${anchor}' data-item-index='${idx}'>
          <h2>${title}</h2>
          <p>${text}</p>
          <div class='item-footer'>
            <div>${hint}</div>
            <div class='item-actions'>
              <button class='pill' type='button' data-action='practice' data-item-index='${idx}'>${btnLabel}</button>
            </div>
          </div>
        </article>
      `
    }).join('')

    els.items.innerHTML = html
  }

  function estimateBlanksHint(item, difficulty) {
    const cfg = item.practice || {}
    const targets = cfg?.blanking?.targets || {}
    const t = targets[difficulty] || targets.standard
    if (!t) return ''
    return `${t.min_blanks}-${t.max_blanks} blanks`
  }

  function onPageClick(e) {
    const t = e.target
    const action = t && t.getAttribute ? t.getAttribute('data-action') : null
    if (action === 'practice') {
      const itemIndex = Number(t.getAttribute('data-item-index'))
      openPracticeForItem(itemIndex)
    }
  }

  function openPracticeForItem(itemIndex) {
    const u = state.unit
    const items = u.items || []
    const it = items[itemIndex]
    if (!it) return

    const returnTo = { hash: `#item-${itemIndex + 1}`, scrollY: window.scrollY }

    dispatch({
      type: 'OPEN',
      payload: { unit: u, itemIndex, difficulty: state.difficulty, returnTo }
    })
  }

  async function buildPracticeModel(modalState) {
    const u = modalState.unit
    const it = u.items[modalState.itemIndex]
    const practiceCfg = it.practice || u.practice || {}

    // Use authored variant if you want later
    // For now, always auto-generate
    const { tokens, blanks } = chooseBlankTargets(it.text || '', modalState.difficulty, practiceCfg)

    return { tokens, blanks }
  }

  function checkGuess(modalState) {
    const b = modalState.blanks[modalState.activeBlankIndex]
    if (!b) {
      return { correct: false, newBlanks: modalState.blanks, deltaScore: 0, feedback: 'Select a blank first', done: false }
    }

    const guess = String(modalState.guess || '').trim()
    if (!guess) {
      return { correct: false, newBlanks: modalState.blanks, deltaScore: 0, feedback: 'Type a guess', done: false }
    }

    const correct = slugKey(guess) === slugKey(b.answer)

    let deltaScore = 0
    let feedback = ''

    const newBlanks = modalState.blanks.map(x => {
      if (x.blankIndex !== b.blankIndex) return x
      if (x.solved || x.revealed) return x

      if (correct) {
        feedback = 'Correct'
        // Simple scoring: divide points across blanks
        const per = Math.floor(modalState.maxPoints / Math.max(1, modalState.blanks.length))
        deltaScore = per
        return { ...x, solved: true }
      } else {
        feedback = 'Not quite'
        deltaScore = -1
        return x
      }
    })

    const done = newBlanks.every(x => x.solved || x.revealed)
    return { correct, newBlanks, deltaScore, feedback, done }
  }

  function renderModal(prev, next) {
    if (next.status === ModalStates.CLOSED) {
      closeModalDOM()
      return
    }

    // Top text
    const u = next.unit
    const it = u && u.items ? u.items[next.itemIndex] : null
    const itemTitle = it && it.title ? it.title : `Item ${next.itemIndex + 1}`

    els.modalTitle.textContent = `Practice: ${itemTitle}`
    els.modalSub.textContent = `${next.itemIndex + 1} / ${(u && u.items ? u.items.length : 0)} • ${next.difficulty}`

    els.modalScore.textContent = `${next.score} / ${next.maxPoints}`

    // Summary visibility
    const showSummary = next.status === ModalStates.SUMMARY
    els.summary.classList.toggle('hidden', !showSummary)

    if (showSummary) {
      els.summaryDetail.textContent = `Score: ${next.score} / ${next.maxPoints}`
    }

    // Main masked text
    const html = renderMaskedHTML(next.tokens, next.blanks, next.activeBlankIndex)
    els.maskedText.innerHTML = html

    // Blank meta
    const b = next.blanks[next.activeBlankIndex]
    if (!b) {
      els.blankMeta.textContent = 'Select a blank'
    } else {
      const status = b.solved ? 'solved' : (b.revealed ? 'revealed' : 'unsolved')
      els.blankMeta.textContent = `Blank ${b.blankIndex + 1} of ${next.blanks.length} • ${status} • ${b.answer.length} letters`
    }

    // Hint box and feedback
    els.hintBox.textContent = next.hintText || next.lastFeedback || ''

    // Input enabling
    const disableInput = showSummary || next.status === ModalStates.ERROR
    els.guessInput.disabled = disableInput
    els.submitGuess.disabled = disableInput

    if (!disableInput && prev.status !== next.status) {
      // Focus input when entering focus state
      if (next.status === ModalStates.FOCUS_BLANK || next.status === ModalStates.READY) {
        window.setTimeout(() => els.guessInput.focus(), 0)
      }
    }
  }

  function onModalClick(e) {
    const t = e.target
    const action = t && t.getAttribute ? t.getAttribute('data-action') : null
    if (action === 'close') {
      const returnTo = state.modal.returnTo
      dispatch({ type: 'CLOSE' })
      restoreReturnTo(returnTo)
      return
    }

    const hintLayer = t && t.getAttribute ? t.getAttribute('data-hint') : null
    if (hintLayer) {
      const hintText = getHintText(state.modal, hintLayer)
      dispatch({ type: 'USE_HINT', payload: { hintText } })
      return
    }

    // Blank click
    if (t && t.classList && t.classList.contains('blank')) {
      const idx = Number(t.getAttribute('data-blank-index'))
      dispatch({ type: 'SELECT_BLANK', payload: { blankIndex: idx } })
      return
    }
  }

  function getHintText(modalState, layer) {
    const u = modalState.unit
    const it = u.items[modalState.itemIndex]
    const b = modalState.blanks[modalState.activeBlankIndex]
    if (!b) return 'Select a blank'

    // Placeholder hint logic
    // Later: use authored hints or LLM-cached hints
    if (layer === 'direct') return `Definition-style hint for '${b.answer}'`
    if (layer === 'intermediate') return `Context hint: look at the sentence around the blank`
    return `Indirect hint: think of a related concept or synonym`
  }

  function restoreReturnTo(returnTo) {
    if (!returnTo) return
    // restore scroll and anchor
    window.setTimeout(() => {
      if (returnTo.hash) {
        const el = qs(returnTo.hash)
        if (el) el.scrollIntoView({ block: 'start' })
      } else {
        window.scrollTo(0, returnTo.scrollY || 0)
      }
    }, 0)
  }

  function keyHandler(e) {
    if (!state.modal || state.modal.status === ModalStates.CLOSED) return

    if (e.key === 'Escape') {
      const returnTo = state.modal.returnTo
      dispatch({ type: 'CLOSE' })
      restoreReturnTo(returnTo)
      return
    }

    if (e.key === 'Enter') {
      if (!els.guessInput.disabled) {
        dispatch({ type: 'SUBMIT_GUESS' })
      }
    }
  }

  function wireUI() {
    els.modeRead.addEventListener('click', () => setMode('read'))
    els.modePractice.addEventListener('click', () => setMode('practice'))

    els.difficultySelect.addEventListener('change', () => setDifficulty(els.difficultySelect.value))

    document.addEventListener('click', onPageClick)

    els.modalRoot.addEventListener('click', onModalClick)

    els.guessInput.addEventListener('input', () => {
      dispatch({ type: 'INPUT_CHANGE', payload: { value: els.guessInput.value } })
    })
    els.submitGuess.addEventListener('click', () => dispatch({ type: 'SUBMIT_GUESS' }))

    els.revealWord.addEventListener('click', () => dispatch({ type: 'REVEAL_WORD' }))
    els.revealAll.addEventListener('click', () => dispatch({ type: 'REVEAL_ALL' }))
    els.prevBlank.addEventListener('click', () => dispatch({ type: 'PREV_BLANK' }))
    els.nextBlank.addEventListener('click', () => dispatch({ type: 'NEXT_BLANK' }))

    els.summaryClose.addEventListener('click', () => {
      // mark completion
      persistCompletionFromModal(state.modal)
      const returnTo = state.modal.returnTo
      dispatch({ type: 'CLOSE' })
      renderItems()
      restoreReturnTo(returnTo)
    })

    els.summaryNextItem.addEventListener('click', () => {
      persistCompletionFromModal(state.modal)
      const nextIndex = state.modal.itemIndex + 1
      const u = state.modal.unit
      if (!u || nextIndex >= (u.items || []).length) return
      // reopen without closing the modal root
      dispatch({
        type: 'OPEN',
        payload: {
          unit: u,
          itemIndex: nextIndex,
          difficulty: state.difficulty,
          returnTo: { hash: `#item-${nextIndex + 1}`, scrollY: window.scrollY }
        }
      })
      renderItems()
    })

    window.addEventListener('keydown', keyHandler)
  }

  function persistCompletionFromModal(modalState) {
    if (!modalState.completed) return
    const u = modalState.unit
    const it = u.items[modalState.itemIndex]
    if (!u || !it) return
    writeCompletion(u.unit_id, it.item_id, modalState.difficulty, {
      score: modalState.score,
      completed_at: new Date().toISOString()
    })
  }

  function completionKey(unitId, itemId, difficulty) {
    return `cluechain:progress:${unitId}:${itemId}:${difficulty}`
  }

  function readCompletion(unitId, itemId, difficulty) {
    try {
      const raw = localStorage.getItem(completionKey(unitId, itemId, difficulty))
      if (!raw) return null
      return JSON.parse(raw)
    } catch (e) {
      return null
    }
  }

  function writeCompletion(unitId, itemId, difficulty, obj) {
    try {
      localStorage.setItem(completionKey(unitId, itemId, difficulty), JSON.stringify(obj))
    } catch (e) {
      // ignore
    }
  }

  async function init() {
    cacheEls()
    wireUI()
    await loadUnit()
  }

  return { init }
})()

window.addEventListener('DOMContentLoaded', () => {
  App.init().catch(err => {
    console.error(err)
  })
})
```

---

## 5) JSON example for a news unit

Save as:

`assets/data/units/news/yyyy/2026/02/25.json`

```json
{
  "schema_version": 1,
  "unit_id": "news-2026-02-25",
  "unit_type": "news",
  "title": "Today's News",
  "date": "2026-02-25",
  "items": [
    {
      "item_id": "news-2026-02-25-01",
      "title": "Federal Reserve Signals Rate Pause",
      "text": "The Federal Reserve indicated it may pause interest rate hikes while watching inflation data and labor market signals.",
      "practice": {
        "blanking": {
          "targets": {
            "easy": { "min_blanks": 3, "max_blanks": 5 },
            "standard": { "min_blanks": 5, "max_blanks": 7 },
            "advanced": { "min_blanks": 7, "max_blanks": 10 }
          },
          "avoid": { "stopwords": true, "numbers": true, "very_short_words_max_len": 3 }
        }
      }
    },
    {
      "item_id": "news-2026-02-25-02",
      "title": "Major Earthquake in Chile",
      "text": "A strong earthquake struck central Chile, prompting emergency assessments and early tsunami monitoring along the coast.",
      "practice": {
        "blanking": {
          "targets": {
            "easy": { "min_blanks": 3, "max_blanks": 5 },
            "standard": { "min_blanks": 5, "max_blanks": 7 },
            "advanced": { "min_blanks": 7, "max_blanks": 10 }
          },
          "avoid": { "stopwords": true, "numbers": true, "very_short_words_max_len": 3 }
        }
      }
    }
  ]
}
```

---

## What you can extend next

* Replace the placeholder hint text with authored hints or cached LLM hints
* Add “All items” mode inside the modal (practice sequentially without closing)
* Add better blank selection (avoid masking proper nouns on Easy, prefer them on Advanced)
* Add per-blank point decay (wrong guesses reduce max points for that blank)


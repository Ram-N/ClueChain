'use strict'

import { ClueChainEngine, nextUnsolvedBlank } from '../js/engine/cluechain-engine.js'

// ---- Letter-selection modal (self-contained, mirrors ui-manager.js logic) ----

const VOWELS = ['a','e','i','o','u']

const LetterPicker = {
  _vowel: '',
  _consonants: [],
  _onConfirm: null,
  _onClose: null,

  open(onConfirm, onClose) {
    this._vowel = ''
    this._consonants = []
    this._onConfirm = onConfirm
    this._onClose = onClose
    this._resetTiles()
    this._wireTiles()
    this._wireButtons()
    this._applyPhaseStyles()
    const modal = document.getElementById('letter-selection-modal')
    if (modal) { modal.classList.remove('closing'); modal.classList.add('show') }
  },

  close() {
    const modal = document.getElementById('letter-selection-modal')
    if (modal) modal.classList.remove('show', 'closing')
  },

  _resetTiles() {
    document.querySelectorAll('#ls-modal-letter-grid .letter-tile').forEach(t => {
      t.classList.remove('ls-vowel-selected','ls-consonant-selected',
                         'vowel-enabled','consonant-enabled','phase-disabled')
    })
    this._setSlot('ls-slot-vowel', null, 'vowel')
    this._setSlot('ls-slot-c1', null, 'consonant', 1)
    this._setSlot('ls-slot-c2', null, 'consonant', 2)
    const btn = document.getElementById('ls-confirm-btn')
    if (btn) btn.disabled = true
  },

  _setSlot(id, letter, type, n) {
    const el = document.getElementById(id)
    if (!el) return
    if (letter) {
      el.textContent = letter.toUpperCase()
      el.className = `ls-slot ls-slot-${type} filled-${type}`
    } else {
      el.innerHTML = type === 'vowel' ? 'Vowel' : `Consonant<br>${n}`
      el.className = `ls-slot ls-slot-${type}`
    }
  },

  _updateSlots() {
    this._setSlot('ls-slot-vowel', this._vowel, 'vowel')
    this._setSlot('ls-slot-c1', this._consonants[0] || null, 'consonant', 1)
    this._setSlot('ls-slot-c2', this._consonants[1] || null, 'consonant', 2)
  },

  _wireTiles() {
    document.querySelectorAll('#ls-modal-letter-grid .letter-tile').forEach(tile => {
      const letter = tile.getAttribute('data-letter')
      const isVowel = VOWELS.includes(letter)
      const fresh = tile.cloneNode(true)
      tile.parentNode.replaceChild(fresh, tile)
      fresh.addEventListener('click', () => this._onTileClick(fresh, letter, isVowel))
    })
  },

  _wireButtons() {
    const confirmBtn = document.getElementById('ls-confirm-btn')
    if (confirmBtn) {
      const fresh = confirmBtn.cloneNode(true)
      confirmBtn.parentNode.replaceChild(fresh, confirmBtn)
      fresh.disabled = true
      fresh.addEventListener('click', () => this._confirm())
    }
    const closeBtn = document.getElementById('ls-modal-close')
    if (closeBtn) {
      const fresh = closeBtn.cloneNode(true)
      closeBtn.parentNode.replaceChild(fresh, closeBtn)
      fresh.addEventListener('click', () => { this.close(); if (this._onClose) this._onClose() })
    }
  },

  _onTileClick(tile, letter, isVowel) {
    if (isVowel) {
      if (this._vowel) {
        document.querySelector(`#ls-modal-letter-grid .letter-tile[data-letter="${this._vowel}"]`)
          ?.classList.remove('ls-vowel-selected')
      }
      this._vowel = letter
      tile.classList.add('ls-vowel-selected')
    } else {
      if (this._consonants.includes(letter)) {
        this._consonants = this._consonants.filter(c => c !== letter)
        tile.classList.remove('ls-consonant-selected')
      } else if (this._consonants.length >= 2) {
        // Simple toast-style feedback inline
        const btn = document.getElementById('ls-confirm-btn')
        const orig = btn ? btn.textContent : ''
        if (btn) { btn.textContent = 'Deselect one first'; setTimeout(() => { btn.textContent = orig }, 1500) }
        return
      } else {
        this._consonants.push(letter)
        tile.classList.add('ls-consonant-selected')
      }
    }
    this._updateSlots()
    this._applyPhaseStyles()
    const btn = document.getElementById('ls-confirm-btn')
    if (btn) btn.disabled = !(this._vowel && this._consonants.length === 2)
  },

  _applyPhaseStyles() {
    const vowelChosen = !!this._vowel
    document.querySelectorAll('#ls-modal-letter-grid .letter-tile').forEach(t => {
      const letter = t.getAttribute('data-letter')
      const isVowel = VOWELS.includes(letter)
      t.classList.remove('vowel-enabled','consonant-enabled','phase-disabled')
      t.style.background = ''
      t.style.borderColor = ''
      t.style.color = ''
      t.style.opacity = ''
      t.style.fontWeight = ''
      if (!vowelChosen) {
        t.classList.add(isVowel ? 'vowel-enabled' : 'phase-disabled')
      } else {
        if (isVowel) {
          t.classList.add('vowel-enabled')
        } else if (!t.classList.contains('ls-consonant-selected')) {
          t.classList.add('consonant-enabled')
          // Force styles directly — overrides any cached/conflicting stylesheet
          t.style.background = '#a5d6a7'
          t.style.borderColor = '#2e7d32'
          t.style.color = '#1b5e20'
          t.style.opacity = '1'
          t.style.fontWeight = 'bold'
        }
      }
    })
  },

  _confirm() {
    if (!this._vowel || this._consonants.length !== 2) return
    const vowel = this._vowel
    const consonants = [...this._consonants]
    const modal = document.getElementById('letter-selection-modal')
    if (modal) {
      modal.classList.add('closing')
      setTimeout(() => {
        modal.classList.remove('show','closing')
        if (this._onConfirm) this._onConfirm(vowel, consonants)
      }, 350)
    } else {
      if (this._onConfirm) this._onConfirm(vowel, consonants)
    }
  }
}

// ---- Utilities ----

function qs(sel, root) {
  return (root || document).querySelector(sel)
}

function getParam(name) {
  return new URL(window.location.href).searchParams.get(name)
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n))
}

function slugKey(s) {
  return String(s || '').trim().toLowerCase()
}

function nowISODate() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function escapeHTML(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

// ---- Blanking engine (STOPWORDS, tokenizeWithSpans, chooseBlankTargets imported from engine) ----

// seededLetters: Set of lowercase letters to reveal within dashes
function renderMaskedHTML(tokens, blanks, activeBlankIndex, seededLetters) {
  const blankByTok = new Map()
  for (const b of blanks) blankByTok.set(b.tokIndex, b)

  const parts = []
  for (let i = 0; i < tokens.length; i++) {
    const tok = tokens[i]
    const b = blankByTok.get(i)
    if (!b) {
      parts.push(escapeHTML(tok.t))
      continue
    }

    const isActive = b.blankIndex === activeBlankIndex
    let shown, cls
    if (b.solved || b.revealed) {
      shown = escapeHTML(b.answer)
      cls = b.solved ? 'blank solved' : 'blank revealed'
    } else {
      // Build dashes, revealing seeded letters in their correct positions
      const chars = Array.from(b.answer.toLowerCase())
      const dashParts = chars.map(ch => {
        if (seededLetters && seededLetters.has(ch)) {
          return `<span class='seeded-letter'>${escapeHTML(ch.toUpperCase())}</span>`
        }
        return '–'
      })
      shown = dashParts.join('<span class="dash-gap"></span>') +
              `&thinsp;<span class='blank-count'>(${b.answer.length})</span>`
      cls = isActive ? 'blank active' : 'blank'
    }

    parts.push(
      `<span class='${cls}' data-blank-index='${b.blankIndex}' role='button' tabindex='0'>${shown}</span>`
    )
  }

  return parts.join('')
}

// ---- Modal state machine ----

const S = {
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
    status: S.CLOSED,
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
    error: '',
    seededLetters: null,   // Set of letters revealed via picker
    _pendingModel: null    // Built model waiting for letter selection
  }
}

function reducer(state, evt) {
  switch (evt.type) {
    case 'OPEN':
      return {
        ...state,
        status: S.OPENING,
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

    case 'OPENED_READY':
      // Store the model and wait for letter selection before going to READY
      return {
        ...state,
        status: S.OPENING,   // stay in OPENING until letters are picked
        _pendingModel: evt.payload
      }

    case 'LETTERS_CONFIRMED': {
      const model = state._pendingModel || {}
      return {
        ...state,
        status: S.READY,
        tokens: model.tokens || [],
        blanks: model.blanks || [],
        activeBlankIndex: (model.blanks || []).length ? 0 : -1,
        _engine: model._engine || null,
        seededLetters: evt.payload.seededLetters,
        _pendingModel: null
      }
    }

    case 'LETTERS_DISMISSED':
      // Player closed the picker without selecting — close the whole modal
      return initialModalState()

    case 'SELECT_BLANK':
      if (state.status === S.SUMMARY || state.status === S.ERROR) return state
      return {
        ...state,
        status: S.FOCUS_BLANK,
        activeBlankIndex: evt.payload.blankIndex,
        guess: '',
        lastFeedback: '',
        hintText: ''
      }

    case 'INPUT_CHANGE':
      return { ...state, guess: evt.payload.value }

    case 'SUBMIT_GUESS':
      if (state.activeBlankIndex < 0) return state
      return { ...state, status: S.CHECKING, lastFeedback: '' }

    case 'GUESS_RESULT': {
      const { newBlanks, deltaScore, feedback } = evt.payload
      const done = newBlanks.every(b => b.solved || b.revealed)
      return {
        ...state,
        status: done ? S.SUMMARY : S.FEEDBACK,
        blanks: newBlanks,
        score: clamp(state.score + deltaScore, 0, state.maxPoints),
        lastFeedback: feedback,
        completed: done
      }
    }

    case 'FEEDBACK_DONE': {
      if (state.completed) return { ...state, status: S.SUMMARY }
      const nextIndex = nextUnsolvedBlank(state.blanks, state.activeBlankIndex)
      return {
        ...state,
        status: S.FOCUS_BLANK,
        activeBlankIndex: nextIndex,
        guess: '',
        lastFeedback: ''
      }
    }

    case 'USE_HINT':
      return { ...state, hintText: evt.payload.hintText }

    case 'REVEAL_WORD': {
      const b = state.blanks[state.activeBlankIndex]
      if (!b || b.solved || b.revealed) return state
      const newBlanks = state.blanks.map(x =>
        x.blankIndex === b.blankIndex ? { ...x, revealed: true } : x
      )
      const done = newBlanks.every(x => x.solved || x.revealed)
      return {
        ...state,
        blanks: newBlanks,
        score: clamp(state.score - 10, 0, state.maxPoints),
        status: done ? S.SUMMARY : S.FOCUS_BLANK,
        completed: done
      }
    }

    case 'REVEAL_ALL': {
      const newBlanks = state.blanks.map(x => ({ ...x, revealed: true }))
      return { ...state, blanks: newBlanks, score: 0, status: S.SUMMARY, completed: true }
    }

    case 'NEXT_BLANK': {
      // Fix from plan: simplified, no misleading loop
      if (!state.blanks.length) return state
      const idx = (state.activeBlankIndex + 1 + state.blanks.length) % state.blanks.length
      return { ...state, status: S.FOCUS_BLANK, activeBlankIndex: idx, guess: '', hintText: '' }
    }

    case 'PREV_BLANK': {
      // Fix from plan: simplified, no misleading loop
      if (!state.blanks.length) return state
      const idx = (state.activeBlankIndex - 1 + state.blanks.length) % state.blanks.length
      return { ...state, status: S.FOCUS_BLANK, activeBlankIndex: idx, guess: '', hintText: '' }
    }

    case 'CLOSE':
      return initialModalState()

    case 'FAIL':
      return { ...state, status: S.ERROR, error: evt.payload.message || 'Something went wrong' }

    default:
      return state
  }
}

// nextUnsolvedBlank imported from engine

// ---- Hint logic ----

function getHintText(modalState, layer) {
  // Delegate to engine when available
  if (modalState._engine) {
    modalState._engine.selectBlank(modalState.activeBlankIndex)
    return modalState._engine.useHint(layer)
  }

  const b = modalState.blanks[modalState.activeBlankIndex]
  if (!b) return 'Select a blank first'
  if (b.solved || b.revealed) return `The word was: ${b.answer}`

  if (b.hints && b.hints[layer]) return `${b.hints[layer]} (${b.answer.length})`

  switch (layer) {
    case 'direct':       return `Definition: look for a ${b.answer.length}-letter word that fits this context.`
    case 'intermediate': return `Context clue: read the surrounding sentence for a hint about this word.`
    case 'indirect':     return `Indirect: think of a synonym or related concept for this position in the text.`
    default:             return `Hint for '${b.answer}'.`
  }
}

// ---- Completion persistence (localStorage) ----

function completionKey(unitId, itemId, difficulty) {
  return `cluechain:progress:${unitId}:${itemId}:${difficulty}`
}

function readCompletion(unitId, itemId, difficulty) {
  try {
    const raw = localStorage.getItem(completionKey(unitId, itemId, difficulty))
    return raw ? JSON.parse(raw) : null
  } catch (_) {
    return null
  }
}

function writeCompletion(unitId, itemId, difficulty, obj) {
  try {
    localStorage.setItem(completionKey(unitId, itemId, difficulty), JSON.stringify(obj))
  } catch (_) {
    // localStorage may be unavailable (private mode, etc.)
  }
}

// ---- App ----

const App = (function () {
  const state = {
    unit: null,
    mode: 'read',
    difficulty: 'standard',
    lbMode: 'all',   // 'all' or 'word'
    modal: initialModalState()
  }

  const els = {}

  function cacheEls() {
    els.items            = qs('#items')
    els.unitTitle        = qs('#unitTitle')
    els.unitDate         = qs('#unitDate')
    els.unitSubtitle     = qs('#unitSubtitle')
    els.modeRead         = qs('#modeRead')
    els.modePractice     = qs('#modePractice')
    els.difficultySelect = qs('#difficultySelect')
    els.modalRoot        = qs('#modalRoot')
    els.maskedText       = qs('#maskedText')
    els.modalTitle       = qs('#modalTitle')
    els.modalSub         = qs('#modalSub')
    els.modalScore       = qs('#modalScore')
    els.blankMeta        = qs('#blankMeta')
    els.guessInput       = qs('#guessInput')
    els.submitGuess      = qs('#submitGuess')
    els.hintBox          = qs('#hintBox')
    els.feedbackPanel    = qs('#feedbackPanel')
    els.revealWord       = qs('#revealWord')
    els.revealAll        = qs('#revealAll')
    els.prevBlank        = qs('#prevBlank')
    els.nextBlank        = qs('#nextBlank')
    els.summary          = qs('#summary')
    els.summaryDetail    = qs('#summaryDetail')
    els.summaryClose     = qs('#summaryClose')
    els.summaryNextItem  = qs('#summaryNextItem')
    els.letterBoard      = qs('#letterBoard')
    els.lbModeAll        = qs('#lbModeAll')
    els.lbModeWord       = qs('#lbModeWord')
  }

  // ---- Mode & difficulty ----

  function setMode(mode) {
    state.mode = mode
    els.modeRead.classList.toggle('active', mode === 'read')
    els.modePractice.classList.toggle('active', mode === 'practice')
    renderItems()
  }

  function setDifficulty(diff) {
    state.difficulty = diff
  }

  // ---- Dispatch / reducer ----

  function dispatch(evt) {
    const prev = state.modal
    state.modal = reducer(state.modal, evt)
    renderModal(prev, state.modal)
    runEffects(prev, state.modal, evt)
  }

  function runEffects(prev, next, evt) {
    if (evt.type === 'OPEN') {
      openModalDOM()
      buildPracticeModel(next)
        .then(model => dispatch({ type: 'OPENED_READY', payload: model }))
        .catch(err => dispatch({ type: 'FAIL', payload: { message: String(err?.message ?? err) } }))
      return
    }

    if (evt.type === 'OPENED_READY') {
      // Show letter picker; on confirm transition to READY, on close dismiss entirely
      LetterPicker.open(
        (vowel, consonants) => {
          const seededLetters = new Set([vowel, ...consonants])
          dispatch({ type: 'LETTERS_CONFIRMED', payload: { seededLetters } })
        },
        () => {
          dispatch({ type: 'LETTERS_DISMISSED' })
          closeModalDOM()
        }
      )
      return
    }

    if (evt.type === 'LETTERS_DISMISSED') {
      closeModalDOM()
      return
    }

    // Auto-show indirect clue whenever a blank becomes active
    if (evt.type === 'OPENED_READY' || evt.type === 'LETTERS_CONFIRMED' || evt.type === 'SELECT_BLANK' || evt.type === 'FEEDBACK_DONE' || evt.type === 'NEXT_BLANK' || evt.type === 'PREV_BLANK') {
      if (next.activeBlankIndex >= 0) {
        const hintText = getHintText(next, 'indirect')
        dispatch({ type: 'USE_HINT', payload: { hintText } })
      }
      return
    }

    if (evt.type === 'SUBMIT_GUESS') {
      const res = checkGuess(next)
      dispatch({ type: 'GUESS_RESULT', payload: res })
      // If correct and "This word" mode is active, switch back to "All"
      if (res.newBlanks && state.lbMode === 'word') {
        const wasCorrect = /correct/i.test(res.feedback)
        if (wasCorrect) setLbMode('all')
      }
      if (!res.done) {
        window.setTimeout(() => dispatch({ type: 'FEEDBACK_DONE' }), 500)
      }
      return
    }

    // Keep engine in sync for reveal actions
    if (evt.type === 'REVEAL_WORD' && next._engine) {
      next._engine.selectBlank(prev.activeBlankIndex)
      next._engine.revealWord(prev.activeBlankIndex)
      return
    }

    if (evt.type === 'REVEAL_ALL' && next._engine) {
      next._engine.revealAll()
      return
    }
  }

  // ---- Modal DOM open/close ----

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

  // ---- Load unit from URL param ----

  async function loadUnit(unitPath) {
    if (!unitPath) throw new Error('Set data-manifest-path on <body> or pass ?unit= in URL.')
    const res = await fetch(unitPath, { cache: 'no-store' })
    if (!res.ok) throw new Error(`Failed to load unit: ${unitPath} (HTTP ${res.status})`)
    state.unit = await res.json()
    renderUnitHeader()
    renderItems()
  }

  // ---- Load pack manifest and render listing ----

  async function loadListing() {
    const manifestPath = document.body.dataset.manifestPath
    if (!manifestPath) throw new Error('Set data-manifest-path on <body>.')
    const res = await fetch('../' + manifestPath, { cache: 'no-store' })
    if (!res.ok) throw new Error(`Failed to load manifest: ${manifestPath}`)
    const manifest = await res.json()
    renderListing(manifest)
  }

  function renderListing(manifest) {
    els.unitTitle.textContent = manifest.title || ''
    els.unitSubtitle.textContent = `${manifest.units.length} unit${manifest.units.length === 1 ? '' : 's'}`
    els.unitDate.textContent = ''
    const html = manifest.units.map(u => `
      <article class='item'>
        <h2>${escapeHTML(u.title)}</h2>
        <div class='item-footer'>
          <div>${escapeHTML(u.date || '')} &bull; ${u.item_count || '?'} items</div>
          <div class='item-actions'>
            <a class='pill' href='?unit=../${escapeHTML(u.path)}'>Open &rarr;</a>
          </div>
        </div>
      </article>
    `).join('')
    els.items.innerHTML = html
  }

  // ---- Page rendering ----

  function renderUnitHeader() {
    const u = state.unit
    els.unitTitle.textContent = u.title || 'News'
    els.unitDate.textContent = u.date || nowISODate()
    els.unitSubtitle.textContent = `${(u.items || []).length} items`
  }

  function renderItems() {
    if (!state.unit) return
    const u = state.unit
    const html = (u.items || []).map((it, idx) => {
      const anchor = `item-${idx + 1}`
      const title = it.title ? escapeHTML(it.title) : `Item ${idx + 1}`
      const text = escapeHTML(it.text || '')
      const completed = readCompletion(u.unit_id, it.item_id, state.difficulty)

      let btnLabel, btnClass
      if (completed) {
        btnLabel = `&#10003; Completed (${completed.score})`
        btnClass = 'pill completed'
      } else if (state.mode === 'practice') {
        btnLabel = 'Practice now'
        btnClass = 'pill'
      } else {
        btnLabel = 'Practice'
        btnClass = 'pill'
      }

      const hint = estimateBlanksHint(it, state.difficulty)

      return `
        <article class='item' id='${anchor}' data-item-index='${idx}'>
          <h2>${title}</h2>
          <p>${text}</p>
          <div class='item-footer'>
            <div>${hint}</div>
            <div class='item-actions'>
              <button class='${btnClass}' type='button' data-action='practice' data-item-index='${idx}'>${btnLabel}</button>
            </div>
          </div>
        </article>
      `
    }).join('')

    els.items.innerHTML = html
  }

  function estimateBlanksHint(item, difficulty) {
    const targets = item.practice?.blanking?.targets || {}
    const t = targets[difficulty] || targets.standard
    if (!t) return ''
    return `${t.min_blanks}&ndash;${t.max_blanks} blanks`
  }

  // ---- Page-level click handler ----
  // Only handles Practice button clicks; ignores everything else
  function onPageClick(e) {
    const t = e.target
    if (!t || !t.getAttribute) return
    if (t.getAttribute('data-action') === 'practice') {
      const itemIndex = Number(t.getAttribute('data-item-index'))
      openPracticeForItem(itemIndex)
    }
  }

  function openPracticeForItem(itemIndex) {
    const items = state.unit?.items || []
    if (!items[itemIndex]) return
    dispatch({
      type: 'OPEN',
      payload: {
        unit: state.unit,
        itemIndex,
        difficulty: state.difficulty,
        returnTo: { hash: `#item-${itemIndex + 1}`, scrollY: window.scrollY }
      }
    })
  }

  // ---- Build practice model via ClueChainEngine ----

  async function buildPracticeModel(modalState) {
    const it = modalState.unit.items[modalState.itemIndex]
    const practiceCfg = it.practice || modalState.unit.practice || {}

    const engine = new ClueChainEngine(it, {
      mode: 'learning',
      practiceCfg,
      difficulty: modalState.difficulty
    })
    engine.init()

    const engineState = engine.getState()
    // Convert normalised engine items back to the blanks[] shape the reducer/renderer expects
    const blanks = engineState.items.map((item, k) => ({
      blankIndex: k,
      tokIndex: item.tokIndex,
      answer: item.word,
      hints: {
        direct:       item.clues.find(c => c.type === 'direct')?.text || '',
        intermediate: item.clues.find(c => c.type === 'intermediate')?.text || '',
        indirect:     item.clues.find(c => c.type === 'indirect')?.text || '',
      },
      solved: false,
      revealed: false,
      usedHints: { direct: false, intermediate: false, indirect: false }
    }))

    return { tokens: engineState.tokens, blanks, _engine: engine }
  }

  // ---- Guess checking (delegates to engine) ----

  function checkGuess(modalState) {
    const b = modalState.blanks[modalState.activeBlankIndex]
    if (!b) return { newBlanks: modalState.blanks, deltaScore: 0, feedback: 'Select a blank first', done: false }

    const guess = String(modalState.guess || '').trim()
    if (!guess) return { newBlanks: modalState.blanks, deltaScore: 0, feedback: 'Type a guess', done: false }

    // Delegate to engine if available
    if (modalState._engine) {
      const engine = modalState._engine

      // Feature 5: check all unsolved blanks, not just the active one
      let matchedBlankIndex = -1
      for (let i = 0; i < modalState.blanks.length; i++) {
        const bx = modalState.blanks[i]
        if (!bx.solved && !bx.revealed && slugKey(guess) === slugKey(bx.answer)) {
          matchedBlankIndex = i
          break
        }
      }

      engine.selectBlank(matchedBlankIndex >= 0 ? matchedBlankIndex : modalState.activeBlankIndex)
      const result = engine.submitGuess(guess)

      const engineState = engine.getState()
      const newBlanks = modalState.blanks.map((x, idx) => ({
        ...x,
        solved: engineState.items[idx]?.solved || x.solved,
        revealed: engineState.items[idx]?.revealed || x.revealed,
      }))

      // Prefix feedback with the guess text
      const label = guess.toUpperCase()
      const feedbackWithGuess = result.correct
        ? `"${label}" — Correct!`
        : `"${label}" — Not quite, try again`

      return { newBlanks, deltaScore: result.deltaScore, feedback: feedbackWithGuess, done: result.done }
    }

    // Fallback (no engine — should not happen in normal flow)
    const correct = slugKey(guess) === slugKey(b.answer)
    let deltaScore = 0
    let feedback = ''
    const label = guess.toUpperCase()
    const newBlanks = modalState.blanks.map(x => {
      if (x.blankIndex !== b.blankIndex || x.solved || x.revealed) return x
      if (correct) {
        const perBlank = Math.floor(modalState.maxPoints / Math.max(1, modalState.blanks.length))
        deltaScore = perBlank
        feedback = `"${label}" — Correct!`
        return { ...x, solved: true }
      } else {
        deltaScore = -1
        feedback = `"${label}" — Not quite, try again`
        return x
      }
    })
    const done = newBlanks.every(x => x.solved || x.revealed)
    return { newBlanks, deltaScore, feedback, done }
  }

  // ---- Feedback notification log ----
  // Appends cards persistently; only cleared when a new practice session opens.

  function showFeedback(feedback) {
    if (!els.feedbackPanel || !feedback) return
    const isCorrect = /correct|well done|great/i.test(feedback)
    const cls = isCorrect ? 'feedback-card correct' : 'feedback-card wrong'
    const card = document.createElement('div')
    card.className = cls
    card.textContent = feedback
    els.feedbackPanel.appendChild(card)
    // Scroll the text panel so the new card is visible
    const textPanel = els.feedbackPanel.closest('.modal-text')
    if (textPanel) textPanel.scrollTop = textPanel.scrollHeight
  }

  function clearFeedback() {
    if (els.feedbackPanel) els.feedbackPanel.innerHTML = ''
  }

  // ---- Letter board ----

  function updateLetterBoard(blanks, activeBlankIndex) {
    if (!els.letterBoard) return
    const counts = {}
    const sourceMode = state.lbMode
    for (const b of blanks) {
      if (b.solved || b.revealed) continue
      if (sourceMode === 'word' && b.blankIndex !== activeBlankIndex) continue
      for (const ch of b.answer.toLowerCase()) {
        if (ch >= 'a' && ch <= 'z') counts[ch] = (counts[ch] || 0) + 1
      }
    }
    for (const tile of els.letterBoard.querySelectorAll('.lt')) {
      const letter = tile.getAttribute('data-letter')
      const sup = tile.querySelector('.lc')
      const n = counts[letter] || 0
      sup.textContent = n > 0 ? n : ''
      tile.classList.toggle('lb-active', n > 0)
      tile.classList.toggle('lb-empty', n === 0)
    }
  }

  function setLbMode(mode) {
    state.lbMode = mode
    els.lbModeAll.classList.toggle('active', mode === 'all')
    els.lbModeWord.classList.toggle('active', mode === 'word')
    updateLetterBoard(state.modal.blanks, state.modal.activeBlankIndex)
  }

  // ---- Modal rendering ----

  function renderModal(prev, next) {
    if (next.status === S.CLOSED) {
      closeModalDOM()
      return
    }

    const u = next.unit
    const it = u?.items?.[next.itemIndex]
    const itemTitle = it?.title || `Item ${next.itemIndex + 1}`

    els.modalTitle.textContent = `Practice: ${itemTitle}`
    els.modalSub.textContent = `${next.itemIndex + 1} / ${u?.items?.length ?? 0}  •  ${next.difficulty}`
    els.modalScore.textContent = `${next.score} / ${next.maxPoints}`

    // Summary overlay
    const isSummary = next.status === S.SUMMARY
    els.summary.classList.toggle('hidden', !isSummary)
    if (isSummary) {
      const solved = next.blanks.filter(b => b.solved).length
      const revealed = next.blanks.filter(b => b.revealed).length
      els.summaryDetail.innerHTML =
        `Score: <strong>${next.score}</strong> / ${next.maxPoints}<br>` +
        `Solved: ${solved} &nbsp;|&nbsp; Revealed: ${revealed} &nbsp;|&nbsp; Total: ${next.blanks.length}`
    }

    // Error display
    if (next.status === S.ERROR) {
      els.maskedText.innerHTML = `<div class='modal-error'>Error: ${escapeHTML(next.error)}</div>`
      return
    }

    // Masked text
    els.maskedText.innerHTML = renderMaskedHTML(next.tokens, next.blanks, next.activeBlankIndex, next.seededLetters)

    // Blank meta
    const b = next.blanks[next.activeBlankIndex]
    if (!b) {
      els.blankMeta.textContent = 'Click a blank to begin'
    } else {
      const status = b.solved ? 'solved' : b.revealed ? 'revealed' : 'unsolved'
      els.blankMeta.textContent = `Blank ${b.blankIndex + 1} of ${next.blanks.length}  •  ${status}  •  ${b.answer.length} letters`
    }

    // Hint box (clue text only)
    els.hintBox.textContent = next.hintText || ''

    // Feedback notification log (correct / wrong)
    // Append a new card whenever feedback text changes; clear only on fresh modal open.
    if (next.lastFeedback && next.lastFeedback !== prev.lastFeedback) {
      showFeedback(next.lastFeedback)
    } else if (next.status === S.OPENING) {
      clearFeedback()
    }

    // Letter board
    updateLetterBoard(next.blanks, next.activeBlankIndex)

    // Input state
    const disableInput = isSummary || next.status === S.ERROR
    els.guessInput.disabled = disableInput
    els.submitGuess.disabled = disableInput

    // Sync input value to state (important after correct guess clears it)
    if (!disableInput && els.guessInput.value !== next.guess) {
      els.guessInput.value = next.guess
    }

    // Auto-focus input when a blank is active
    if (!disableInput && (next.status === S.FOCUS_BLANK || next.status === S.READY)) {
      if (prev.activeBlankIndex !== next.activeBlankIndex) {
        window.setTimeout(() => els.guessInput.focus(), 0)
      }
    }
  }

  // ---- Modal click handler ----
  // Fix from plan: stopPropagation on handled events prevents bubbling to page handler

  function onModalClick(e) {
    const t = e.target

    // Close via backdrop or back button
    if (t?.getAttribute?.('data-action') === 'close') {
      e.stopPropagation()
      doClose()
      return
    }

    // Hint buttons
    const hintLayer = t?.getAttribute?.('data-hint')
    if (hintLayer) {
      e.stopPropagation()
      dispatch({ type: 'USE_HINT', payload: { hintText: getHintText(state.modal, hintLayer) } })
      return
    }

    // Blank token click
    if (t?.classList?.contains('blank')) {
      e.stopPropagation()
      const idx = Number(t.getAttribute('data-blank-index'))
      dispatch({ type: 'SELECT_BLANK', payload: { blankIndex: idx } })
      return
    }
  }

  function doClose() {
    const returnTo = state.modal.returnTo
    dispatch({ type: 'CLOSE' })
    restoreReturnTo(returnTo)
    renderItems() // refresh completion badges
  }

  function restoreReturnTo(returnTo) {
    if (!returnTo) return
    window.setTimeout(() => {
      if (returnTo.hash) {
        const el = qs(returnTo.hash)
        if (el) el.scrollIntoView({ block: 'start' })
      } else {
        window.scrollTo(0, returnTo.scrollY || 0)
      }
    }, 0)
  }

  // ---- Keyboard handler ----

  function keyHandler(e) {
    if (!state.modal || state.modal.status === S.CLOSED) return

    if (e.key === 'Escape') {
      doClose()
      return
    }

    if (e.key === 'Enter' && !els.guessInput.disabled) {
      dispatch({ type: 'SUBMIT_GUESS' })
      return
    }

    // Route printable keys to the guess input when it's not already focused
    if (
      !els.guessInput.disabled &&
      document.activeElement !== els.guessInput &&
      e.key.length === 1 &&
      !e.ctrlKey && !e.metaKey && !e.altKey
    ) {
      els.guessInput.focus()
      // Don't preventDefault — let the character land in the input naturally
    }
  }

  // ---- Wire up all UI events ----

  function wireUI() {
    els.modeRead.addEventListener('click', () => setMode('read'))
    els.modePractice.addEventListener('click', () => setMode('practice'))
    els.difficultySelect.addEventListener('change', () => setDifficulty(els.difficultySelect.value))
    els.lbModeAll.addEventListener('click', () => setLbMode('all'))
    els.lbModeWord.addEventListener('click', () => setLbMode('word'))

    // Page-level click (items list only; modal stops propagation for its own clicks)
    document.addEventListener('click', onPageClick)

    // Modal container click
    els.modalRoot.addEventListener('click', onModalClick)

    // Hover removed — clicking a blank now sticks it as active (no hover auto-select)

    // Input
    els.guessInput.addEventListener('input', () => {
      dispatch({ type: 'INPUT_CHANGE', payload: { value: els.guessInput.value } })
    })

    els.submitGuess.addEventListener('click', () => dispatch({ type: 'SUBMIT_GUESS' }))
    els.revealWord.addEventListener('click', () => dispatch({ type: 'REVEAL_WORD' }))
    els.revealAll.addEventListener('click', () => dispatch({ type: 'REVEAL_ALL' }))
    els.prevBlank.addEventListener('click', () => dispatch({ type: 'PREV_BLANK' }))
    els.nextBlank.addEventListener('click', () => dispatch({ type: 'NEXT_BLANK' }))

    // Summary actions
    els.summaryClose.addEventListener('click', () => {
      persistCompletionFromModal(state.modal)
      doClose()
    })

    els.summaryNextItem.addEventListener('click', () => {
      persistCompletionFromModal(state.modal)
      const nextIndex = state.modal.itemIndex + 1
      const u = state.modal.unit
      if (!u || nextIndex >= (u.items || []).length) return
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

  // ---- Completion persistence ----

  function persistCompletionFromModal(modalState) {
    if (!modalState.completed) return
    const u = modalState.unit
    const it = u?.items?.[modalState.itemIndex]
    if (!u || !it) return
    writeCompletion(u.unit_id, it.item_id, modalState.difficulty, {
      score: modalState.score,
      completed_at: new Date().toISOString()
    })
  }

  // ---- Init ----

  async function init() {
    cacheEls()
    const unitPath = getParam('unit') || document.body.dataset.defaultUnit || ''
    if (unitPath) {
      wireUI()
      await loadUnit(unitPath)
    } else {
      await loadListing()
    }
  }

  return { init }
})()

function startApp() {
  App.init().catch(err => {
    console.error('[ClueChain Learning]', err)
    const items = document.getElementById('items')
    if (items) items.innerHTML = `<p style='color:#f88;padding:16px'>Failed to load: ${err.message}</p>`
  })
}

// ES modules are deferred; DOMContentLoaded may have already fired
if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', startApp)
} else {
  startApp()
}

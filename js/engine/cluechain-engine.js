'use strict'

/**
 * @fileoverview ClueChainEngine — shared, UI-agnostic game logic for both
 * Daily and Learning modes.
 *
 * Design goals:
 *  - No DOM, no fetch, no routing
 *  - Accepts both daily (hiddenWords[]) and learning (authored_variants[]) data
 *  - Both modes normalise into the same internal items[] shape
 *  - Returns plain snapshots from getState() — callers must not mutate them
 */

// ---- Blanking utilities (moved from learning/news.js) ----

export const STOPWORDS = new Set([
  'the','a','an','and','or','but','if','then','so','to','of','in','on','for','with','as','at','by','from',
  'is','are','was','were','be','been','being','it','this','that','these','those','their','there','here',
  'you','your','we','our','they','them','he','him','she','her','i','me','my','mine',
  'not','no','yes','do','does','did','doing','done','can','could','will','would','should','may','might','must'
])

/**
 * Tokenise text into word / non-word spans.
 * @param {string} text
 * @returns {Array<{t: string, isWord: boolean}>}
 */
export function tokenizeWithSpans(text) {
  const re = /([A-Za-z']+)|(\s+)|([^A-Za-z'\s]+)/g
  const out = []
  let m
  while ((m = re.exec(text)) !== null) {
    if (m[1]) out.push({ t: m[1], isWord: true })
    else if (m[2]) out.push({ t: m[2], isWord: false })
    else out.push({ t: m[3], isWord: false })
  }
  return out
}

function _clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)) }
function _slugKey(s) { return String(s || '').trim().toLowerCase() }

/**
 * Choose blank targets automatically from plain text.
 * @param {string} text
 * @param {string} difficulty
 * @param {Object} practiceCfg
 * @returns {{ tokens: Array, blanks: Array }}
 */
export function chooseBlankTargets(text, difficulty, practiceCfg) {
  const targets = practiceCfg?.blanking?.targets || {}
  const t = targets[difficulty] || targets.standard || { min_blanks: 6, max_blanks: 8 }
  const minB = t.min_blanks ?? 6
  const maxB = t.max_blanks ?? 8
  const want = _clamp(Math.floor((minB + maxB) / 2), 1, 20)
  const avoid = practiceCfg?.blanking?.avoid || {}

  const tokens = tokenizeWithSpans(text)
  const candidates = []

  for (let i = 0; i < tokens.length; i++) {
    if (!tokens[i].isWord) continue
    const w = tokens[i].t
    if (avoid.stopwords && STOPWORDS.has(w.toLowerCase())) continue
    if (avoid.very_short_words_max_len && w.length <= avoid.very_short_words_max_len) continue
    if (avoid.numbers && /\d/.test(w)) continue
    candidates.push(i)
  }

  if (candidates.length === 0) return { tokens, blanks: [] }

  // Sort by word length descending (prefer longer/rarer words)
  candidates.sort((a, b) => tokens[b].t.length - tokens[a].t.length)

  const chosen = []
  const step = Math.max(1, Math.floor(candidates.length / want))
  for (let i = 0; i < candidates.length && chosen.length < want; i += step) {
    chosen.push(candidates[i])
  }

  if (chosen.length < want) {
    const chosenSet = new Set(chosen)
    const remaining = candidates.filter(i => !chosenSet.has(i))
    while (chosen.length < want && remaining.length > 0) {
      const j = Math.floor(Math.random() * remaining.length)
      chosen.push(remaining.splice(j, 1)[0])
    }
  }

  chosen.sort((a, b) => a - b)

  const blanks = chosen.map((tokIndex, k) => ({
    blankIndex: k,
    tokIndex,
    answer: tokens[tokIndex].t,
    solved: false,
    revealed: false,
    usedHints: { direct: false, intermediate: false, indirect: false }
  }))

  return { tokens, blanks }
}

/**
 * Find the next unsolved blank, wrapping around.
 * @param {Array} blanks
 * @param {number} from
 * @returns {number}
 */
export function nextUnsolvedBlank(blanks, from) {
  if (!blanks.length) return -1
  for (let i = from + 1; i < blanks.length; i++) {
    if (!blanks[i].solved && !blanks[i].revealed) return i
  }
  for (let i = 0; i < blanks.length; i++) {
    if (!blanks[i].solved && !blanks[i].revealed) return i
  }
  return _clamp(from, 0, blanks.length - 1)
}

// ---- ClueChainEngine ----

/**
 * Shared game engine for both Daily and Learning modes.
 *
 * Usage — daily:
 *   const engine = new ClueChainEngine(puzzleData, { mode: 'daily', params })
 *   engine.init()
 *
 * Usage — learning:
 *   const engine = new ClueChainEngine(item, { mode: 'learning', practiceCfg, difficulty })
 *   await engine.init()          // async only for learning (authored_variants path is sync too)
 */
export class ClueChainEngine {
  /**
   * @param {Object} data         Raw puzzle data (daily or learning item)
   * @param {Object} options
   * @param {'daily'|'learning'} options.mode
   * @param {Object} [options.params]       game_parameters.json (daily mode)
   * @param {Object} [options.practiceCfg]  practice config from unit JSON (learning mode)
   * @param {string} [options.difficulty]   difficulty key (learning mode, default 'standard')
   */
  constructor(data, options = {}) {
    this._data = data
    this._mode = options.mode || 'daily'
    this._params = options.params || null
    this._practiceCfg = options.practiceCfg || {}
    this._difficulty = options.difficulty || 'standard'

    /** @type {Array} Normalised internal items */
    this._items = []
    /** @type {Array} Tokens (learning mode only) */
    this._tokens = []
    /** @type {number} */
    this._activeIndex = -1
    /** @type {number} */
    this._score = 0
    /** @type {number} */
    this._maxScore = 100
    /** @type {boolean} */
    this._completed = false
    /** @type {number|null} streak is managed externally; engine just tracks whether the game ended */
    this._streak = null
  }

  // ---- Lifecycle ----

  /**
   * Parse data, set up internal state. Sync for daily mode, sync for learning too
   * (authored_variants path is synchronous; auto-blank is also sync).
   */
  init() {
    if (this._mode === 'daily') {
      this._initDaily()
    } else {
      this._initLearning()
    }
  }

  _initDaily() {
    const hiddenWords = (this._data.hiddenWords || [])
    const params = this._params

    // Normalise daily hiddenWords into shared items[]
    this._items = hiddenWords.map(w => ({
      word: w.word,
      solved: false,
      revealed: false,
      clues: Array.isArray(w.clues)
        ? w.clues.map(c => ({ text: c.clue || c.text || '', type: c.type || '', points: c.points || 0 }))
        : (w.clue ? [{ text: w.clue, type: 'hard', points: w.points || 0 }] : []),
      hintsUsed: [],
      // Daily-specific: track clue tiers
      activeClueIndex: 0,
      lowestClueIndexSeen: 0,
      // Letter positions in paragraph (for masking)
      positions: w.positions || [],
    }))

    // Score starts in deficit (see game-state.js setCurrentWords logic):
    // perfect play earns back to 100
    let totalWordPoints = 0
    this._items.forEach(item => {
      if (item.clues.length > 0) totalWordPoints += item.clues[0].points || 0
    })
    this._maxScore = 100
    this._score = Math.max(0, 100 - totalWordPoints)
    this._activeIndex = 0
    this._completed = false
  }

  _initLearning() {
    const it = this._data
    const text = it.text || ''
    const practiceCfg = this._practiceCfg
    const difficulty = this._difficulty

    const authoredVariant = it.authored_variants?.[0]
    if (authoredVariant?.blanks?.length) {
      const hintMap = new Map()
      for (const entry of authoredVariant.blanks) {
        // Support both legacy {hints:{indirect,intermediate,direct}} and
        // new {clues:[{type,clue,points}]} formats.
        let hints = entry.hints || {}
        if (!entry.hints && Array.isArray(entry.clues)) {
          hints = {}
          for (const c of entry.clues) {
            const t = (c.type || '').toLowerCase()
            const text = c.clue || c.text || ''
            if (t === 'indirect')     hints.indirect     = text
            else if (t === 'suggestive') hints.intermediate = text
            else if (t === 'straight')   hints.direct      = text
            else if (t === 'intermediate') hints.intermediate = text
            else if (t === 'direct')   hints.direct      = text
          }
        }
        hintMap.set(_slugKey(entry.word), hints)
      }

      const tokens = tokenizeWithSpans(text)
      const authoredWords = authoredVariant.blanks.map(e => _slugKey(e.word))
      const used = new Set()
      const blanks = []

      for (let i = 0; i < tokens.length; i++) {
        if (!tokens[i].isWord) continue
        const key = _slugKey(tokens[i].t)
        if (!authoredWords.includes(key) || used.has(key)) continue
        used.add(key)
        blanks.push({
          blankIndex: blanks.length,
          tokIndex: i,
          answer: tokens[i].t,
          hints: hintMap.get(key) || {},
          solved: false,
          revealed: false,
          usedHints: { direct: false, intermediate: false, indirect: false }
        })
      }

      blanks.sort((a, b) => a.tokIndex - b.tokIndex)
      blanks.forEach((b, k) => { b.blankIndex = k })

      if (blanks.length) {
        this._tokens = tokens
        this._items = this._normaliseLearningBlanks(blanks)
        this._activeIndex = 0
        this._score = 0
        this._maxScore = 100
        this._completed = false
        return
      }
    }

    // Auto-blank fallback
    const { tokens, blanks } = chooseBlankTargets(text, difficulty, practiceCfg)
    this._tokens = tokens
    this._items = this._normaliseLearningBlanks(blanks)
    this._activeIndex = this._items.length ? 0 : -1
    this._score = 0
    this._maxScore = 100
    this._completed = false
  }

  /**
   * Normalise learning blanks into the shared items[] shape.
   * @private
   */
  _normaliseLearningBlanks(blanks) {
    return blanks.map(b => ({
      word: b.answer,
      solved: b.solved || false,
      revealed: b.revealed || false,
      // Map hint layers to clues array for shared API compatibility
      clues: [
        { text: b.hints?.indirect  || '', type: 'indirect',    points: 0 },
        { text: b.hints?.intermediate || '', type: 'intermediate', points: 0 },
        { text: b.hints?.direct    || '', type: 'direct',      points: 0 },
      ],
      hintsUsed: [],
      // Learning-specific raw blank data (needed for scoring and hint display)
      _blank: b,
      // Keep tokIndex for text rendering
      tokIndex: b.tokIndex,
    }))
  }

  // ---- Getters ----

  /**
   * Returns a plain (frozen) snapshot of current state.
   * @returns {Object}
   */
  getState() {
    return Object.freeze({
      mode: this._mode,
      items: this._items.map(item => ({ ...item })),
      tokens: this._tokens.slice(),
      activeIndex: this._activeIndex,
      score: this._score,
      maxScore: this._maxScore,
      completed: this._completed,
      streak: this._streak,
      replayAllowed: this._mode === 'learning',
    })
  }

  // ---- Gameplay ----

  /**
   * Submit a guess for the active item.
   * @param {string} guess
   * @returns {{ correct: boolean, deltaScore: number, done: boolean, feedback: string }}
   */
  submitGuess(guess) {
    if (this._mode === 'daily') return this._submitGuessDaily(guess)
    return this._submitGuessLearning(guess)
  }

  _submitGuessDaily(guess) {
    const normalised = (guess || '').toLowerCase().trim()
    const item = this._items.find(it => it.word.toLowerCase() === normalised && !it.solved)

    // Each guess attempt potentially reveals one more clue (existing behaviour)
    this._revealNextClueOnGuess()

    if (item) {
      item.solved = true
      const clueIdx = item.lowestClueIndexSeen || 0
      const pointsEarned = item.clues[clueIdx] ? (item.clues[clueIdx].points || 0) : (item.clues[0]?.points || 0)
      this._score += pointsEarned
      this._completed = this._items.every(it => it.solved || it.revealed)
      return { correct: true, deltaScore: pointsEarned, done: this._completed, feedback: 'Correct!' }
    }

    // Wrong guess
    const penalty = this._params?.penalties?.wrongGuess ?? 5
    const deduct = Math.min(this._score, penalty)
    this._score = Math.max(0, this._score - deduct)
    return { correct: false, deltaScore: -deduct, done: false, feedback: 'Not quite — try again' }
  }

  _submitGuessLearning(guess) {
    const activeItem = this._items[this._activeIndex]
    if (!activeItem) return { correct: false, deltaScore: 0, done: false, feedback: 'Select a blank first' }

    const g = (guess || '').trim()
    if (!g) return { correct: false, deltaScore: 0, done: false, feedback: 'Type a guess' }

    const correct = _slugKey(g) === _slugKey(activeItem.word)
    let deltaScore = 0
    let feedback = ''

    if (correct) {
      activeItem.solved = true
      const perBlank = Math.floor(this._maxScore / Math.max(1, this._items.length))
      deltaScore = perBlank
      feedback = 'Correct!'
    } else {
      deltaScore = -1
      feedback = 'Not quite — try again'
    }

    this._score = _clamp(this._score + deltaScore, 0, this._maxScore)
    this._completed = this._items.every(it => it.solved || it.revealed)
    return { correct, deltaScore, done: this._completed, feedback }
  }

  /**
   * (Daily) After each guess, reveal one previously hidden clue at random.
   * @private
   */
  _revealNextClueOnGuess() {
    // This replicates the shownWordIndices behaviour from game-state.js checkGuess.
    // The engine doesn't own the UI concept of "shown indices" but it does own
    // which items' clues should become visible. We track this via item.clueVisible.
    const hidden = this._items.filter(it => !it.solved && !it.revealed && !it.clueVisible)
    if (hidden.length === 0) return
    const pick = hidden[Math.floor(Math.random() * hidden.length)]
    pick.clueVisible = true
  }

  /**
   * (Daily) Reveal the next clue tier for the active word.
   * @returns {{ clueIndex: number, clue: Object } | null}
   */
  revealNextClue() {
    const item = this._items[this._activeIndex]
    if (!item || item.solved || item.revealed) return null
    const nextIdx = (item.activeClueIndex || 0) + 1
    if (!item.clues[nextIdx]) return null
    item.activeClueIndex = nextIdx
    if (nextIdx > (item.lowestClueIndexSeen || 0)) {
      item.lowestClueIndexSeen = nextIdx
    }
    return { clueIndex: nextIdx, clue: item.clues[nextIdx] }
  }

  /**
   * (Learning) Use a hint layer for the active blank.
   * @param {'direct'|'intermediate'|'indirect'} layer
   * @returns {string} The hint text
   */
  useHint(layer) {
    const item = this._items[this._activeIndex]
    if (!item) return 'Select a blank first'
    if (item.solved || item.revealed) return `The word was: ${item.word}`

    if (!item.hintsUsed.includes(layer)) item.hintsUsed.push(layer)

    // Find the clue matching this layer
    const clue = item.clues.find(c => c.type === layer)
    if (clue && clue.text) return `${clue.text} (${item.word.length})`

    // Generic fallback
    switch (layer) {
      case 'direct':       return `Definition: look for a ${item.word.length}-letter word that fits this context.`
      case 'intermediate': return `Context clue: read the surrounding sentence for a hint about this word.`
      case 'indirect':     return `Indirect: think of a synonym or related concept for this position in the text.`
      default:             return `Hint for this blank.`
    }
  }

  /**
   * (Daily) Purchase a letter from the marketplace.
   * @param {string} letter
   * @param {'vowel'|'consonant'} type
   * @returns {{ success: boolean, cost: number }}
   */
  purchaseLetter(letter, type) {
    // The daily game-state.js handles the full marketplace logic (letterCounts, sets).
    // This stub delegates cost calculation to the params object so callers can use it.
    // Full marketplace state (purchased sets, letter counts) remains in game-state.js
    // for now, since that's the plan's "daily adapter" responsibility.
    const params = this._params
    if (!params) return { success: false, cost: 0 }
    const costPerInstance = type === 'vowel'
      ? (params.marketplace?.vowel?.costPerInstance ?? 2)
      : (params.marketplace?.consonant?.costPerInstance ?? 3)
    return { success: true, costPerInstance }
  }

  /**
   * Reveal a word (forfeit active item) with a score penalty.
   * @param {number} [index] defaults to activeIndex
   * @returns {{ success: boolean, pointsDeducted: number, done: boolean }}
   */
  revealWord(index) {
    const idx = index !== undefined ? index : this._activeIndex
    const item = this._items[idx]
    if (!item || item.solved || item.revealed) return { success: false, pointsDeducted: 0, done: false }

    const penalty = this._mode === 'daily'
      ? (this._params?.marketplace?.wordReveal?.cost ?? 8)
      : 10
    const deduct = Math.min(this._score, penalty)
    this._score = Math.max(0, this._score - deduct)
    item.revealed = true
    this._completed = this._items.every(it => it.solved || it.revealed)

    // Daily: surface a new clue when a word is revealed
    if (this._mode === 'daily') this._revealNextClueOnGuess()

    return { success: true, pointsDeducted: deduct, done: this._completed }
  }

  /**
   * Forfeit everything — reveal all unsolved items, score → 0.
   * @returns {{ done: boolean }}
   */
  revealAll() {
    this._items.forEach(it => { if (!it.solved) it.revealed = true })
    this._score = 0
    this._completed = true
    return { done: true }
  }

  // ---- Navigation ----

  /**
   * (Daily) Set active word by index.
   * @param {number} index
   */
  selectWord(index) {
    if (index >= 0 && index < this._items.length) {
      this._activeIndex = index
    }
  }

  /**
   * (Learning) Set active blank by index.
   * @param {number} index
   */
  selectBlank(index) {
    if (index >= 0 && index < this._items.length) {
      this._activeIndex = index
    }
  }

  /**
   * Advance activeIndex to the next unsolved item.
   * @returns {number} new activeIndex
   */
  nextUnsolved() {
    const idx = nextUnsolvedBlank(
      this._items.map(it => ({ solved: it.solved, revealed: it.revealed })),
      this._activeIndex
    )
    this._activeIndex = idx
    return idx
  }
}

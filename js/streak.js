/**
 * @fileoverview Pure streak logic for ClueChain.
 * No I/O, no globals — fully unit-testable.
 *
 * Run tests: node js/tests/streak.test.js
 */

/**
 * Returns 'YYYY-MM-DD' from a Date using local time.
 * @param {Date} date
 * @returns {string}
 */
export function localDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * Returns the local-calendar date key for the day before todayKey.
 * Uses noon as a DST-safe anchor (±1h DST shifts can't cross midnight from noon).
 * @param {string} todayKey - 'YYYY-MM-DD'
 * @returns {string} 'YYYY-MM-DD'
 */
export function yesterdayKey(todayKey) {
  const [y, m, d] = todayKey.split('-').map(Number)
  const noon = new Date(y, m - 1, d, 12, 0, 0)
  noon.setDate(noon.getDate() - 1)
  return localDateKey(noon)
}

/**
 * Pure streak state machine. Apply when a daily puzzle is completed.
 *
 * @param {Object} state - Current streak record
 * @param {number} state.currentStreak
 * @param {number} state.longestStreak
 * @param {string|null} state.lastCompletedDate - 'YYYY-MM-DD' or null
 * @param {string|null} state.lastCompletedAt - ISO timestamp or null
 * @param {Date} completedAt - Local Date at the moment of completion
 * @returns {Object} New streak record (does not mutate input)
 */
export function applyDailyCompletion(state, completedAt) {
  const todayKey = localDateKey(completedAt)

  // Already completed today — no streak change (replay does not count)
  if (state.lastCompletedDate === todayKey) {
    return { ...state, lastCompletedAt: completedAt.toISOString() }
  }

  const yKey = yesterdayKey(todayKey)
  const currentStreak = state.lastCompletedDate === yKey
    ? (state.currentStreak || 0) + 1
    : 1

  const longestStreak = Math.max(state.longestStreak || 0, currentStreak)

  return {
    currentStreak,
    longestStreak,
    lastCompletedDate: todayKey,
    lastCompletedAt: completedAt.toISOString()
  }
}

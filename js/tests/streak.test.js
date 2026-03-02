'use strict'

// Run from ClueChain root: node js/tests/streak.test.js
// Node 20+ auto-detects ES module syntax (produces a harmless warning).
// To silence the warning: add {"type":"module"} to package.json in this dir.

const { applyDailyCompletion, localDateKey, yesterdayKey } = await import('../streak.js')

function assertEqual(actual, expected, msg) {
  const a = JSON.stringify(actual)
  const e = JSON.stringify(expected)
  if (a !== e) {
    throw new Error(`${msg}\nExpected: ${e}\nActual:   ${a}`)
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg)
}

function state0() {
  return { currentStreak: 0, longestStreak: 0, lastCompletedDate: null, lastCompletedAt: null }
}

// Helpers to create a local Date deterministically.
// NOTE: new Date(y, m-1, d, h, min) uses local time zone.
function dLocal(y, m, d, h = 12, min = 0) {
  return new Date(y, m - 1, d, h, min, 0, 0)
}

function run(name, fn) {
  try {
    fn()
    console.log(`PASS: ${name}`)
  } catch (e) {
    console.error(`FAIL: ${name}\n${e.stack || e}`)
    process.exitCode = 1
  }
}

/* -----------------------
   Tests
------------------------ */

run('1) First ever completion sets streak to 1', () => {
  const s = state0()
  const dt = dLocal(2026, 2, 25, 8, 0)
  const next = applyDailyCompletion(s, dt)

  assertEqual(next.currentStreak, 1, 'currentStreak should be 1')
  assertEqual(next.longestStreak, 1, 'longestStreak should be 1')
  assertEqual(next.lastCompletedDate, localDateKey(dt), 'lastCompletedDate should match today')
})

run('2) Completing twice on same local date does not increment', () => {
  const dt1 = dLocal(2026, 2, 25, 8, 0)
  const dt2 = dLocal(2026, 2, 25, 20, 0)

  const s1 = applyDailyCompletion(state0(), dt1)
  const s2 = applyDailyCompletion(s1, dt2)

  assertEqual(s2.currentStreak, 1, 'streak should not increment on same day replay')
  assertEqual(s2.longestStreak, 1, 'longest should remain 1')
  assertEqual(s2.lastCompletedDate, localDateKey(dt1), 'lastCompletedDate remains today')
})

run('3) Completing on consecutive local dates increments streak', () => {
  const dt1 = dLocal(2026, 2, 25, 23, 50)
  const dt2 = dLocal(2026, 2, 26, 0, 10)

  const s1 = applyDailyCompletion(state0(), dt1)
  const s2 = applyDailyCompletion(s1, dt2)

  assertEqual(s2.currentStreak, 2, 'streak should increment to 2')
  assertEqual(s2.longestStreak, 2, 'longest should be 2')
  assertEqual(s2.lastCompletedDate, localDateKey(dt2), 'lastCompletedDate should be new day')
})

run('4) Missing a day resets streak to 1', () => {
  const dt1 = dLocal(2026, 2, 25, 10, 0)
  const dt3 = dLocal(2026, 2, 27, 10, 0) // skipped 26th

  const s1 = applyDailyCompletion(state0(), dt1)
  const s2 = applyDailyCompletion(s1, dt3)

  assertEqual(s2.currentStreak, 1, 'streak should reset to 1 after gap')
  assertEqual(s2.longestStreak, 1, 'longest remains 1 (only two completions with gap)')
})

run('5) Longest streak tracks max over time', () => {
  const dt1 = dLocal(2026, 2, 25, 9, 0)
  const dt2 = dLocal(2026, 2, 26, 9, 0)
  const dt3 = dLocal(2026, 2, 27, 9, 0)
  const dt5 = dLocal(2026, 3, 1, 9, 0) // gap

  let s = state0()
  s = applyDailyCompletion(s, dt1) // 1
  s = applyDailyCompletion(s, dt2) // 2
  s = applyDailyCompletion(s, dt3) // 3
  assertEqual(s.currentStreak, 3, 'streak should be 3')
  assertEqual(s.longestStreak, 3, 'longest should be 3')

  s = applyDailyCompletion(s, dt5) // reset to 1
  assertEqual(s.currentStreak, 1, 'streak resets after gap')
  assertEqual(s.longestStreak, 3, 'longest should stay 3')
})

run('6) yesterdayKey computes calendar yesterday (no 24h subtraction)', () => {
  // This test ensures yesterdayKey is calendar-based.
  // It will pass regardless of DST details, as long as yesterdayKey uses calendar subtraction.
  const today = '2026-03-01'
  const y = yesterdayKey(today)
  assertEqual(y, '2026-02-28', 'yesterdayKey should be Feb 28, 2026 for Mar 1, 2026 (non-leap year)')
})

run('7) Leap day: yesterdayKey handles Feb 29 correctly', () => {
  // 2028 is a leap year. (Divisible by 4 and not a century year.)
  const today = '2028-03-01'
  const y = yesterdayKey(today)
  assertEqual(y, '2028-02-29', 'yesterdayKey should return Feb 29 on leap year')
})

console.log('Done.')

## ClueChain Daily Streak Spec

### Goal

Maintain a **daily streak** per logged-in user.

A streak increments only when the user **completes the Daily puzzle for that local calendar date**.

* Score does not matter.
* No skip feature.
* Replay does not count.
* Time of day does not matter.
* All streak logic uses the user’s **local date** (not UTC).

---

## Definitions

### Daily puzzle

* Exactly one puzzle per local date.
* Identified by a stable puzzle key like:

  * `dailyKey = 'YYYY-MM-DD'` (preferred), or
  * `mmdd` with a year override (your current system)
* For streak purposes, we only care about the **local date key**.

### Completed

A Daily puzzle is “completed” when:

* Every masked word is either **solved or revealed**, and
* The session reaches an explicit terminal state (e.g., modal shows summary, user closes the completion screen, or your code calls a `completeDailyPuzzle()` function).

Important: “Completion” is an event your app fires once.

### Local date key

A string computed in local time:

* Format: `YYYY-MM-DD`
* Example: `2026-03-01`

---

## Data model

### Per-user streak record

Store (client-side first, server later):

```json
{
  "currentStreak": 7,
  "longestStreak": 12,
  "lastCompletedDate": "2026-02-25",
  "lastCompletedAt": "2026-02-25T21:18:34.552Z"
}
```

Field meanings:

* `currentStreak`: current consecutive-day count
* `longestStreak`: max historical streak
* `lastCompletedDate`: local-date key of last completion (critical)
* `lastCompletedAt`: timestamp for debugging/analytics only (not used for streak math)

### Storage key

If localStorage:

* `cluechain:streak:<userId>`

If server-backed later:

* same fields in user profile

---

## Streak update rules

### Inputs

* `state`: current streak record
* `completedAt`: Date object at completion time (client time)
* `todayKey`: local date key from `completedAt`

### Outputs

* `newState`: updated streak record

### Algorithm (must follow exactly)

1. Compute `todayKey` (local date of completion time)

2. If `state.lastCompletedDate === todayKey`

* Do not change streak (replay does not count)
* Update `lastCompletedAt` optionally
* Return

3. Else compute `yesterdayKey` from `todayKey` using **calendar day subtraction** in local time (not “minus 24 hours”)

* Use a safe method like “noon local time” then subtract 1 day

4. If `state.lastCompletedDate === yesterdayKey`

* `currentStreak = state.currentStreak + 1`

5. Else

* `currentStreak = 1` (because they completed today, but they had a gap)

6. `longestStreak = max(state.longestStreak, currentStreak)`

7. Set:

* `lastCompletedDate = todayKey`
* `lastCompletedAt = completedAt.toISOString()`

Return updated state.

---

## Edge cases (explicit)

1. **First ever completion**

* lastCompletedDate missing
* result: `currentStreak = 1`, `longestStreak = 1`

2. **Two completions same day**

* lastCompletedDate == todayKey
* result: streak unchanged (no double count)

3. **Missed one or more days**

* lastCompletedDate older than yesterdayKey
* result: streak resets to 1

4. **Daylight Saving Time**

* Must not use “subtract 24 hours”
* Must subtract one calendar day from a local date anchor (noon recommended)

5. **Travel across time zones**

* Use the device’s local time at completion. Streak follows the user’s local calendar experience.

---

## Integration points in your app

### Where to update streak

Trigger streak update only at the moment Daily puzzle completion becomes true:

* Daily puzzle engine detects “all blanks solved or revealed”
* Calls `completeDailyPuzzle(userId, completedAt)`

### Pseudocode integration

```js
if (isDailyPuzzle && isCompleted) {
  updateDailyStreak(userId, new Date())
}
```

### Completion gating

The completion event must fire once per day:

* Use `lastCompletedDate == todayKey` as the hard gate
* Never increment if already completed today

---

## Required functions (module API)

Create a module, for example `streak.js`, exporting:

1. `localDateKey(date) -> 'YYYY-MM-DD'`
2. `yesterdayKey(todayKey) -> 'YYYY-MM-DD'` (calendar safe)
3. `applyDailyCompletion(state, completedAt) -> newState`
4. `readStreak(userId) -> state`
5. `writeStreak(userId, state)`

Optional:

* `getStreakDisplay(state)` for UI

---

## UI requirements

### Daily page display

Show:

* `currentStreak` prominently
* Optional: `longestStreak`

### After completion

On summary screen:

* Show “Streak: X days”
* If it increased: show “+1” indicator (optional)

---

## Testing requirements (must pass)

1. New user completes today → streak 1
2. Same user completes again today → still 1
3. Completes next day → 2
4. Skips a day, completes following day → 1
5. Completes at 11:50pm, then next day at 12:10am → 2
6. DST transition weekend: completing on consecutive local dates increments correctly

----

Below are plain-JS unit tests you can run in Node (no frameworks). They assume your `streak.js` exports:

* `localDateKey(d)`
* `yesterdayKey(todayKey)`
* `applyDailyCompletion(state, completedAt)`

## `streak.test.js`

```js
'use strict'

// Run: node streak.test.js
// Assumes: streak.js is in same folder and is an ES module or CJS. Pick one section below.

// ----- If streak.js is ES module (export ...), use this:
const { applyDailyCompletion, localDateKey, yesterdayKey } = await import('./streak.js')

// ----- If streak.js is CommonJS (module.exports = ...), use this instead:
// const { applyDailyCompletion, localDateKey, yesterdayKey } = require('./streak.js')

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
```

### Notes

* These tests use `new Date(y, m-1, d, h, min)` which is local time, matching your spec.
* DST-specific tests are hard to make deterministic without forcing a timezone. The `yesterdayKey` test is the important safety check: it ensures you aren’t doing “minus 24 hours”.


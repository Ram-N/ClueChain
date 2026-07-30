Good. You are thinking correctly.

What you want is:

* One core game engine
* Two different entry points
* Two different UIs
* Zero duplicated logic

That is exactly the right architectural instinct.

Let’s structure this cleanly.

---

# 1. Separate Engine from Presentation

You must split ClueChain into:

### A. Core Game Engine (Pure Logic)

No UI. No layout. No routing.

This layer handles:

* Score calculation
* Clue reveal logic
* Key usage
* Letter purchase logic
* Completion detection
* Streak logic (only when applicable)
* State transitions

This should be completely UI-agnostic.

Example mental model:

```
ClueChainEngine
  - init(gameData)
  - revealNextClue()
  - useKey()
  - purchaseLetter(letter)
  - submitGuess(word)
  - getGameState()
```

Both Daily and Learning Pack modes call the same engine.

---

# 2. Two Game Modes (Thin Wrappers)

Now you create two wrappers around the engine.

---

## Mode 1: Daily Puzzle

* Full page layout
* Score + streak visible
* Leaderboard visible
* Persistent daily ID
* One play per day

It mounts the engine like:

```
const game = new ClueChainEngine(dailyPuzzleData)
```

And renders state from `game.getGameState()`.

---

## Mode 2: Learning Pack

This is NOT a new game.
It is just a different launcher.

Flow:

* User selects Unit
* User selects Paragraph
* Modal opens
* Inside modal → exact same ClueChain UI component

Important:
The modal should not contain new gameplay logic.

It should literally render:

```
<ClueChainGame engine={gameInstance} />
```

Same component. Same visuals. Same scoring system.

Only difference:

* No streak tracking
* No leaderboard
* Maybe no daily lock restriction
* No permanent scoring impact

That’s it.

---

# 3. Architectural Pattern (Clean Version)

Think of this structure:

```
/core
   cluechain-engine.js

/components
   ClueChainGame.jsx   ← full game UI

/modes
   DailyPage.jsx
   LearningPackModal.jsx
```

DailyPage:

* Fetch daily puzzle
* Create engine
* Render <ClueChainGame />

LearningPackModal:

* Fetch selected paragraph puzzle
* Create engine
* Render <ClueChainGame />

The ClueChainGame component should not know:

* If it's daily
* If it's learning pack
* If it's modal
* If it's full page

It just renders the game.

---

# 4. Important UX Decision

You said:

> Inside learning pack modal it should look exactly the same as daily puzzle.

That is correct.

But I would slightly modify:

Visually same game layout.
Context different header.

Example:

Daily:
"Daily Puzzle – March 3"

Learning Pack:
"Unit 4 – French Revolution – Paragraph 2"

Everything below that header is identical.

---

# 5. What Must Be Mode-Specific

You need a config flag when initializing engine:

```
new ClueChainEngine(data, {
   mode: 'daily' | 'learning'
})
```

Then internally:

If mode === daily:

* Enable streak
* Lock replay
* Save completion

If mode === learning:

* Allow replay
* No streak
* Optional unlimited attempts

Everything else identical.

---

# 6. Why This Matters Long Term

Because you are building:

* Daily competition system
* Structured curriculum system

If you fork logic now, you will:

* Break balancing
* Introduce scoring inconsistencies
* Create debugging chaos

One engine prevents all of that.

---

# 7. One Subtle Design Question

In Learning Packs:

Should score matter?

Options:

1. Yes, but only local to session.
2. Yes, but tracked per unit.
3. No, just show progress.

For education, I would recommend:

* Keep score.
* But track per learning pack unit.
* Not global leaderboard.

That makes it feel real without pressure.

---

# 8. Final Mental Model

You are not building:

Two games.

You are building:

One game engine
Two containers
Different metadata

That’s the correct way.


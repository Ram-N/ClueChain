# ClueChain TODO List

This document tracks tasks and improvements needed for the ClueChain project.

Last updated: July 2026

---

## Open Items

- In the text box (widget), there should be a faint (ghost) text saying "Type any answer..."


### 1. Settings Modal Implementation
- **Location**: `main.js:48`
- **Status**: Not implemented (shows "Settings coming soon!" alert)
- **Action Needed**: Design and implement a settings modal with user preferences
  - Possible settings: difficulty level, theme selection, etc.

### 2. Replay Warning for Daily Puzzle
- **Status**: Not started
- **Problem**: If a player has already completed today's puzzle, returning shows no message
- **Goal**: Detect if the player has already played today, and display a message like:
  "You've already played today's ClueChain! You can play again, but only your original score will be saved."
- **Dependencies**: Requires reading stored score from localStorage or Supabase

### 3. Debug and Console Logging Cleanup
- **Status**: Partially cleaned — 75+ console statements still remain across js/ files
- **Action Needed**:
  - Consider adding a debug flag to toggle verbose logging
  - Clean up or standardize logging approach for production

### 4. Gradual Replacement of "Okay" Puzzles
- **Status**: Ongoing background task
- **Goal**: Replace puzzles currently scored as "okay" with better-quality ones
- **Approach**: Generate → score → stage → replace workflow (see `docs/REPLACE_WITH_BETTER_PARAGRAPHS.md`)
- **Constraints**: Paragraphs over 200 words are automatically rejected
- **Pace**: Gradual, a few at a time

### 5. Backfill Metadata Fields on Existing Puzzles
- **Goal**: Add `topic`, `themes`, `source`, `summary` to all existing puzzle JSONs
- **Approach**: Script that reads each puzzle's `title` + `text`, sends a classification
  prompt to the LLM (Groq), and writes the fields back to the JSON file
- **Script location (proposed)**: `scripts/backfill_metadata.py`
- **Status**: Not started

---

## Future Feature Requests

### 6. Multiplayer/Social Features
- Daily leaderboards
- Compare streak statistics

### 7. Accessibility Improvements
- Keyboard navigation for all features
- Screen reader support
- High contrast mode
- Configurable font sizes

### 8. Analytics
- Track which clues are most helpful
- Monitor difficulty levels
- User engagement metrics

---

## Completed Items

- ✅ Create `remind-me` bash script with glow support
- ✅ Rename `Pickup.md` to `QUICKSTART.md`
- ✅ Progressive clue revealing system — initial 3 clues, additional revealed per guess, suffix revealing
- ✅ Calendar-based date navigation
- ✅ Suffix revealing system
- ✅ Chain link progress display
- ✅ Authentication system integration (Google OAuth, Supabase, streak tracking)
- ✅ Score sharing / social tease feature — WhatsApp share, copy button, deep-link URLs, score-tier banner (July 2026)
- ✅ Future date blocking — calendar disables future dates, arrow nav blocked, tooltip feedback
- ✅ Mobile-friendly layout — 4 media queries, collapsible panels, fixed input bar, 44px touch targets, notch support
- ✅ Help system — 8-rule modal with ESC/click-outside close, covers all game mechanics
- ✅ Content pipeline — automated batch generation, multi-dimensional scoring (rule-based + LLM), replacement workflow
- ✅ Paragraph scoring system — 6 dimensions, clue leak detection, length penalty, 200-word rejection
- ✅ Git status cleanup (old issue with library files)
- ✅ Learning packs system — separate page with topic categories, manifest-based unit loading

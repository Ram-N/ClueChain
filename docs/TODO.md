  # ClueChain TODO List

This document tracks tasks and improvements needed for the ClueChain project.

## Immediate Issues

### 1. Settings Modal Implementation
- **Location**: `main.js:41`
- **Status**: Not implemented
- **Description**: The settings button currently shows "Settings coming soon!" alert
- **Action Needed**: Design and implement a settings modal with user preferences
  - Possible settings: difficulty level, sound effects, theme selection, etc.

### 2. Git Status Cleanup
- **Issues**:
  - Deleted file: `assets/data/library/paragraphs_food,txt` (with comma) needs to be removed from git
  - New files to stage:
    - `assets/data/library/paragraphs_food.txt` (with period)
    - `remind-me` script
- **Action Needed**:
  ```bash
  git rm assets/data/library/paragraphs_food,txt
  git add assets/data/library/paragraphs_food.txt
  git add remind-me
  ```

## Content Pipeline

### 3. Paragraph Processing Workflow
- **Current Status**: Workflow is documented but manual
- **Process**:
  1. Raw paragraphs stored in `assets/data/library/` (currently 2 text files)
  2. Need to be "built out" as daily JSON files using Gemini Gem
  3. Must update `assets/data/index.json` when adding new files
  4. Validate with `python json_validator.py <filename>.json`
- **Action Needed**:
  - Process existing library files into daily JSON format
  - Consider automating the workflow
  - Document the Gemini Gem process in more detail

## Code Quality & Testing

### 4. Authentication System Testing
- **Files**:
  - `js/auth/auth-manager.js`
  - `js/auth/supabase-client.js`
  - `js/auth/streak-tracker.js`
  - `js/ui/auth-ui.js`
- **Status**: Integrated but needs comprehensive testing
- **Action Needed**:
  - Test Google OAuth flow end-to-end
  - Verify streak tracking functionality
  - Ensure proper error handling for auth failures

### 5. Future Date Blocking
- **Status**: Implemented and appears complete
- **Features**:
  - Calendar prevents clicking future dates
  - Arrow navigation disabled for future dates
  - Proper user feedback with tooltips
- **Action Needed**: Testing to confirm all edge cases work correctly

### 6. Progressive Clue System ✅ DONE
- **Status**: Complete — initial 3 clues, additional revealed per guess, suffix revealing active

## Optional Enhancements

### 7. Glow Fallback Enhancement
- **Location**: `remind-me` script
- **Current**: Falls back to `cat` if glow not found
- **Enhancement**: Could add installation instructions if glow is missing
- **Priority**: Low (current fallback works fine)

### 8. Debug and Console Logging Cleanup ← UP NEXT
- **Locations**: Multiple files have debug logging
  - `main.js`: "Log the selected date for debugging" (lines 204, 221, 391)
  - `game-controller.js`: "Log more details about the file" (line 358)
  - `game-state.js`: Multiple `console.debug` calls
- **Action Needed**:
  - Consider adding a debug flag to toggle verbose logging
  - Clean up or standardize logging approach for production

### 9. Mobile Responsiveness
- **Status**: Unknown
- **Action Needed**: Test on various mobile devices and screen sizes
- **Areas to check**:
  - Calendar picker on mobile
  - Letter marketplace keyboard layout
  - Clues display on small screens

### 10. Performance Optimization
- **Potential Areas**:
  - Loading all paragraph data files in parallel (currently implemented)
  - Caching paragraph data to avoid re-fetching
  - Optimizing DOM updates during gameplay

## Documentation

### 11. Update CLAUDE.md
- **Current**: Has good overview but could be enhanced
- **Additions Needed**:
  - Document the authentication system
  - Add troubleshooting section
  - Include the paragraph content workflow in detail

### 12. User Guide/Help System
- **Status**: Help button exists, implementation unknown
- **Action Needed**: Review help modal content and ensure it's comprehensive

## Near-Term Priorities (July 2026)

### 13. Mobile-Friendly Layout ⭐ TOP PRIORITY
- **Status**: Not started — current layout is designed for laptop/iPad
- **Problem**: The screen is crowded with letter marketplace, clues, paragraph, input field, and links
- **Goal**: Brainstorm and implement a layout that works well on phone screens
- **Approach to explore**:
  - Tabbed or accordion layout to collapse/expand sections (e.g., hide marketplace when guessing)
  - Sticky input at bottom, scrollable paragraph area
  - Smaller clue chips, collapsible marketplace
  - Consider whether full feature parity on mobile is achievable or if a simplified mode makes more sense
- **Note**: Feasibility TBD — some complexity may not translate well to small screens

### 14. Replay Warning for Daily Puzzle
- **Status**: Not started
- **Problem**: If a player has already completed today's puzzle, returning shows no message
- **Goal**: Detect if the player has already played today, and display a message like:
  "You've already played today's ClueChain! You can play again, but only your original score will be saved."
- **Dependencies**: Requires reading stored score from localStorage or Supabase

### 15. Gradual Replacement of "Okay" Puzzles
- **Status**: Ongoing background task
- **Goal**: Replace puzzles currently scored as "okay" (not poor, not good) with better-quality ones
- **Estimate**: ~100 "okay" puzzles remaining
- **Approach**: Continue using the existing generate → score → stage → replace workflow (see `docs/REPLACE_WITH_BETTER_PARAGRAPHS.md`)
- **Pace**: Gradual, a few at a time

### 16. Score Sharing / Social Tease Feature ✅ DONE
- **Status**: Implemented — WhatsApp share, copy button, deep-link URLs, score-tier banner, auto-scroll
- Completed: July 2026

## Feature Requests (Future)

### 17. Multiplayer/Social Features
- Share results with friends
- Daily leaderboards
- Compare streak statistics

### 18. Accessibility Improvements
- Keyboard navigation for all features
- Screen reader support
- High contrast mode
- Configurable font sizes

### 19. Analytics
- Track which clues are most helpful
- Monitor difficulty levels
- User engagement metrics

---

## Future Ideas (TBD)

### 20. Backfill Metadata Fields on Existing Puzzles
- **Goal**: Add `topic`, `themes`, `source`, `summary` to all ~150 existing puzzle JSONs
- **Approach**: Script that reads each puzzle's `title` + `text`, sends a short classification
  prompt to the LLM (Groq), and writes the fields back to the JSON file
- **Token cost**: Low — classification only, ~200–400 tokens per puzzle
- **Considerations**:
  - Run in batches respecting Groq free plan limits (100k tokens/day)
  - Validate output before writing (topic must be in controlled vocab)
  - Dry-run mode to preview without writing
- **Files affected**: All `assets/data/puzzles/daily/mmdd/*.json`
- **Script location (proposed)**: `scripts/backfill_metadata.py`

---

## Completed Items

- ✅ Create `remind-me` bash script with glow support
- ✅ Rename `Pickup.md` to `QUICKSTART.md`
- ✅ Progressive clue revealing system (#6)
- ✅ Calendar-based date navigation
- ✅ Suffix revealing system
- ✅ Chain link progress display
- ✅ Authentication system integration
- ✅ Score sharing / social tease feature (#16) — WhatsApp, copy, deep-links, score-tier banner (July 2026)

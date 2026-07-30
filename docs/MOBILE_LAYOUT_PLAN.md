# Mobile-Friendly Layout for ClueChain

## Context

ClueChain's current layout is a 2-column CSS grid designed for laptop/iPad screens. On phones (~375px wide), the 65%/35% split is unusable — panels are cramped, the keyboard grid overflows, and there's no way to focus on the core gameplay loop. TODO item #13 marks this as a top priority for July 2026.

The game has 5 major panels competing for screen space: paragraph, clues, input+score, letter marketplace, and notifications. The goal is to reorganize these for a single-column phone layout without removing any functionality.

## Design Decisions (confirmed by user)

- **Clues**: Active clue strip inline + full clues in a slide-up panel
- **Marketplace**: Hidden by default, accessible via bottom tab bar
- **Feedback**: Toast notifications for correct/wrong guesses

## Mobile Layout Structure

```
┌──────────────────────────┐
│ ClueChain  ← Jul 23 → ? │  Header (compact)
├──────────────────────────┤
│                          │
│  Paragraph with masked   │  Scrollable, max 40vh
│  words...                │
│                          │
├──────────────────────────┤
│ 📋 "Large animal..." +2  │  Active clue strip (tap to expand)
├──────────────────────────┤
│ 🔗🔗🔗🔗  Score: 12/45   │  Compact progress row
├──────────────────────────┤
│  (content area ends)     │
│                          │
│  ░░ bottom spacer ░░░░░  │  Prevents content hiding behind fixed bars
╞══════════════════════════╡
│ [Clues] [Keyboard] [Msgs]│  Fixed toggle bar (bottom: ~56px)
├──────────────────────────┤
│ [guess input___] [Go]🗝🪙│  Fixed input bar (bottom: 0)
└──────────────────────────┘

When a tab is active, its panel slides up between
the toggle bar and the main content (max-height 50vh).
```

When the phone keyboard opens, JS detects it via `visualViewport` API and hides the toggle bar so only the input bar remains above the keyboard.

## Implementation Steps

### Step 1: Add mobile DOM containers to `index.html`

Add these elements inside `.game-layout`, after the existing `</section>` tags but before the closing `</div>`:

- `<div id="mobile-active-clue" class="mobile-active-clue"></div>` — active clue strip
- `<div id="mobile-progress-row" class="mobile-progress-row"></div>` — compact score + chain
- `<div class="mobile-bottom-spacer"></div>` — spacer

Add these elements at the end of `<main>`, outside `.game-layout` (they're fixed-position overlays):

- Toggle bar with 3 buttons: Clues, Keyboard, Messages (`id="mobile-toggle-bar"`)
- Three panel containers: `id="mobile-panel-clues"`, `mobile-panel-keyboard`, `mobile-panel-messages`
- Toast container: `id="mobile-toast"`
- Input bar: `id="mobile-input-bar"` (input + submit + golden buttons move here via JS)

All hidden by default (`display: none`), shown only via media query.

### Step 2: CSS media queries in `style.css`

Add a `@media (max-width: 768px)` block that:

1. **Converts grid to flex column**: `.game-layout { display: flex; flex-direction: column; height: auto; min-height: auto; }`
2. **Hides desktop sections**: `#clues-section, #input-section, #marketplace-section { display: none; }`
3. **Shows mobile elements**: `.mobile-active-clue, .mobile-progress-row, .mobile-bottom-spacer, .mobile-input-bar, .mobile-toggle-bar { display: flex; }`
4. **Paragraph**: `max-height: 40vh; overflow-y: auto; font-size: 1rem;`
5. **Fixed input bar**: `position: fixed; bottom: 0; left: 0; right: 0; z-index: 50; background: #fff; box-shadow: 0 -2px 8px rgba(0,0,0,0.1); padding: 8px;`
6. **Fixed toggle bar**: `position: fixed; bottom: 56px; z-index: 49;` with 3 equal-width tab buttons
7. **Slide-up panels**: `position: fixed; bottom: 100px; max-height: 0; overflow: hidden; transition: max-height 0.3s ease;` → `.open { max-height: 50vh; overflow-y: auto; }`
8. **Toast styles**: Fixed at top center, fades in/out, color-coded (green/red/blue)
9. **Input font-size: 16px** — prevents iOS Safari auto-zoom on focus
10. **Touch targets**: Ensure all buttons ≥ 44px tap area
11. **Letter tiles**: Sized to fit 10 across in ~375px (about 30px each with 2px gaps)
12. **Compact header**: Smaller title, reduced padding

Add `@media (max-width: 480px)` refinements:
- Paragraph max-height to 30vh
- Slightly smaller letter tiles (28px)

### Step 3: Mobile setup logic in `js/ui-manager.js`

New exported function `setupMobileLayout()`:

1. Check `window.matchMedia('(max-width: 768px)').matches` — bail if desktop
2. **Move elements** (not clone) into mobile containers:
   - `#guess-input`, `#submit-guess`, `#golden-actions` → `#mobile-input-bar`
   - `#clues-container` → `#mobile-panel-clues`
   - `.letter-grid-container` + `#reset-selection` → `#mobile-panel-keyboard`
   - `#notification-panel` → `#mobile-panel-messages`
3. Moving (not cloning) preserves all existing event listeners — no re-attachment needed
4. Populate `#mobile-progress-row` with score + chain links (move `#chain-links` and `.score-display` there)

New function `setupMobileToggles()`:
- Add click listeners to toggle bar buttons
- Accordion behavior: one panel open at a time, tap again to close
- Track active panel state

New function `setupMobileKeyboardHandler()`:
- Listen on `window.visualViewport.addEventListener('resize', ...)`
- When keyboard opens (viewport height shrinks by >100px): hide toggle bar, close any open panel
- When keyboard closes: restore toggle bar

New exported function `updateMobileActiveClue()`:
- Called at the end of `renderClues()`
- Finds the first active (unsolved) clue from `#clues-list`
- Populates the `#mobile-active-clue` strip with: clue icon + text + "+N more" indicator
- Tap handler opens the Clues panel

Modify existing `addNotification()` (at the end, after adding the card):
- If mobile, also call `showMobileToast(message, type)` — a brief 2.5-second fade notification at the top of the screen
- Reuse the existing `showToast` name or add internal `showMobileToast()` function

### Step 4: Wire up in `js/game-controller.js`

- Import `setupMobileLayout` from `ui-manager.js`
- Call `setupMobileLayout()` at the end of `setupGame()` (after `setupMarketplace` and `renderClues` have run, so DOM elements exist to be moved)

### Step 5: Handle resize/orientation changes

- Add a `matchMedia` listener so that if the user rotates from portrait to landscape (or resizes browser past 768px), elements are moved back to their desktop positions
- This is a `setupMobileLayout()` counterpart: `teardownMobileLayout()` that moves elements back

## Files Modified

| File | Changes |
|------|---------|
| `index.html` | Add mobile container divs (active-clue, progress-row, input-bar, toggle-bar, panels, toast, spacer) |
| `style.css` | Add `@media (max-width: 768px)` and `@media (max-width: 480px)` blocks with full mobile layout |
| `js/ui-manager.js` | Add `setupMobileLayout()`, `teardownMobileLayout()`, `setupMobileToggles()`, `setupMobileKeyboardHandler()`, `updateMobileActiveClue()`, `showMobileToast()`. Modify `addNotification()` and `renderClues()` |
| `js/game-controller.js` | Import and call `setupMobileLayout()` in `setupGame()` |

## Key Technical Notes

- **Move DOM elements, don't clone** — this preserves event listeners attached by `setupMarketplace()`, `setupGuessInput()`, etc.
- **`font-size: 16px`** on inputs prevents iOS Safari auto-zoom
- **`visualViewport` API** is the reliable way to detect the mobile keyboard
- **No framework dependencies** — pure CSS + vanilla JS, consistent with the existing codebase
- Existing media queries at 768px/480px (chain links, input wrapping) will be superseded by the new comprehensive block

## Verification

1. Start local server: `python -m http.server 8000`
2. Open Chrome DevTools → toggle device toolbar
3. Test on iPhone SE (375px), iPhone 12 (390px), Pixel 5 (393px)
4. Verify: paragraph readable, active clue visible, input reachable
5. Test each toggle tab: Clues/Keyboard/Messages panels open and close
6. Make a correct guess — verify toast appears and fades
7. Make a wrong guess — verify toast appears red
8. Buy a letter — verify keyboard panel works, tile states update
9. Open phone keyboard (focus input) — verify toggle bar hides, input stays above keyboard
10. Rotate to landscape — verify layout adapts
11. Test on desktop (>768px) — verify desktop layout unchanged

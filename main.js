// Main entry point for ParaSight
import { initializeGame, getAvailableDates } from "./js/game-controller.js?v=1.1";
import { setupHelpButton } from "../shared/components/help-modal.js";
import { DailyCalendar } from "../shared/components/daily-calendar.js";

// Initialize the game when the window loads
window.onload = async () => {
  // Set the date display on page load, respecting ?date=MMDD param for deep links
  const dateElementInit = document.getElementById("current-date");
  if (dateElementInit) {
    const params = new URLSearchParams(window.location.search);
    const dateParam = params.get('date'); // e.g. "0719"
    let initialDate = new Date();
    if (dateParam && /^\d{4}$/.test(dateParam)) {
      const month = parseInt(dateParam.slice(0, 2), 10) - 1; // 0-based month
      const day = parseInt(dateParam.slice(2), 10);
      const parsed = new Date(new Date().getFullYear(), month, day);
      if (!isNaN(parsed.getTime()) && parsed <= new Date()) {
        initialDate = parsed;
      }
    }
    dateElementInit.textContent = initialDate.toLocaleDateString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric'
    });
  }

  // Initialize authentication system first
  try {
    await window.authManager.initialize();
    await window.streakTracker.initialize();
    await window.authUI.initialize();
    console.log('✅ Authentication system initialized');
  } catch (error) {
    console.error('❌ Failed to initialize authentication system:', error);
    // Continue with game initialization even if auth fails
  }

  // Then initialize the game
  initializeGame();

  // Then set up header controls
  const settingsButton = document.getElementById("settings-button");
  const dateElement = document.getElementById("current-date");
  const arrows = document.querySelectorAll(".arrow");

  // Settings button handler
  if (settingsButton) {
    settingsButton.addEventListener("click", () => {
      // TODO: Implement settings modal
      alert("Settings coming soon!");
    });
  }

  // Setup help button handler
  setupHelpButton();

  // Initialize current date from the element or default to today
  let currentDate =
    dateElement && dateElement.textContent
      ? new Date(dateElement.textContent)
      : new Date();

  // Update the date display
  function updateDateDisplay(date) {
    if (dateElement) {
      dateElement.textContent = date.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
    }
  }
  updateDateDisplay(currentDate);

  // Keep the URL bar in sync with the active puzzle date so links are shareable
  function setDateInUrl(date) {
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    history.replaceState(null, '', `?date=${mm}${dd}`);
  }
  setDateInUrl(currentDate);

  // ── Calendar module ─────────────────────────────────────────────────────

  const cal = new DailyCalendar({
    onDateSelect: (mmdd, date) => {
      currentDate = date;
      updateDateDisplay(currentDate);
      setDateInUrl(currentDate);
      initializeGame();
      updateArrowStates();
    },
    isGameInProgress: () => {
      const isComplete = document.querySelector('.game-over-message') !== null;
      return !isComplete && (
        document.querySelectorAll('#clues-list li.found').length > 0 ||
        document.querySelectorAll('.letter-tile.purchased').length > 0 ||
        document.querySelectorAll('.letter-tile.selected').length > 0
      );
    },
    getPlayHistory: async () => {
      if (!window.authManager?.isAuthenticated()) return null;
      const result = await window.streakTracker.getActivityHistory({ limit: 365 });
      if (!result.success) return null;
      const history = {};
      result.activities.forEach(a => {
        const pct = a.max_possible_score > 0
          ? Math.round((a.score / a.max_possible_score) * 100)
          : a.score;
        history[a.activity_date] = pct;
      });
      return history;
    },
    getAvailableDates: () => getAvailableDates(),
    historyWindowDays: 60,
    scoreThresholds: { green: 80, yellow: 50 },
  });

  // Expose globally so ui-manager.js can refresh after game completion
  window.loadPlayHistory = () => cal.refreshPlayHistory();

  // ── Arrow navigation ────────────────────────────────────────────────────

  // Helper: is date today or later?
  function isDateTodayOrFuture(date) {
    const todayStr = new Date().toISOString().split('T')[0];
    const dateStr  = date.toISOString().split('T')[0];
    return dateStr >= todayStr;
  }

  // Helper: is date strictly in the future?
  function isDateInFuture(date) {
    const todayStr = new Date().toISOString().split('T')[0];
    const dateStr  = date.toISOString().split('T')[0];
    return dateStr > todayStr;
  }

  // Update right-arrow disabled state based on current date
  function updateArrowStates() {
    const rightArrow = document.querySelector('.arrow:last-child');
    if (!rightArrow) return;

    const isToday = isDateTodayOrFuture(currentDate) && !isDateInFuture(currentDate);
    if (isToday) {
      rightArrow.classList.add('disabled');
      rightArrow.setAttribute('aria-disabled', 'true');
      rightArrow.title = 'Cannot navigate to future dates';
    } else {
      rightArrow.classList.remove('disabled');
      rightArrow.removeAttribute('aria-disabled');
      rightArrow.title = '';
    }
  }

  arrows.forEach((arrow) => {
    arrow.addEventListener("click", (e) => {
      // Ignore if disabled
      if (e.target.classList.contains('disabled')) return;

      // Check completion vs. in-progress
      const isGameComplete = document.querySelector('.game-over-message') !== null;
      const isGameInProgress = !isGameComplete && (
        document.querySelectorAll('#clues-list li.found').length > 0 ||
        document.querySelectorAll('.letter-tile.purchased').length > 0 ||
        document.querySelectorAll('.letter-tile.selected').length > 0
      );

      if (isGameInProgress) {
        if (!confirm("Changing the date will reset your current game progress. Continue?")) {
          return;
        }
      }

      const newDate = new Date(currentDate);
      const isLeft  = e.target.textContent.includes("←");

      if (isLeft) {
        newDate.setDate(newDate.getDate() - 1);
      } else {
        // Block navigating forward from today
        if (isDateTodayOrFuture(currentDate) && !isDateInFuture(currentDate)) return;
        newDate.setDate(newDate.getDate() + 1);
      }

      currentDate = newDate;
      updateDateDisplay(currentDate);
      setDateInUrl(currentDate);
      cal.setSelectedDate(currentDate); // Keep calendar in sync
      updateArrowStates();

      console.log(`Navigated to date: ${currentDate.toISOString().split('T')[0]}`);
      initializeGame();
    });
  });

  // Initialize arrow states on load
  updateArrowStates();
};

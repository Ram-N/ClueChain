// Main entry point for ParaSight
import { initializeGame, getAvailableDates } from "./js/game-controller.js?v=1.1";
import { setupHelpButton } from "./assets/js/help-modal.js";

// Initialize the game when the window loads
window.onload = async () => {
  // Set the date display to today's date on page load
  const dateElementInit = document.getElementById("current-date");
  if (dateElementInit) {
    const today = new Date();
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    // Fix: use correct type for year/month/day
    dateElementInit.textContent = today.toLocaleDateString('en-US', {
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
  const helpButton = document.getElementById("help-button");
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
  
  // Set up custom calendar
  const calendarButton = document.getElementById("calendar-button");
  const dateSelector = document.querySelector(".date-selector");
  const customCalendar = document.getElementById("custom-calendar");
  const monthYearDisplay = document.getElementById("month-year");
  const prevMonthBtn = document.getElementById("prev-month");
  const nextMonthBtn = document.getElementById("next-month");
  const calendarDaysContainer = document.getElementById("calendar-days");
  
  // Calendar state variables
  let calendarCurrentDate = new Date(currentDate);
  let calendarCurrentMonth = calendarCurrentDate.getMonth();
  let calendarCurrentYear = calendarCurrentDate.getFullYear();
  
  // Days with content - we'll fetch this from our data later
  const daysWithContent = [];

  // Play history: "YYYY-MM-DD" → score (populated when calendar opens)
  let playedDates = {};

  async function loadPlayHistory() {
    if (!window.authManager || !window.authManager.isAuthenticated()) return;
    console.log('📅 loadPlayHistory: fetching activity history...');
    const result = await window.streakTracker.getActivityHistory({ limit: 365 });
    console.log('📅 loadPlayHistory result:', result);
    if (!result.success) {
      console.error('❌ Failed to load play history:', result.error);
      return;
    }
    playedDates = {};
    result.activities.forEach(a => {
      const pct = a.max_possible_score > 0
        ? Math.round((a.score / a.max_possible_score) * 100)
        : a.score;
      console.log(`📅  ${a.activity_date}: raw=${a.score}, max=${a.max_possible_score}, pct=${pct}`);
      playedDates[a.activity_date] = pct;
    });
    console.log('📅 playedDates after load:', playedDates);

    // Re-render the calendar if it's currently visible
    if (customCalendar.classList.contains('show')) {
      renderCalendarDays();
    }
  }

  // Expose loadPlayHistory globally so it can be called after game completion
  window.loadPlayHistory = loadPlayHistory;

  function getScoreDotClass(score) {
    if (score >= 80) return "played-green";
    if (score >= 50) return "played-yellow";
    return "played-red";
  }
  
  // Build content dates from the already-loaded index (no network requests needed)
  function buildContentDates() {
    const files = getAvailableDates();
    files.forEach(file => {
      const m = file.match(/\/(\d{2}-\d{2})-/);
      if (m) daysWithContent.push(m[1]);
    });
  }

  // Load a specific date's puzzle file and reinitialize the game
  async function loadParagraphForDate(mmDD) {
    const files = getAvailableDates();
    const targetFile = files.find(file => file.includes(`/assets/data/${mmDD}-`));
    if (!targetFile) {
      console.log(`No puzzle file found for ${mmDD}`);
      initializeGame();
      return;
    }
    // The game-controller reads the date display element to pick the file;
    // updateDateDisplay already set it before this call, so just reinitialize.
    initializeGame();
  }
  
  // Function to generate and render calendar days
  function renderCalendarDays() {
    calendarDaysContainer.innerHTML = "";

    // Update month and year display
    monthYearDisplay.textContent = new Date(calendarCurrentYear, calendarCurrentMonth, 1)
      .toLocaleDateString("en-US", { month: "long", year: "numeric" });

    // Enforce 60-day history window
    const minDate = new Date();
    minDate.setDate(minDate.getDate() - 60);
    const minDateStr = `${minDate.getFullYear()}-${String(minDate.getMonth() + 1).padStart(2, '0')}-${String(minDate.getDate()).padStart(2, '0')}`;
    const minYear = minDate.getFullYear();
    const minMonth = minDate.getMonth();
    if (prevMonthBtn) {
      prevMonthBtn.disabled = (calendarCurrentYear < minYear) ||
        (calendarCurrentYear === minYear && calendarCurrentMonth <= minMonth);
    }
    
    // Get the first day of the month
    const firstDay = new Date(calendarCurrentYear, calendarCurrentMonth, 1);
    const startingDay = firstDay.getDay(); // 0 (Sunday) to 6 (Saturday)
    
    // Get the last day of the month
    const lastDay = new Date(calendarCurrentYear, calendarCurrentMonth + 1, 0);
    const totalDays = lastDay.getDate();
    
    // Create empty cells for days before the first day of month
    for (let i = 0; i < startingDay; i++) {
      const emptyDay = document.createElement("div");
      emptyDay.className = "calendar-day empty";
      calendarDaysContainer.appendChild(emptyDay);
    }
    
    // Format current selected date for comparison
    const selectedDateStr = currentDate.toISOString().split('T')[0];
    const todayDateStr = new Date().toISOString().split('T')[0];
    
    // Create cells for all days of the month
    for (let day = 1; day <= totalDays; day++) {
      const dayElement = document.createElement("div");
      dayElement.className = "calendar-day";
      dayElement.textContent = day;
      
      // Format this calendar day as YYYY-MM-DD for comparison
      // Use local date parts directly to avoid UTC timezone shift
      const thisDate = new Date(calendarCurrentYear, calendarCurrentMonth, day);
      const thisDateStr = `${calendarCurrentYear}-${String(calendarCurrentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      
      // Add special classes
      if (thisDateStr === selectedDateStr) {
        dayElement.classList.add("selected");
      }
      
      if (thisDateStr === todayDateStr) {
        dayElement.classList.add("today");
      }
      
      // Check if this date is in the future or too old (outside 60-day window)
      const isFutureDate = thisDateStr > todayDateStr;
      const isTooOld = thisDateStr < minDateStr;

      // Extract MM-DD from this date for year-agnostic matching
      const mmDD = thisDateStr.substring(5); // Get MM-DD from YYYY-MM-DD

      // Mark days that have content and handle clickability
      // Check both full date (YYYY-MM-DD) and year-agnostic (MM-DD)
      if (daysWithContent.includes(thisDateStr) || daysWithContent.includes(mmDD)) {
        dayElement.classList.add("has-content");

        // If it's a future date, disable it
        if (isFutureDate) {
          dayElement.classList.add("future-date");
          dayElement.title = "Cannot access future dates";
        } else if (isTooOld) {
          dayElement.classList.add("too-old");
          dayElement.title = "Only the last 60 days are available";
        } else {
          // Add click handler to select date (only for dates with content and not in future)
          dayElement.addEventListener("click", () => {
          // More comprehensive check if game is in progress
          const isGameInProgress = document.querySelectorAll('#clues-list li.found').length > 0 ||
                                   document.querySelectorAll('.letter-tile.purchased').length > 0 ||
                                   document.querySelectorAll('.letter-tile.selected').length > 0;

          const clickedMmDD = `${String(calendarCurrentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

          if (isGameInProgress) {
            // Ask for confirmation before changing date and resetting game
            if (confirm("Changing the date will reset your current game progress. Continue?")) {
              currentDate = new Date(calendarCurrentYear, calendarCurrentMonth, day);
              updateDateDisplay(currentDate);
              console.log(`Selected date: ${currentDate.toISOString().split('T')[0]}`);
              customCalendar.classList.remove("show");
              loadParagraphForDate(clickedMmDD);
              updateArrowStates();
            }
          } else {
            // No game in progress, proceed without confirmation
            currentDate = new Date(calendarCurrentYear, calendarCurrentMonth, day);
            updateDateDisplay(currentDate);
            console.log(`Selected date: ${currentDate.toISOString().split('T')[0]}`);
            customCalendar.classList.remove("show");
            loadParagraphForDate(clickedMmDD);
            updateArrowStates();
          }
        });
        }
      } else {
        // For dates without content, add a class to show they're not clickable
        dayElement.classList.add("no-content");
      }
      
      // Apply score color to the entire date circle for played days (authenticated users only)
      if (playedDates.hasOwnProperty(thisDateStr)) {
        const score = playedDates[thisDateStr];
        dayElement.classList.add(getScoreDotClass(score));
        dayElement.title = `Score: ${score}%`;
      }

      calendarDaysContainer.appendChild(dayElement);
    }
  }

  // Function to show/hide calendar
  function toggleCalendar() {
    const isVisible = customCalendar.classList.toggle("show");
    
    if (isVisible) {
      // Set calendar to current month/year and render days
      calendarCurrentMonth = currentDate.getMonth();
      calendarCurrentYear = currentDate.getFullYear();
      renderCalendarDays();
      loadPlayHistory().then(() => renderCalendarDays());
      
      // Build content dates from already-loaded index (no network requests)
      if (daysWithContent.length === 0) {
        buildContentDates();
        renderCalendarDays();
      }
      
      // Add click outside to close
      setTimeout(() => {
        document.addEventListener("click", closeCalendarOnClickOutside);
      }, 10);
    }
  }
  
  // Function to close calendar when clicking outside
  function closeCalendarOnClickOutside(e) {
    if (!customCalendar.contains(e.target) && 
        !dateSelector.contains(e.target)) {
      customCalendar.classList.remove("show");
      document.removeEventListener("click", closeCalendarOnClickOutside);
    }
  }
  
  // Set up event listeners for the calendar
  if (dateSelector && customCalendar) {
    // Toggle calendar on date or button click
    dateSelector.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleCalendar();
    });
    
    // Navigate to previous month
    if (prevMonthBtn) {
      prevMonthBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        calendarCurrentMonth--;
        if (calendarCurrentMonth < 0) {
          calendarCurrentMonth = 11;
          calendarCurrentYear--;
        }
        renderCalendarDays();
      });
    }
    
    // Navigate to next month
    if (nextMonthBtn) {
      nextMonthBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        calendarCurrentMonth++;
        if (calendarCurrentMonth > 11) {
          calendarCurrentMonth = 0;
          calendarCurrentYear++;
        }
        renderCalendarDays();
      });
    }
    
  }

  // Helper function to check if a date is today or in the future
  function isDateTodayOrFuture(date) {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    const dateStr = date.toISOString().split('T')[0];
    return dateStr >= todayStr;
  }

  // Helper function to check if a date is in the future
  function isDateInFuture(date) {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    const dateStr = date.toISOString().split('T')[0];
    return dateStr > todayStr;
  }

  // Function to update arrow states based on current date
  function updateArrowStates() {
    const leftArrow = document.querySelector('.arrow:first-child');
    const rightArrow = document.querySelector('.arrow:last-child');
    
    if (rightArrow) {
      const isCurrentDateToday = isDateTodayOrFuture(currentDate) && !isDateInFuture(currentDate);
      
      if (isCurrentDateToday) {
        rightArrow.classList.add('disabled');
        rightArrow.setAttribute('aria-disabled', 'true');
        rightArrow.title = 'Cannot navigate to future dates';
      } else {
        rightArrow.classList.remove('disabled');
        rightArrow.removeAttribute('aria-disabled');
        rightArrow.title = '';
      }
    }
  }

  // Add date navigation handlers
  arrows.forEach((arrow) => {
    arrow.addEventListener("click", (e) => {
      // Check if the arrow is disabled
      if (e.target.classList.contains('disabled')) {
        return;
      }

      // Check if game is complete (victory message shown)
      const isGameComplete = document.querySelector('.game-over-message') !== null;
      
      // Check if game is in progress (but not complete)
      const isGameInProgress = !isGameComplete && (
        document.querySelectorAll('#clues-list li.found').length > 0 || 
        document.querySelectorAll('.letter-tile.purchased').length > 0 ||
        document.querySelectorAll('.letter-tile.selected').length > 0
      );
      
      // Only ask for confirmation if game is in progress but not complete
      if (isGameInProgress) {
        if (!confirm("Changing the date will reset your current game progress. Continue?")) {
          return; // Cancel if user doesn't confirm
        }
      }
      
      const newDate = new Date(currentDate);
      const isLeft = e.target.textContent.includes("←");

      if (isLeft) {
        newDate.setDate(newDate.getDate() - 1);
      } else {
        // Additional check to prevent future navigation
        if (isDateTodayOrFuture(currentDate) && !isDateInFuture(currentDate)) {
          return; // Don't allow navigation to future from today
        }
        newDate.setDate(newDate.getDate() + 1);
      }

      currentDate = newDate;
      updateDateDisplay(currentDate);
      updateArrowStates();
      
      // Log the navigated date for debugging
      const dateStr = currentDate.toISOString().split('T')[0];
      console.log(`Navigated to date: ${dateStr}`);
      
      // Reinitialize game with new date
      initializeGame();
    });
  });
  
  // Initialize arrow states after setting up navigation
  updateArrowStates();
};

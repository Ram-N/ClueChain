/**
 * DailyCalendar — reusable daily-puzzle calendar widget.
 *
 * Usage:
 *   import { DailyCalendar } from './assets/js/daily-calendar.js';
 *
 *   const cal = new DailyCalendar({
 *     // Required
 *     onDateSelect:      (mmdd, date) => loadPuzzleForDate(mmdd),
 *     isGameInProgress:  () => checkIfGameActive(),
 *
 *     // Optional: authenticated score history
 *     getPlayHistory:    async () => { return { "2026-09-28": 95, ... }; },
 *
 *     // Optional: which dates have puzzles (lazily fetched if omitted initially)
 *     getAvailableDates: () => gameState.config.availableDates,  // MMDD strings like "0929"
 *
 *     // Optional config
 *     historyWindowDays: 60,
 *     scoreThresholds:   { green: 80, yellow: 50 },
 *   });
 *
 * Public API:
 *   cal.toggle()
 *   cal.open()
 *   cal.close()
 *   cal.setSelectedDate(date)  — sync when host navigates via arrow keys
 *   cal.refreshPlayHistory()   — re-fetch history after game completion
 */
export class DailyCalendar {
  constructor(options = {}) {
    // Required callbacks
    this._onDateSelect    = options.onDateSelect    ?? (() => {});
    this._isGameInProgress = options.isGameInProgress ?? (() => false);

    // Optional callbacks
    this._getPlayHistory   = options.getPlayHistory   ?? null;
    this._getAvailableDates = options.getAvailableDates ?? null;

    // Config
    this._historyWindowDays = options.historyWindowDays ?? 60;
    this._scoreThresholds   = options.scoreThresholds   ?? { green: 80, yellow: 50 };

    // Internal state
    this._selectedDate   = new Date();
    this._displayMonth   = this._selectedDate.getMonth();
    this._displayYear    = this._selectedDate.getFullYear();
    this._playedDates    = {};
    this._daysWithContent = [];  // MM-DD strings like "09-29"

    // DOM refs
    this._container   = document.getElementById('custom-calendar');
    this._dateSelector = document.querySelector('.date-selector');
    this._monthYearEl  = document.getElementById('month-year');
    this._prevBtn      = document.getElementById('prev-month');
    this._nextBtn      = document.getElementById('next-month');
    this._daysEl       = document.getElementById('calendar-days');
    this._todayBtn     = document.getElementById('today-button');

    this._boundOutsideClick = this._closeOnOutsideClick.bind(this);

    this._attachListeners();
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /** Sync the highlighted selected date (e.g. after arrow navigation). */
  setSelectedDate(date) {
    this._selectedDate = new Date(date);
    if (this._isOpen()) {
      this._displayMonth = this._selectedDate.getMonth();
      this._displayYear  = this._selectedDate.getFullYear();
      this._render();
    }
  }

  /** Re-fetch and redraw play history (call after game completion). */
  async refreshPlayHistory() {
    if (!this._getPlayHistory) return;
    const history = await this._getPlayHistory();
    if (history) {
      this._playedDates = history;
      if (this._isOpen()) this._render();
    }
  }

  toggle() {
    this._isOpen() ? this.close() : this.open();
  }

  open() {
    this._displayMonth = this._selectedDate.getMonth();
    this._displayYear  = this._selectedDate.getFullYear();

    // Populate content dates lazily on first open
    if (this._daysWithContent.length === 0 && this._getAvailableDates) {
      this._buildContentDates(this._getAvailableDates());
    }

    this._container.classList.add('show');
    this._render();

    // Async: load play history and re-render
    if (this._getPlayHistory) {
      this._getPlayHistory().then(history => {
        if (history && this._isOpen()) {
          this._playedDates = history;
          this._render();
        }
      });
    }

    setTimeout(() => {
      document.addEventListener('click', this._boundOutsideClick);
    }, 10);
  }

  close() {
    this._container.classList.remove('show');
    document.removeEventListener('click', this._boundOutsideClick);
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  _isOpen() {
    return this._container?.classList.contains('show') ?? false;
  }

  /** Build MM-DD content list from MMDD strings (e.g. "0929" → "09-29"). */
  _buildContentDates(rawDates) {
    this._daysWithContent = [];
    rawDates.forEach(key => {
      if (/^\d{4}$/.test(key)) {
        this._daysWithContent.push(`${key.slice(0, 2)}-${key.slice(2)}`);
      } else {
        // Already MM-DD or YYYY-MM-DD — accept as-is
        this._daysWithContent.push(key);
      }
    });
  }

  /** YYYY-MM-DD string from a Date, using local time (avoids UTC shift). */
  _toDateStr(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  /** MM-DD string for the onDateSelect callback. */
  _toMmDD(date) {
    return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  _getScoreDotClass(score) {
    if (score >= this._scoreThresholds.green)  return 'played-green';
    if (score >= this._scoreThresholds.yellow) return 'played-yellow';
    return 'played-red';
  }

  _closeOnOutsideClick(e) {
    if (!this._container.contains(e.target) && !this._dateSelector?.contains(e.target)) {
      this.close();
    }
  }

  _attachListeners() {
    // Toggle on date-selector click
    if (this._dateSelector) {
      this._dateSelector.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggle();
      });
    }

    // Previous month
    if (this._prevBtn) {
      this._prevBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this._displayMonth--;
        if (this._displayMonth < 0) {
          this._displayMonth = 11;
          this._displayYear--;
        }
        this._render();
      });
    }

    // Next month
    if (this._nextBtn) {
      this._nextBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this._displayMonth++;
        if (this._displayMonth > 11) {
          this._displayMonth = 0;
          this._displayYear++;
        }
        this._render();
      });
    }

    // Today button
    if (this._todayBtn) {
      this._todayBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const today = new Date();
        if (this._toDateStr(today) === this._toDateStr(this._selectedDate)) {
          this.close();
          return;
        }
        if (this._isGameInProgress() &&
            !confirm('Changing the date will reset your current game progress. Continue?')) {
          return;
        }
        this._selectedDate = today;
        this.close();
        this._onDateSelect(this._toMmDD(today), today);
      });
    }
  }

  _render() {
    if (!this._daysEl || !this._monthYearEl) return;

    this._daysEl.innerHTML = '';
    this._monthYearEl.textContent = new Date(this._displayYear, this._displayMonth, 1)
      .toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const today   = new Date();
    const todayStr = this._toDateStr(today);

    // Compute history-window boundary
    const minDate = new Date();
    minDate.setDate(minDate.getDate() - this._historyWindowDays);
    const minDateStr = this._toDateStr(minDate);

    // Disable prev-month button at the history boundary
    if (this._prevBtn) {
      this._prevBtn.disabled =
        (this._displayYear < minDate.getFullYear()) ||
        (this._displayYear === minDate.getFullYear() && this._displayMonth <= minDate.getMonth());
    }

    const selectedStr = this._toDateStr(this._selectedDate);

    // Leading empty cells
    const firstDayOfWeek = new Date(this._displayYear, this._displayMonth, 1).getDay();
    for (let i = 0; i < firstDayOfWeek; i++) {
      const empty = document.createElement('div');
      empty.className = 'calendar-day empty';
      this._daysEl.appendChild(empty);
    }

    const totalDays = new Date(this._displayYear, this._displayMonth + 1, 0).getDate();

    for (let day = 1; day <= totalDays; day++) {
      const el = document.createElement('div');
      el.className = 'calendar-day';
      el.textContent = day;

      const mm   = String(this._displayMonth + 1).padStart(2, '0');
      const dd   = String(day).padStart(2, '0');
      const thisDateStr = `${this._displayYear}-${mm}-${dd}`;
      const mmDD = `${mm}-${dd}`;

      if (thisDateStr === selectedStr) el.classList.add('selected');
      if (thisDateStr === todayStr)    el.classList.add('today');

      const isFuture = thisDateStr > todayStr;
      const isTooOld = thisDateStr < minDateStr;
      const hasContent = this._daysWithContent.includes(thisDateStr) ||
                         this._daysWithContent.includes(mmDD);

      if (hasContent) {
        el.classList.add('has-content');
        if (isFuture) {
          el.classList.add('future-date');
          el.title = 'Cannot access future dates';
        } else if (isTooOld) {
          el.classList.add('too-old');
          el.title = `Only the last ${this._historyWindowDays} days are available`;
        } else {
          el.addEventListener('click', () => {
            if (this._isGameInProgress() &&
                !confirm('Changing the date will reset your current game progress. Continue?')) {
              return;
            }
            this._selectedDate = new Date(this._displayYear, this._displayMonth, day);
            this.close();
            this._onDateSelect(mmDD, this._selectedDate);
          });
        }
      } else {
        el.classList.add('no-content');
      }

      // Score color (authenticated users)
      if (Object.prototype.hasOwnProperty.call(this._playedDates, thisDateStr)) {
        el.classList.add(this._getScoreDotClass(this._playedDates[thisDateStr]));
        el.title = `Score: ${this._playedDates[thisDateStr]}%`;
      }

      this._daysEl.appendChild(el);
    }
  }
}

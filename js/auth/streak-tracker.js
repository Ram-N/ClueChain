/**
 * @fileoverview Streak tracking functionality for ClueChain
 * Handles recording game activities and managing user streaks
 */

// ---------------------------------------------------------------------------
// Private helpers (mirrors streak.js — kept here because streak-tracker.js
// is a plain <script>, not an ES module, and cannot import streak.js)
// ---------------------------------------------------------------------------

function _localDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function _yesterdayKey(todayKey) {
  const [y, m, d] = todayKey.split('-').map(Number)
  const noon = new Date(y, m - 1, d, 12, 0, 0)
  noon.setDate(noon.getDate() - 1)
  return _localDateKey(noon)
}

// ---------------------------------------------------------------------------

class StreakTracker {
  constructor() {
    this.supabase = null;
    this.initialized = false;
    this.activityTypes = {
      GAME_COMPLETED: 'game_completed',
      GAME_STARTED: 'game_started'
    };
  }

  /**
   * Initialize the streak tracker
   * @returns {Promise<void>}
   */
  async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      this.supabase = window.SupabaseClient.get();
      this.initialized = true;
      console.log('✅ StreakTracker initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize StreakTracker:', error);
      throw error;
    }
  }

  /**
   * Record a game activity
   * @param {string} activityType - Type of activity
   * @param {Object} gameData - Game data
   * @returns {Promise<Object>} Recording result
   */
  async recordActivity(activityType, gameData = {}) {
    if (!this.initialized) {
      await this.initialize();
    }

    if (!window.authManager.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      const user = window.authManager.getCurrentUser();
      const today = _localDateKey(new Date());
      const gameDateToUse = gameData.gameDate || today;

      const activityData = {
        user_id: user.id,
        activity_type: activityType,
        activity_date: today,     // Always today — streak = consecutive days you played
        game_date: gameDateToUse, // The puzzle date (for calendar display)
        score: gameData.score || 0,
        max_possible_score: gameData.maxPossibleScore || 0,
        words_found: gameData.wordsFound || 0,
        total_words: gameData.totalWords || 0,
        completion_time_seconds: gameData.completionTime || null,
        metadata: {
          timestamp: new Date().toISOString(),
          ...gameData.metadata
        }
      };

      const { data, error } = await this.supabase
        .from('user_activities')
        .insert([activityData])
        .select()
        .single();

      if (error) {
        // If it's a duplicate activity (same day), that's okay
        if (error.code === '23505') {
          console.log('📝 Activity already recorded for today');
          return { success: true, message: 'Activity already recorded for today' };
        }
        throw error;
      }

      console.log('✅ Activity recorded successfully:', data);
      return { success: true, activity: data };
    } catch (error) {
      console.error('❌ Failed to record activity:', error);
      return { success: false, error };
    }
  }

  /**
   * Record game completion
   * @param {Object} gameData - Game completion data
   * @returns {Promise<Object>} Recording result
   */
  async recordGameCompletion(gameData) {
    const result = await this.recordActivity(this.activityTypes.GAME_COMPLETED, gameData);
    // Refresh streak display in UI after recording
    if (window.authUI) {
      window.authUI.loadUserStreak();
    }
    return result;
  }

  /**
   * Get current streak for user
   * @param {string} activityType - Type of activity
   * @returns {Promise<Object>} Streak data
   */
  async getCurrentStreak(activityType = this.activityTypes.GAME_COMPLETED) {
    if (!this.initialized) {
      await this.initialize();
    }

    if (!window.authManager.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      // Calculate streak directly from activity history
      const result = await this.getActivityHistory({ activityType, limit: 365 });
      if (!result.success) throw result.error;

      const streak = this.calculateStreakFromActivities(result.activities);
      return { success: true, streak };
    } catch (error) {
      console.error('❌ Failed to get current streak:', error);
      return { success: false, error };
    }
  }

  /**
   * Get user activity history
   * @param {Object} options - Query options
   * @returns {Promise<Object>} Activity history
   */
  async getActivityHistory(options = {}) {
    if (!this.initialized) {
      await this.initialize();
    }

    if (!window.authManager.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      const user = window.authManager.getCurrentUser();
      const {
        activityType = this.activityTypes.GAME_COMPLETED,
        limit = 30,
        offset = 0,
        startDate = null,
        endDate = null
      } = options;

      let query = this.supabase
        .from('user_activities')
        .select('*')
        .eq('user_id', user.id)
        .eq('activity_type', activityType)
        .order('activity_date', { ascending: false })
        .range(offset, offset + limit - 1);

      if (startDate) {
        query = query.gte('activity_date', startDate);
      }

      if (endDate) {
        query = query.lte('activity_date', endDate);
      }

      const { data, error } = await query;

      if (error) {
        throw error;
      }

      return { success: true, activities: data };
    } catch (error) {
      console.error('❌ Failed to get activity history:', error);
      return { success: false, error };
    }
  }

  /**
   * Check if user has played today
   * @param {string} activityType - Type of activity
   * @returns {Promise<Object>} Check result
   */
  async hasPlayedToday(activityType = this.activityTypes.GAME_COMPLETED) {
    if (!this.initialized) {
      await this.initialize();
    }

    if (!window.authManager.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      const user = window.authManager.getCurrentUser();
      const today = _localDateKey(new Date()); // local date, not UTC

      const { data, error } = await this.supabase
        .from('user_activities')
        .select('id')
        .eq('user_id', user.id)
        .eq('activity_type', activityType)
        .eq('activity_date', today)
        .single();

      if (error) {
        // If no record found, user hasn't played today
        if (error.code === 'PGRST116') {
          return { success: true, hasPlayed: false };
        }
        throw error;
      }

      return { success: true, hasPlayed: true };
    } catch (error) {
      console.error('❌ Failed to check if user played today:', error);
      return { success: false, error };
    }
  }

  /**
   * Calculate streak from raw activity data
   * @param {Array} activities - Array of activity records
   * @returns {Object} Calculated streak information
   */
  calculateStreakFromActivities(activities) {
    if (!activities || activities.length === 0) {
      return {
        current_streak: 0,
        longest_streak: 0,
        last_activity_date: null
      };
    }

    // Sort activities by date string (newest first) — lexicographic order is correct for YYYY-MM-DD
    const sortedActivities = activities.sort((a, b) =>
      b.activity_date.localeCompare(a.activity_date)
    );

    // Deduplicate by date string (multiple activities on same day count as one)
    const uniqueDates = [...new Set(sortedActivities.map(a => a.activity_date))];

    let currentStreak = 0;
    let longestStreak = 0;
    let tempStreak = 0;
    let lastDateStr = null;

    for (let i = 0; i < uniqueDates.length; i++) {
      if (lastDateStr === null) {
        tempStreak = 1;
        lastDateStr = uniqueDates[i];
      } else {
        // Calendar-safe consecutive check: is uniqueDates[i] the day before lastDateStr?
        const isConsecutive = uniqueDates[i] === _yesterdayKey(lastDateStr);

        if (isConsecutive) {
          tempStreak++;
        } else {
          longestStreak = Math.max(longestStreak, tempStreak);
          tempStreak = 1;
        }

        lastDateStr = uniqueDates[i];
      }
    }

    // Check if current streak is still active (most recent activity is today or yesterday)
    const todayStr = _localDateKey(new Date());
    const mostRecentStr = uniqueDates[0];
    const stillActive = mostRecentStr === todayStr || mostRecentStr === _yesterdayKey(todayStr);

    if (stillActive) {
      currentStreak = tempStreak;
    } else {
      currentStreak = 0;
    }

    longestStreak = Math.max(longestStreak, tempStreak);

    return {
      current_streak: currentStreak,
      longest_streak: longestStreak,
      last_activity_date: sortedActivities[0].activity_date
    };
  }
}

// Create global instance
window.streakTracker = new StreakTracker();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StreakTracker;
}

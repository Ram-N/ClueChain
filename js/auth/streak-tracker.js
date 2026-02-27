/**
 * @fileoverview Streak tracking functionality for ClueChain
 * Handles recording game activities and managing user streaks
 */

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
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
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
   * Record game start
   * @param {Object} gameData - Game start data
   * @returns {Promise<Object>} Recording result
   */
  async recordGameStart(gameData) {
    return this.recordActivity(this.activityTypes.GAME_STARTED, gameData);
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
      const today = new Date().toISOString().split('T')[0];

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
   * Get streak statistics
   * @returns {Promise<Object>} Streak statistics
   */
  async getStreakStatistics() {
    if (!this.initialized) {
      await this.initialize();
    }

    if (!window.authManager.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      const user = window.authManager.getCurrentUser();
      
      const { data, error } = await this.supabase
        .from('user_streaks')
        .select('*')
        .eq('user_id', user.id);

      if (error) {
        throw error;
      }

      // Calculate additional statistics
      const stats = {
        totalActivities: data.length,
        streaks: data,
        gameCompletion: data.find(s => s.activity_type === this.activityTypes.GAME_COMPLETED),
        gameStart: data.find(s => s.activity_type === this.activityTypes.GAME_STARTED)
      };

      return { success: true, statistics: stats };
    } catch (error) {
      console.error('❌ Failed to get streak statistics:', error);
      return { success: false, error };
    }
  }

  /**
   * Calculate streak from raw activity data (useful for validation)
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

    // Parse YYYY-MM-DD as local date (avoids UTC midnight timezone shift)
    const parseLocalDate = (dateStr) => {
      const [y, m, d] = dateStr.split('-').map(Number);
      return new Date(y, m - 1, d);
    };

    // Sort activities by date (newest first)
    const sortedActivities = activities.sort((a, b) =>
      parseLocalDate(b.activity_date) - parseLocalDate(a.activity_date)
    );

    // Deduplicate by date string (multiple activities on same day count as one)
    const uniqueDates = [...new Set(sortedActivities.map(a => a.activity_date))];

    let currentStreak = 0;
    let longestStreak = 0;
    let tempStreak = 0;
    let lastDate = null;

    for (let i = 0; i < uniqueDates.length; i++) {
      const activityDate = parseLocalDate(uniqueDates[i]);

      if (lastDate === null) {
        // First activity
        tempStreak = 1;
        lastDate = activityDate;
      } else {
        const daysDiff = Math.round((lastDate - activityDate) / (1000 * 60 * 60 * 24));

        if (daysDiff === 1) {
          // Consecutive day
          tempStreak++;
        } else {
          // Streak broken
          longestStreak = Math.max(longestStreak, tempStreak);
          tempStreak = 1;
        }

        lastDate = activityDate;
      }
    }

    // Check if current streak is still active
    // Compare today's local date against most recent activity date string
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const mostRecentStr = uniqueDates[0];
    const mostRecentDate = parseLocalDate(mostRecentStr);
    const todayDate = parseLocalDate(todayStr);
    const daysSinceLastActivity = Math.round((todayDate - mostRecentDate) / (1000 * 60 * 60 * 24));

    if (daysSinceLastActivity <= 1) {
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
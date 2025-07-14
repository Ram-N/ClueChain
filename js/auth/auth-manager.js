/**
 * @fileoverview Authentication manager for ClueChain
 * Handles user authentication, session management, and auth state changes
 */

class AuthManager {
  constructor() {
    this.supabase = null;
    this.currentUser = null;
    this.authListeners = new Set();
    this.initialized = false;
  }

  /**
   * Initialize the authentication manager
   * @returns {Promise<void>}
   */
  async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      this.supabase = window.SupabaseClient.get();
      
      // Check if we're returning from OAuth
      console.log('🔄 Current URL:', window.location.href);
      console.log('🔄 URL hash:', window.location.hash);
      console.log('🔄 URL search:', window.location.search);
      
      // Set up auth state listener
      this.supabase.auth.onAuthStateChange((event, session) => {
        this.handleAuthStateChange(event, session);
      });

      // Get initial session
      console.log('🔄 Getting initial session...');
      const { data: { session }, error } = await this.supabase.auth.getSession();
      console.log('🔄 Initial session result:', { session, error });
      
      if (session) {
        console.log('✅ Found existing session:', session.user.email);
        this.currentUser = session.user;
        this.notifyAuthListeners('INITIAL_SESSION', session);
      } else {
        console.log('❌ No existing session found');
      }

      // Check database schema
      console.log('🔍 Checking database schema...');
      await window.SupabaseClient.checkDatabaseSchema();
      await window.SupabaseClient.testUserCreation();

      this.initialized = true;
      console.log('✅ AuthManager initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize AuthManager:', error);
      throw error;
    }
  }

  /**
   * Handle authentication state changes
   * @param {string} event - Auth event type
   * @param {Object} session - Session data
   * @private
   */
  handleAuthStateChange(event, session) {
    console.log('🔄 Auth state changed:', event, session?.user?.email);
    
    switch (event) {
      case 'SIGNED_IN':
        this.currentUser = session.user;
        this.notifyAuthListeners('SIGNED_IN', session);
        break;
      case 'SIGNED_OUT':
        this.currentUser = null;
        this.notifyAuthListeners('SIGNED_OUT', null);
        break;
      case 'TOKEN_REFRESHED':
        this.currentUser = session.user;
        this.notifyAuthListeners('TOKEN_REFRESHED', session);
        break;
      case 'USER_UPDATED':
        this.currentUser = session.user;
        this.notifyAuthListeners('USER_UPDATED', session);
        break;
    }
  }

  /**
   * Sign in with Google OAuth
   * @param {Object} options - Sign in options
   * @returns {Promise<Object>} Auth result
   */
  async signInWithGoogle(options = {}) {
    console.log('🔄 signInWithGoogle called with options:', options);
    console.log('🔄 Current window location:', window.location.origin);
    
    try {
      console.log('🔄 About to call supabase.auth.signInWithOAuth...');
      
      const { data, error } = await this.supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          ...options
        }
      });

      console.log('🔄 signInWithOAuth returned:', { data, error });

      if (error) {
        console.error('❌ OAuth error:', error);
        throw error;
      }

      console.log('✅ OAuth success:', data);
      return { success: true, data };
    } catch (error) {
      console.error('❌ Google sign in failed:', error);
      return { success: false, error };
    }
  }

  /**
   * Sign out current user
   * @returns {Promise<Object>} Sign out result
   */
  async signOut() {
    try {
      const { error } = await this.supabase.auth.signOut();
      
      if (error) {
        throw error;
      }

      return { success: true };
    } catch (error) {
      console.error('❌ Sign out failed:', error);
      return { success: false, error };
    }
  }

  /**
   * Get current user
   * @returns {Object|null} Current user or null
   */
  getCurrentUser() {
    return this.currentUser;
  }

  /**
   * Check if user is authenticated
   * @returns {boolean} Authentication status
   */
  isAuthenticated() {
    return this.currentUser !== null;
  }

  /**
   * Get current session
   * @returns {Promise<Object>} Current session
   */
  async getCurrentSession() {
    try {
      const { data: { session }, error } = await this.supabase.auth.getSession();
      
      if (error) {
        throw error;
      }

      return { success: true, session };
    } catch (error) {
      console.error('❌ Failed to get current session:', error);
      return { success: false, error };
    }
  }

  /**
   * Add authentication state listener
   * @param {Function} listener - Callback function
   */
  addAuthListener(listener) {
    this.authListeners.add(listener);
  }

  /**
   * Remove authentication state listener
   * @param {Function} listener - Callback function
   */
  removeAuthListener(listener) {
    this.authListeners.delete(listener);
  }

  /**
   * Notify all auth listeners
   * @param {string} event - Event type
   * @param {Object} data - Event data
   * @private
   */
  notifyAuthListeners(event, data) {
    this.authListeners.forEach(listener => {
      try {
        listener(event, data);
      } catch (error) {
        console.error('❌ Auth listener error:', error);
      }
    });
  }

  /**
   * Get user profile data
   * @returns {Promise<Object>} User profile
   */
  async getUserProfile() {
    if (!this.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      const { data, error } = await this.supabase
        .from('profiles')
        .select('*')
        .eq('id', this.currentUser.id)
        .single();

      if (error) {
        throw error;
      }

      return { success: true, profile: data };
    } catch (error) {
      console.error('❌ Failed to get user profile:', error);
      return { success: false, error };
    }
  }

  /**
   * Update user profile
   * @param {Object} updates - Profile updates
   * @returns {Promise<Object>} Update result
   */
  async updateUserProfile(updates) {
    if (!this.isAuthenticated()) {
      return { success: false, error: new Error('User not authenticated') };
    }

    try {
      const { data, error } = await this.supabase
        .from('profiles')
        .upsert({
          id: this.currentUser.id,
          ...updates,
          updated_at: new Date()
        })
        .select()
        .single();

      if (error) {
        throw error;
      }

      return { success: true, profile: data };
    } catch (error) {
      console.error('❌ Failed to update user profile:', error);
      return { success: false, error };
    }
  }
}

// Create global instance
window.authManager = new AuthManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AuthManager;
}
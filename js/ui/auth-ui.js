/**
 * @fileoverview Authentication UI components for ClueChain
 * Handles sign-in/sign-out buttons and user profile display
 */

class AuthUI {
  constructor() {
    this.initialized = false;
    this.currentUser = null;
    this.authContainer = null;
  }

  /**
   * Initialize the authentication UI
   * @returns {Promise<void>}
   */
  async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      // Wait for auth manager to be initialized
      await window.authManager.initialize();
      
      // Create auth container
      this.createAuthContainer();
      
      // Set up auth state listener
      window.authManager.addAuthListener((event, data) => {
        this.handleAuthStateChange(event, data);
      });

      // Update UI based on current auth state with a small delay
      // to ensure auth manager has finished initialization
      setTimeout(() => {
        this.updateAuthUI();
      }, 100);
      
      this.initialized = true;
      console.log('✅ AuthUI initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize AuthUI:', error);
      throw error;
    }
  }

  /**
   * Create authentication container in the header
   * @private
   */
  createAuthContainer() {
    const gameHeader = document.querySelector('.game-header');
    if (!gameHeader) {
      console.error('❌ Game header not found for auth container');
      return;
    }

    // Create auth container
    this.authContainer = document.createElement('div');
    this.authContainer.className = 'auth-container';
    
    // Add auth container as a sibling to header-content (same level)
    gameHeader.appendChild(this.authContainer);
  }

  /**
   * Handle authentication state changes
   * @param {string} event - Auth event type
   * @param {Object} data - Auth data
   * @private
   */
  handleAuthStateChange(event, data) {
    console.log('🔄 AuthUI received auth state change:', event, data?.user?.email);
    
    switch (event) {
      case 'SIGNED_IN':
        this.currentUser = data.user;
        this.updateAuthUI();
        break;
      case 'SIGNED_OUT':
        this.currentUser = null;
        this.updateAuthUI();
        break;
      case 'USER_UPDATED':
        this.currentUser = data.user;
        this.updateAuthUI();
        break;
      case 'INITIAL_SESSION':
        // Handle initial session - this is fired when we detect an existing session
        if (data && data.user) {
          this.currentUser = data.user;
          this.updateAuthUI();
        }
        break;
    }
  }

  /**
   * Update authentication UI based on current state
   * @private
   */
  updateAuthUI() {
    if (!this.authContainer) {
      return;
    }

    // Double-check auth state from auth manager
    const authManagerUser = window.authManager.getCurrentUser();
    const isAuthenticated = window.authManager.isAuthenticated();

    console.log('🔄 Updating auth UI. Current user:', this.currentUser);
    console.log('🔄 Auth manager user:', authManagerUser);
    console.log('🔄 Is authenticated:', isAuthenticated);

    // GUEST MODE: Always show game content, show different UI based on auth state
    // This allows users to play without signing in
    if (isAuthenticated && authManagerUser) {
      this.currentUser = authManagerUser;
      console.log('✅ User is authenticated, rendering authenticated UI');
      this.renderAuthenticatedUI();
    } else {
      this.currentUser = null;
      console.log('👤 User is guest, rendering guest UI');
      this.renderGuestUI();
    }

    // Always show game content (no welcome screen blocking)
    this.showGameContent();
  }

  /**
   * Show welcome screen with only sign-in
   * @private
   */
  showWelcomeScreen() {
    // Hide game content
    const gameContent = document.querySelector('.container');
    if (gameContent) {
      gameContent.style.display = 'none';
    }

    // Create or show welcome screen
    let welcomeScreen = document.getElementById('welcome-screen');
    if (!welcomeScreen) {
      welcomeScreen = document.createElement('div');
      welcomeScreen.id = 'welcome-screen';
      welcomeScreen.className = 'welcome-screen';
      welcomeScreen.innerHTML = `
        <div class="welcome-content">
          <h1>Welcome to ClueChain</h1>
          <p>A word guessing game where you reveal hidden words by solving clues.</p>
          <div class="welcome-auth">
            <p>Please sign in to play:</p>
            <div id="welcome-auth-container"></div>
          </div>
        </div>
      `;
      document.body.appendChild(welcomeScreen);
    }

    welcomeScreen.style.display = 'flex';

    // Move auth container to welcome screen
    const welcomeAuthContainer = document.getElementById('welcome-auth-container');
    if (welcomeAuthContainer && this.authContainer) {
      welcomeAuthContainer.appendChild(this.authContainer);
    }
  }

  /**
   * Show game content and hide welcome screen
   * @private
   */
  showGameContent() {
    // Show game content
    const gameContent = document.querySelector('.container');
    if (gameContent) {
      gameContent.style.display = 'block';
    }

    // Hide welcome screen
    const welcomeScreen = document.getElementById('welcome-screen');
    if (welcomeScreen) {
      welcomeScreen.style.display = 'none';
    }

    // Move auth container back to header (as sibling to header-content)
    const gameHeader = document.querySelector('.game-header');
    if (gameHeader && this.authContainer) {
      gameHeader.appendChild(this.authContainer);
    }
  }

  /**
   * Render UI for authenticated users
   * @private
   */
  renderAuthenticatedUI() {
    const displayName = this.getDisplayName();
    const avatarUrl = this.currentUser.user_metadata?.avatar_url;

    this.authContainer.innerHTML = `
      <div class="user-profile-minimal">
        <div class="user-avatar-small">
          ${avatarUrl ? 
            `<img src="${avatarUrl}" alt="${displayName}" class="avatar-img-small">` :
            `<div class="avatar-placeholder-small">${displayName.charAt(0).toUpperCase()}</div>`
          }
        </div>
        <div class="user-streak-minimal" id="user-streak">
          <span class="streak-icon">🔥</span>
          <span class="streak-count">0</span>
        </div>
        <div class="user-menu">
          <button class="menu-dots" id="user-menu-btn">⋯</button>
          <div class="menu-dropdown" id="user-menu-dropdown">
            <button class="menu-item" id="sign-out-btn">Sign Out</button>
            <button class="menu-item" id="stats-btn">Stats</button>
          </div>
        </div>
      </div>
    `;

    // Add event listeners
    this.setupAuthenticatedEventListeners();
    
    // Load and display streak
    this.loadUserStreak();
  }

  /**
   * Render UI for guest users (not signed in)
   * Shows a small, non-blocking sign-in option in the header
   * @private
   */
  renderGuestUI() {
    this.authContainer.innerHTML = `
      <div class="guest-mode">
        <span class="guest-label">Playing as Guest</span>
        <button class="sign-in-btn-small" id="sign-in-btn-small">
          <svg class="google-icon-small" viewBox="0 0 24 24" width="16" height="16">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Sign In
        </button>
      </div>
    `;

    // Add event listener for sign-in button
    const signInBtn = document.getElementById('sign-in-btn-small');
    if (signInBtn) {
      signInBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        await this.handleSignIn();
      });
    }
  }

  /**
   * Render UI for unauthenticated users
   * @private
   */
  renderUnauthenticatedUI() {
    console.log('🔄 Rendering unauthenticated UI');
    
    // Create button element programmatically
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'sign-in-btn';
    button.id = 'sign-in-btn';
    
    button.innerHTML = `
      <svg class="google-icon" viewBox="0 0 24 24" width="18" height="18">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
      Sign in with Google
    `;
    
    // Add event listener directly to the button
    button.addEventListener('click', (e) => {
      console.log('🔄 Direct button click handler triggered!', e);
      console.log('🔄 Event target:', e.target);
      console.log('🔄 Event currentTarget:', e.currentTarget);
      console.log('🔄 Event type:', e.type);
      
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      // Log to console instead of alert
      console.log('🔄 Button clicked! Starting auth flow...');
      
      // Call handleSignIn but catch any errors
      try {
        this.handleSignIn();
      } catch (error) {
        console.error('❌ Error in handleSignIn:', error);
      }
      return false;
    });
    
    // Clear container and add button
    this.authContainer.innerHTML = '';
    this.authContainer.appendChild(button);
    
    console.log('🔄 Button created and added to container');
  }

  /**
   * Set up event listeners for authenticated state
   * @private
   */
  setupAuthenticatedEventListeners() {
    const menuBtn = document.getElementById('user-menu-btn');
    const menuDropdown = document.getElementById('user-menu-dropdown');
    const signOutBtn = document.getElementById('sign-out-btn');
    const statsBtn = document.getElementById('stats-btn');

    // Toggle menu dropdown
    if (menuBtn && menuDropdown) {
      menuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        menuDropdown.classList.toggle('show');
      });

      // Close menu when clicking outside
      document.addEventListener('click', () => {
        menuDropdown.classList.remove('show');
      });
    }

    // Sign out
    if (signOutBtn) {
      signOutBtn.addEventListener('click', async () => {
        await this.handleSignOut();
      });
    }

    // Stats (placeholder)
    if (statsBtn) {
      statsBtn.addEventListener('click', () => {
        alert('Stats feature coming soon!');
      });
    }
  }

  /**
   * Set up event listeners for unauthenticated state
   * @private
   */
  setupUnauthenticatedEventListeners() {
    console.log('🔄 Setting up unauthenticated event listeners');
    
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
      const signInBtn = document.getElementById('sign-in-btn');
      console.log('🔄 Sign in button found:', signInBtn);
      
      if (signInBtn) {
        // Remove any existing event listeners
        signInBtn.onclick = null;
        
        // Add click event listener with capture phase
        signInBtn.addEventListener('click', (e) => {
          console.log('🔄 Sign in button clicked!', e);
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          this.handleSignIn();
          return false;
        }, true);
        
        // Also add as onclick handler as backup
        signInBtn.onclick = (e) => {
          console.log('🔄 Sign in button onclick!', e);
          e.preventDefault();
          e.stopPropagation();
          this.handleSignIn();
          return false;
        };
        
        signInBtn.addEventListener('mousedown', () => {
          console.log('🔄 Sign in button mousedown!');
        });
        
        // Test if button is actually clickable
        setTimeout(() => {
          console.log('🔄 Testing button clickability...');
          const buttonRect = signInBtn.getBoundingClientRect();
          console.log('🔄 Button position:', buttonRect);
          console.log('🔄 Button style:', window.getComputedStyle(signInBtn));
        }, 1000);
      } else {
        console.error('❌ Sign in button not found!');
      }
    }, 100);
  }

  /**
   * Check current authentication status
   * @returns {Object} Current auth status
   */
  async checkAuthStatus() {
    console.log('🔄 Checking authentication status...');
    const session = await window.authManager.getCurrentSession();
    console.log('🔄 Current session:', session);
    const user = window.authManager.getCurrentUser();
    console.log('🔄 Current user:', user);
    const isAuthenticated = window.authManager.isAuthenticated();
    console.log('🔄 Is authenticated:', isAuthenticated);
    return { session, user, isAuthenticated };
  }

  /**
   * Handle sign in button click
   * @private
   */
  async handleSignIn() {
    console.log('🔄 handleSignIn called');
    
    try {
      // First check if we're already authenticated
      console.log('🔄 Checking auth status...');
      await this.checkAuthStatus();
      
      const signInBtn = document.getElementById('sign-in-btn');
      if (signInBtn) {
        signInBtn.disabled = true;
        signInBtn.innerHTML = '<span>Signing in...</span>';
      }

      console.log('🔄 About to call signInWithGoogle...');
      console.log('🔄 Auth manager available:', !!window.authManager);
      
      if (!window.authManager) {
        throw new Error('Auth manager not available');
      }
      
      console.log('🔄 Calling signInWithGoogle...');
      const result = await window.authManager.signInWithGoogle();
      console.log('🔄 SignInWithGoogle result:', result);
      
      if (!result.success) {
        console.error('❌ Sign in failed:', result.error);
        this.showAuthError('Sign in failed. Please try again.');
      }
    } catch (error) {
      console.error('❌ Sign in error:', error);
      this.showAuthError('Sign in failed. Please try again.');
    } finally {
      // Reset button state
      if (signInBtn) {
        signInBtn.disabled = false;
        this.renderUnauthenticatedUI();
      }
    }
  }

  /**
   * Handle sign out button click
   * @private
   */
  async handleSignOut() {
    const signOutBtn = document.getElementById('sign-out-btn');
    if (signOutBtn) {
      signOutBtn.disabled = true;
      signOutBtn.innerHTML = '<span>Signing out...</span>';
    }

    try {
      const result = await window.authManager.signOut();
      
      if (!result.success) {
        console.error('❌ Sign out failed:', result.error);
        this.showAuthError('Sign out failed. Please try again.');
      }
    } catch (error) {
      console.error('❌ Sign out error:', error);
      this.showAuthError('Sign out failed. Please try again.');
    }
  }

  /**
   * Load and display user streak
   * @private
   */
  async loadUserStreak() {
    if (!window.streakTracker) {
      return;
    }

    try {
      const result = await window.streakTracker.getCurrentStreak();
      
      if (result.success) {
        this.updateStreakDisplay(result.streak.current_streak || 0);
      }
    } catch (error) {
      console.error('❌ Failed to load user streak:', error);
    }
  }

  /**
   * Update streak display
   * @param {number} streakCount - Current streak count
   */
  updateStreakDisplay(streakCount) {
    const streakElement = document.getElementById('user-streak');
    if (streakElement) {
      const streakCountElement = streakElement.querySelector('.streak-count');
      if (streakCountElement) {
        streakCountElement.textContent = streakCount;
      }
    }
  }

  /**
   * Get display name for current user
   * @returns {string} Display name
   * @private
   */
  getDisplayName() {
    if (!this.currentUser) {
      return 'User';
    }

    return this.currentUser.user_metadata?.full_name ||
           this.currentUser.user_metadata?.name ||
           this.currentUser.email?.split('@')[0] ||
           'User';
  }

  /**
   * Show authentication error message
   * @param {string} message - Error message
   * @private
   */
  showAuthError(message) {
    // Use existing toast system if available
    if (window.showToast) {
      window.showToast(message, 'error');
    } else {
      alert(message);
    }
  }

  /**
   * Show authentication success message
   * @param {string} message - Success message
   */
  showAuthSuccess(message) {
    // Use existing toast system if available
    if (window.showToast) {
      window.showToast(message, 'success');
    } else {
      console.log(message);
    }
  }
}

// Create global instance
window.authUI = new AuthUI();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AuthUI;
}
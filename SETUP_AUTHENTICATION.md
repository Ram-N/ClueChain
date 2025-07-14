# ClueChain Authentication Setup Guide

This guide will help you set up Gmail OAuth authentication with Supabase for ClueChain.

## Prerequisites

- Google Cloud Console account
- Supabase account

## Step 1: Create Supabase Project

1. Go to [Supabase](https://supabase.com) and create a new project
2. Choose a project name (e.g., "cluechain")
3. Set a database password (save this securely)
4. Select your region
5. Wait for the project to be created

## Step 2: Get Supabase Credentials

1. In your Supabase project dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (e.g., `https://xyzabc123.supabase.co`)
   - **Anon/Public Key** (starts with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)

## Step 3: Configure Supabase in ClueChain

1. Open `config/supabase-config.js`
2. Replace the placeholder values:
   ```javascript
   const SUPABASE_CONFIG = {
     url: 'https://your-project-ref.supabase.co', // Replace with your Project URL
     anonKey: 'your-anon-key', // Replace with your Anon/Public Key
     // ... rest of config
   };
   ```

## Step 4: Set Up Database Schema

1. In your Supabase project, go to **SQL Editor**
2. Run the following SQL files in order:
   - First: `assets/sql/create-tables.sql`
   - Second: `assets/sql/create-triggers.sql`
   - Third: `assets/sql/rls-policies.sql`

## Step 5: Configure Google OAuth

### 5.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google+ API** (if not already enabled)

### 5.2 Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** user type
3. Fill in the required information:
   - **App name**: ClueChain
   - **User support email**: Your email
   - **App logo**: Optional
   - **App domain**: Your domain (or leave blank for localhost)
   - **Developer contact information**: Your email
4. Add scopes:
   - `../auth/userinfo.email`
   - `../auth/userinfo.profile`
   - `openid`
5. Save and continue

### 5.3 Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth Client ID**
3. Choose **Web application**
4. Configure:
   - **Name**: ClueChain Web Client
   - **Authorized JavaScript origins**:
     - `http://localhost:8000` (for local development)
     - `https://your-domain.com` (for production)
   - **Authorized redirect URIs**:
     - `https://your-project-ref.supabase.co/auth/v1/callback`
5. Save the credentials

### 5.4 Configure Google OAuth in Supabase

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Find **Google** and click the toggle to enable it
3. Enter your Google OAuth credentials:
   - **Client ID**: From Google Cloud Console
   - **Client Secret**: From Google Cloud Console
4. Save the configuration

## Step 6: Test the Setup

1. Start a local server:
   ```bash
   python -m http.server 8000
   # OR
   npx http-server -p 8000
   ```

2. Open `http://localhost:8000` in your browser
3. You should see a "Sign in with Google" button in the header
4. Click it to test the authentication flow

## Step 7: Production Deployment

When deploying to production:

1. Update the Google OAuth credentials with your production domain
2. Update the Supabase redirect URLs if needed
3. Ensure your production domain is added to Supabase's allowed origins

## Troubleshooting

### Common Issues

1. **"Please configure your Supabase URL"**
   - Make sure you've updated `config/supabase-config.js` with your actual credentials

2. **"OAuth Error: redirect_uri_mismatch"**
   - Check that your redirect URIs in Google Cloud Console match your Supabase project URL

3. **"Authentication not working"**
   - Check browser console for errors
   - Verify all SQL scripts have been run successfully
   - Ensure Row Level Security policies are enabled

4. **"Streaks not updating"**
   - Check that database triggers are created
   - Verify user has proper permissions

### Testing Database Connection

You can test the database connection by opening the browser console and running:

```javascript
// Test Supabase connection
await window.SupabaseClient.testConnection();

// Test authentication
console.log('User authenticated:', window.authManager.isAuthenticated());

// Test streak tracking
const streak = await window.streakTracker.getCurrentStreak();
console.log('Current streak:', streak);
```

## Features

Once set up, users will be able to:

- Sign in with their Google account
- Track their daily play streaks
- View their current and longest streaks
- Have their game progress saved to the database
- See their streak count in the header

## Security Notes

- Never commit your Supabase credentials to version control
- Use environment variables for production deployments
- Regularly rotate your Supabase service keys
- Monitor your Supabase usage and authentication logs

## Next Steps

After basic authentication is working, you can extend the system with:

- Leaderboards
- Achievement system
- Email notifications for streak milestones
- Social features
- Advanced analytics

For any issues, check the browser console for error messages and refer to the Supabase documentation.
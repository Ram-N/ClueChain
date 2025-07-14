-- ClueChain Row Level Security Policies (Fixed for Supabase)
-- Secure access to user data with proper authentication

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_streaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_scores ENABLE ROW LEVEL SECURITY;

-- Profiles table policies
-- Users can view their own profile
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile"
    ON public.profiles
    FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own profile
DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile"
    ON public.profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- FIXED: Allow profile creation during OAuth signup
-- This policy allows the trigger to create profiles for new users
DROP POLICY IF EXISTS "Allow profile creation for authenticated users" ON public.profiles;
CREATE POLICY "Allow profile creation for authenticated users"
    ON public.profiles
    FOR INSERT
    WITH CHECK (true);  -- Allow system to create profiles via trigger

-- User activities table policies
-- Users can view their own activities
DROP POLICY IF EXISTS "Users can view their own activities" ON public.user_activities;
CREATE POLICY "Users can view their own activities"
    ON public.user_activities
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own activities
DROP POLICY IF EXISTS "Users can insert their own activities" ON public.user_activities;
CREATE POLICY "Users can insert their own activities"
    ON public.user_activities
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own activities (if needed)
DROP POLICY IF EXISTS "Users can update their own activities" ON public.user_activities;
CREATE POLICY "Users can update their own activities"
    ON public.user_activities
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Optional: Allow users to delete their own activities
DROP POLICY IF EXISTS "Users can delete their own activities" ON public.user_activities;
CREATE POLICY "Users can delete their own activities"
    ON public.user_activities
    FOR DELETE
    USING (auth.uid() = user_id);

-- User streaks table policies
-- Users can view their own streaks
DROP POLICY IF EXISTS "Users can view their own streaks" ON public.user_streaks;
CREATE POLICY "Users can view their own streaks"
    ON public.user_streaks
    FOR SELECT
    USING (auth.uid() = user_id);

-- FIXED: Allow streak creation via triggers
DROP POLICY IF EXISTS "Allow streak creation for authenticated users" ON public.user_streaks;
CREATE POLICY "Allow streak creation for authenticated users"
    ON public.user_streaks
    FOR INSERT
    WITH CHECK (true);  -- Allow system to create streaks via trigger

-- FIXED: Allow streak updates via triggers
DROP POLICY IF EXISTS "Allow streak updates for authenticated users" ON public.user_streaks;
CREATE POLICY "Allow streak updates for authenticated users"
    ON public.user_streaks
    FOR UPDATE
    USING (true)  -- Allow system to update streaks via trigger
    WITH CHECK (true);

-- Game scores table policies
-- Users can view their own scores
DROP POLICY IF EXISTS "Users can view their own game scores" ON public.game_scores;
CREATE POLICY "Users can view their own game scores"
    ON public.game_scores
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own scores
DROP POLICY IF EXISTS "Users can insert their own game scores" ON public.game_scores;
CREATE POLICY "Users can insert their own game scores"
    ON public.game_scores
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own scores (for game completion)
DROP POLICY IF EXISTS "Users can update their own game scores" ON public.game_scores;
CREATE POLICY "Users can update their own game scores"
    ON public.game_scores
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Grant necessary permissions
-- Allow authenticated users to access their own data
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_activities TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_streaks TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.game_scores TO authenticated;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon;

-- Comments for documentation
COMMENT ON POLICY "Users can view their own profile" ON public.profiles IS 'Allows users to view their own profile data';
COMMENT ON POLICY "Users can view their own activities" ON public.user_activities IS 'Allows users to view their own activity history';
COMMENT ON POLICY "Users can view their own streaks" ON public.user_streaks IS 'Allows users to view their own streak information';
COMMENT ON POLICY "Users can view their own game scores" ON public.game_scores IS 'Allows users to view their own game scores';
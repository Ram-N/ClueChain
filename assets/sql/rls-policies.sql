-- ClueChain Row Level Security Policies
-- Secure access to user data with proper authentication

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_streaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_scores ENABLE ROW LEVEL SECURITY;

-- Profiles table policies
-- Users can view their own profile
CREATE POLICY "Users can view their own profile"
    ON public.profiles
    FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update their own profile"
    ON public.profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Allow profile creation for new users (handled by trigger)
CREATE POLICY "Allow profile creation for authenticated users"
    ON public.profiles
    FOR INSERT
    WITH CHECK (auth.uid() = id);

-- User activities table policies
-- Users can view their own activities
CREATE POLICY "Users can view their own activities"
    ON public.user_activities
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own activities
CREATE POLICY "Users can insert their own activities"
    ON public.user_activities
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own activities (if needed)
CREATE POLICY "Users can update their own activities"
    ON public.user_activities
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Optional: Allow users to delete their own activities
CREATE POLICY "Users can delete their own activities"
    ON public.user_activities
    FOR DELETE
    USING (auth.uid() = user_id);

-- User streaks table policies
-- Users can view their own streaks
CREATE POLICY "Users can view their own streaks"
    ON public.user_streaks
    FOR SELECT
    USING (auth.uid() = user_id);

-- System can insert streak records (via triggers)
CREATE POLICY "Allow streak creation for authenticated users"
    ON public.user_streaks
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- System can update streak records (via triggers)
CREATE POLICY "Allow streak updates for authenticated users"
    ON public.user_streaks
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Game scores table policies
-- Users can view their own scores
CREATE POLICY "Users can view their own game scores"
    ON public.game_scores
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own scores
CREATE POLICY "Users can insert their own game scores"
    ON public.game_scores
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own scores (for game completion)
CREATE POLICY "Users can update their own game scores"
    ON public.game_scores
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Optional: Public leaderboard access (commented out for now)
-- Uncomment these if you want to implement public leaderboards

-- Allow public read access to anonymized leaderboard data
-- CREATE POLICY "Public leaderboard access"
--     ON public.game_scores
--     FOR SELECT
--     USING (true);

-- Allow public read access to anonymized profile data for leaderboards
-- CREATE POLICY "Public profile access for leaderboards"
--     ON public.profiles
--     FOR SELECT
--     USING (true);

-- Admin policies (for future admin functionality)
-- These should be used cautiously and only for authorized admin users

-- CREATE POLICY "Admin can view all profiles"
--     ON public.profiles
--     FOR SELECT
--     USING (
--         auth.uid() IN (
--             SELECT id FROM public.profiles 
--             WHERE email = 'admin@cluechain.com'
--         )
--     );

-- Security functions for additional checks
-- Function to check if user owns the record
CREATE OR REPLACE FUNCTION auth.user_owns_record(user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN auth.uid() = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is authenticated
CREATE OR REPLACE FUNCTION auth.is_authenticated()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN auth.uid() IS NOT NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's email (for admin checks)
CREATE OR REPLACE FUNCTION auth.get_user_email()
RETURNS TEXT AS $$
BEGIN
    RETURN (
        SELECT email 
        FROM auth.users 
        WHERE id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
-- Allow authenticated users to access their own data
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_activities TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_streaks TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.game_scores TO authenticated;

-- Allow anonymous users to view public data (if needed)
-- GRANT SELECT ON public.profiles TO anon;
-- GRANT SELECT ON public.game_scores TO anon;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon;

-- Comments for documentation
COMMENT ON POLICY "Users can view their own profile" ON public.profiles IS 'Allows users to view their own profile data';
COMMENT ON POLICY "Users can view their own activities" ON public.user_activities IS 'Allows users to view their own activity history';
COMMENT ON POLICY "Users can view their own streaks" ON public.user_streaks IS 'Allows users to view their own streak information';
COMMENT ON POLICY "Users can view their own game scores" ON public.game_scores IS 'Allows users to view their own game scores';

COMMENT ON FUNCTION auth.user_owns_record(UUID) IS 'Helper function to check if authenticated user owns a record';
COMMENT ON FUNCTION auth.is_authenticated() IS 'Helper function to check if user is authenticated';
COMMENT ON FUNCTION auth.get_user_email() IS 'Helper function to get current user email for admin checks';
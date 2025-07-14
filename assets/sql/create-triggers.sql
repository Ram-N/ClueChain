-- ClueChain Database Triggers
-- Automatic streak calculation and profile updates

-- Function to update streak when new activity is recorded
CREATE OR REPLACE FUNCTION update_user_streak()
RETURNS TRIGGER AS $$
DECLARE
    streak_record RECORD;
    days_since_last INTEGER;
BEGIN
    -- Get current streak record
    SELECT * INTO streak_record
    FROM public.user_streaks
    WHERE user_id = NEW.user_id AND activity_type = NEW.activity_type;
    
    -- If no streak record exists, create one
    IF streak_record IS NULL THEN
        INSERT INTO public.user_streaks (
            user_id, 
            activity_type, 
            current_streak, 
            current_streak_start_date,
            last_activity_date,
            longest_streak,
            longest_streak_start_date,
            longest_streak_end_date
        ) VALUES (
            NEW.user_id,
            NEW.activity_type,
            1,
            NEW.activity_date,
            NEW.activity_date,
            1,
            NEW.activity_date,
            NEW.activity_date
        );
        
        RETURN NEW;
    END IF;
    
    -- Calculate days since last activity
    days_since_last := NEW.activity_date - streak_record.last_activity_date;
    
    -- Handle different scenarios
    IF days_since_last = 0 THEN
        -- Same day activity, no streak change
        RETURN NEW;
    ELSIF days_since_last = 1 THEN
        -- Consecutive day, increment streak
        UPDATE public.user_streaks SET
            current_streak = current_streak + 1,
            last_activity_date = NEW.activity_date,
            longest_streak = GREATEST(longest_streak, current_streak + 1),
            longest_streak_start_date = CASE
                WHEN current_streak + 1 > longest_streak THEN current_streak_start_date
                ELSE longest_streak_start_date
            END,
            longest_streak_end_date = CASE
                WHEN current_streak + 1 > longest_streak THEN NEW.activity_date
                ELSE longest_streak_end_date
            END,
            updated_at = NOW()
        WHERE user_id = NEW.user_id AND activity_type = NEW.activity_type;
    ELSE
        -- Streak broken, reset to 1
        UPDATE public.user_streaks SET
            current_streak = 1,
            current_streak_start_date = NEW.activity_date,
            last_activity_date = NEW.activity_date,
            updated_at = NOW()
        WHERE user_id = NEW.user_id AND activity_type = NEW.activity_type;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for streak updates
DROP TRIGGER IF EXISTS trigger_update_user_streak ON public.user_activities;
CREATE TRIGGER trigger_update_user_streak
    AFTER INSERT ON public.user_activities
    FOR EACH ROW
    EXECUTE FUNCTION update_user_streak();

-- Function to update profile statistics
CREATE OR REPLACE FUNCTION update_profile_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update profile statistics when game is completed
    IF NEW.activity_type = 'game_completed' THEN
        UPDATE public.profiles SET
            total_games_played = total_games_played + 1,
            total_score = total_score + COALESCE(NEW.score, 0),
            updated_at = NOW()
        WHERE id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for profile stats updates
DROP TRIGGER IF EXISTS trigger_update_profile_stats ON public.user_activities;
CREATE TRIGGER trigger_update_profile_stats
    AFTER INSERT ON public.user_activities
    FOR EACH ROW
    EXECUTE FUNCTION update_profile_stats();

-- Function to handle profile creation for new users
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (
        id, 
        email, 
        full_name, 
        avatar_url,
        display_name
    ) VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url',
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1)
        )
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for new user profile creation
DROP TRIGGER IF EXISTS trigger_handle_new_user ON auth.users;
CREATE TRIGGER trigger_handle_new_user
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- Function to update timestamps automatically
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS trigger_profiles_updated_at ON public.profiles;
CREATE TRIGGER trigger_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

DROP TRIGGER IF EXISTS trigger_user_streaks_updated_at ON public.user_streaks;
CREATE TRIGGER trigger_user_streaks_updated_at
    BEFORE UPDATE ON public.user_streaks
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

-- Function to validate streak data integrity
CREATE OR REPLACE FUNCTION validate_streak_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure current_streak is not negative
    IF NEW.current_streak < 0 THEN
        NEW.current_streak := 0;
    END IF;
    
    -- Ensure longest_streak is not less than current_streak
    IF NEW.longest_streak < NEW.current_streak THEN
        NEW.longest_streak := NEW.current_streak;
    END IF;
    
    -- Ensure start date is not after end date
    IF NEW.current_streak_start_date > NEW.last_activity_date THEN
        NEW.current_streak_start_date := NEW.last_activity_date;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for streak validation
DROP TRIGGER IF EXISTS trigger_validate_streak_data ON public.user_streaks;
CREATE TRIGGER trigger_validate_streak_data
    BEFORE INSERT OR UPDATE ON public.user_streaks
    FOR EACH ROW
    EXECUTE FUNCTION validate_streak_data();

-- Function to clean up old activity records (optional, for data management)
CREATE OR REPLACE FUNCTION cleanup_old_activities()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete activity records older than 2 years
    DELETE FROM public.user_activities
    WHERE created_at < NOW() - INTERVAL '2 years';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON FUNCTION update_user_streak() IS 'Automatically updates user streak when new activity is recorded';
COMMENT ON FUNCTION update_profile_stats() IS 'Updates profile statistics when games are completed';
COMMENT ON FUNCTION handle_new_user() IS 'Creates profile record for new authenticated users';
COMMENT ON FUNCTION handle_updated_at() IS 'Automatically updates updated_at timestamp';
COMMENT ON FUNCTION validate_streak_data() IS 'Validates streak data integrity before insert/update';
COMMENT ON FUNCTION cleanup_old_activities() IS 'Utility function to clean up old activity records';
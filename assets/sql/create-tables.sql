-- ClueChain Database Schema
-- Tables for user authentication, profiles, activities, and streak tracking

-- Enable UUID extension (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User profiles table (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- ClueChain specific fields
    display_name TEXT,
    total_games_played INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    
    PRIMARY KEY (id)
);

-- User activities table for tracking game sessions
CREATE TABLE IF NOT EXISTS public.user_activities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL, -- 'game_completed', 'game_started', etc.
    activity_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Activity metadata (JSON for flexibility)
    metadata JSONB DEFAULT '{}',
    
    -- Game-specific fields
    game_date DATE, -- The date of the puzzle (might be different from activity_date)
    score INTEGER,
    max_possible_score INTEGER,
    words_found INTEGER,
    total_words INTEGER,
    completion_time_seconds INTEGER,
    
    -- Ensure one activity per user per day per type
    CONSTRAINT unique_user_activity_per_day UNIQUE (user_id, activity_type, activity_date)
);

-- User streaks table for efficient streak tracking
CREATE TABLE IF NOT EXISTS public.user_streaks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    
    -- Current streak info
    current_streak INTEGER DEFAULT 0,
    current_streak_start_date DATE,
    last_activity_date DATE,
    
    -- Longest streak info
    longest_streak INTEGER DEFAULT 0,
    longest_streak_start_date DATE,
    longest_streak_end_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one streak record per user per activity type
    CONSTRAINT unique_user_streak_per_activity UNIQUE (user_id, activity_type)
);

-- Game scores table for detailed score tracking (future enhancement)
CREATE TABLE IF NOT EXISTS public.game_scores (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    game_date DATE NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    max_possible_score INTEGER NOT NULL DEFAULT 0,
    percentage DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN max_possible_score > 0 THEN ROUND((score::DECIMAL / max_possible_score) * 100, 2)
            ELSE 0
        END
    ) STORED,
    
    -- Game completion details
    words_found INTEGER DEFAULT 0,
    total_words INTEGER DEFAULT 0,
    completion_time_seconds INTEGER,
    letters_purchased INTEGER DEFAULT 0,
    hints_used INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure one score record per user per game date
    CONSTRAINT unique_user_game_score UNIQUE (user_id, game_date)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_display_name ON public.profiles(display_name);

CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON public.user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_date ON public.user_activities(user_id, activity_date);
CREATE INDEX IF NOT EXISTS idx_user_activities_type_date ON public.user_activities(activity_type, activity_date);
CREATE INDEX IF NOT EXISTS idx_user_activities_game_date ON public.user_activities(user_id, game_date);

CREATE INDEX IF NOT EXISTS idx_user_streaks_user_id ON public.user_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_streaks_activity_type ON public.user_streaks(activity_type);

CREATE INDEX IF NOT EXISTS idx_game_scores_user_id ON public.game_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_game_scores_game_date ON public.game_scores(game_date);
CREATE INDEX IF NOT EXISTS idx_game_scores_score ON public.game_scores(score DESC);

-- Comments for documentation
COMMENT ON TABLE public.profiles IS 'Extended user profile information';
COMMENT ON TABLE public.user_activities IS 'Tracks all user activities including game sessions';
COMMENT ON TABLE public.user_streaks IS 'Maintains current and longest streak information per user';
COMMENT ON TABLE public.game_scores IS 'Detailed game score tracking with completion metrics';

COMMENT ON COLUMN public.user_activities.activity_type IS 'Type of activity: game_completed, game_started, etc.';
COMMENT ON COLUMN public.user_activities.activity_date IS 'Date when the activity occurred (user timezone)';
COMMENT ON COLUMN public.user_activities.game_date IS 'Date of the puzzle being played (might differ from activity_date)';
COMMENT ON COLUMN public.user_activities.metadata IS 'Flexible JSON field for additional activity data';

COMMENT ON COLUMN public.user_streaks.current_streak IS 'Current consecutive days streak';
COMMENT ON COLUMN public.user_streaks.longest_streak IS 'Longest streak ever achieved by user';
COMMENT ON COLUMN public.user_streaks.activity_type IS 'Type of activity being tracked for streaks';
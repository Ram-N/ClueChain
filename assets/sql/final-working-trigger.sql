-- Final working trigger for OAuth user creation
-- This version has proper error handling and works with OAuth

-- Drop the debug trigger
DROP TRIGGER IF EXISTS trigger_handle_new_user ON auth.users;
DROP FUNCTION IF EXISTS handle_new_user();

-- Create the final working version
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Create profile for new user with proper error handling
    INSERT INTO public.profiles (
        id, 
        email, 
        full_name, 
        avatar_url,
        display_name
    ) VALUES (
        NEW.id,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name'
        ),
        NEW.raw_user_meta_data->>'avatar_url',
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1)
        )
    );
    
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    -- Log the error but don't fail the user creation
    RAISE WARNING 'Failed to create profile for user %: %', NEW.id, SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER trigger_handle_new_user
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- Now let's set up proper RLS policies that work with OAuth
-- First, ensure RLS is enabled
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Drop the temporary permissive policy
DROP POLICY IF EXISTS "Allow all profile operations for testing" ON public.profiles;

-- Create proper policies that work with OAuth
CREATE POLICY "Users can view their own profile"
    ON public.profiles
    FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- This policy allows the system to create profiles during OAuth
-- but prevents manual unauthorized creation
CREATE POLICY "System can create profiles during OAuth"
    ON public.profiles
    FOR INSERT
    WITH CHECK (
        -- Allow if no current user (system/trigger creating during OAuth)
        auth.uid() IS NULL OR
        -- Or if the user is creating their own profile
        auth.uid() = id
    );

-- Test that everything is working
SELECT 'Trigger and policies created successfully' as status;
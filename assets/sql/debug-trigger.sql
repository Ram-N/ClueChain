-- Debug version of the trigger to see what's happening
-- This will help us understand why the trigger is failing

-- Drop the existing trigger and function
DROP TRIGGER IF EXISTS trigger_handle_new_user ON auth.users;
DROP FUNCTION IF EXISTS handle_new_user();

-- Create a simpler debug version
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Log what we're trying to do
    RAISE NOTICE 'Trigger called for user: %', NEW.id;
    RAISE NOTICE 'User email: %', NEW.email;
    RAISE NOTICE 'User meta_data: %', NEW.raw_user_meta_data;
    
    -- Try to insert the profile with basic error handling
    BEGIN
        INSERT INTO public.profiles (
            id, 
            email, 
            full_name, 
            display_name
        ) VALUES (
            NEW.id,
            NEW.email,
            COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name'),
            COALESCE(
                NEW.raw_user_meta_data->>'full_name',
                NEW.raw_user_meta_data->>'name',
                split_part(NEW.email, '@', 1)
            )
        );
        
        RAISE NOTICE 'Profile created successfully for user: %', NEW.id;
        
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Error creating profile for user %: %', NEW.id, SQLERRM;
        -- Don't re-raise the error, let the user creation succeed
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER trigger_handle_new_user
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- Test that the trigger is created
SELECT 
    tgname AS trigger_name,
    tgrelid::regclass AS table_name,
    tgenabled AS enabled
FROM pg_trigger 
WHERE tgrelid = 'auth.users'::regclass;
-- Temporarily disable RLS for OAuth testing
-- This is a temporary fix to get OAuth working
-- You should re-enable RLS after testing

-- Disable RLS on profiles table temporarily
ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;

-- Drop all existing policies on profiles table
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
DROP POLICY IF EXISTS "Allow profile creation for authenticated users" ON public.profiles;
DROP POLICY IF EXISTS "Allow profile creation for new users" ON public.profiles;

-- Re-enable RLS but with more permissive policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create very permissive policies for testing
CREATE POLICY "Allow all profile operations for testing"
    ON public.profiles
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Show current policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE tablename = 'profiles';
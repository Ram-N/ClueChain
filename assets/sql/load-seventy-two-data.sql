-- =============================================================
-- Load 72somewhere seed data into the seventy_two schema
-- Run AFTER add-seventy-two-schema.sql
--
-- In Supabase SQL Editor you must run each block separately,
-- OR set the search path and paste the insert files manually.
--
-- Step 1: Set search path so INSERT statements hit the right schema
-- =============================================================
SET search_path TO seventy_two;

-- Step 2: Paste the contents of:
--   ~/projects/72somewhere/data/sql/cities_insert.sql
-- here (or run it as a separate query after setting search_path above)

-- Step 3: Paste the contents of:
--   ~/projects/72somewhere/data/sql/climate_insert.sql
-- here

-- Reset search path when done
RESET search_path;

-- Verify row counts
SELECT 'cities' AS table_name, COUNT(*) AS rows FROM seventy_two.cities
UNION ALL
SELECT 'climate', COUNT(*) FROM seventy_two.climate;

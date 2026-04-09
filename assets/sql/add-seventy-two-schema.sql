-- =============================================================
-- Add 72somewhere data as a separate schema in ClueChain's project
-- Run this ONCE in the ClueChain Supabase SQL Editor
-- =============================================================

-- 1. Create the schema
CREATE SCHEMA IF NOT EXISTS seventy_two;

-- 2. Create tables inside that schema
CREATE TABLE IF NOT EXISTS seventy_two.cities (
  id TEXT PRIMARY KEY,
  city TEXT NOT NULL,
  city_ascii TEXT NOT NULL,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  country TEXT NOT NULL,
  iso2 TEXT,
  iso3 TEXT,
  admin_name TEXT,
  capital TEXT,
  population NUMERIC
);

CREATE TABLE IF NOT EXISTS seventy_two.climate (
  city_id TEXT NOT NULL,
  city_name TEXT NOT NULL,
  country TEXT NOT NULL,
  month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
  avg_high_temp_c REAL NOT NULL,
  avg_low_temp_c REAL NOT NULL,
  avg_precip_mm REAL NOT NULL,
  PRIMARY KEY (city_id, month),
  FOREIGN KEY (city_id) REFERENCES seventy_two.cities(id) ON DELETE CASCADE
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_72_climate_month ON seventy_two.climate(month);
CREATE INDEX IF NOT EXISTS idx_72_climate_temp_range ON seventy_two.climate(avg_high_temp_c, avg_low_temp_c);
CREATE INDEX IF NOT EXISTS idx_72_cities_country ON seventy_two.cities(country);
CREATE INDEX IF NOT EXISTS idx_72_cities_city ON seventy_two.cities(city);

-- 4. Enable RLS
ALTER TABLE seventy_two.cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE seventy_two.climate ENABLE ROW LEVEL SECURITY;

-- 5. Public read policies
CREATE POLICY "Allow public read access to cities"
  ON seventy_two.cities FOR SELECT USING (true);

CREATE POLICY "Allow public read access to climate"
  ON seventy_two.climate FOR SELECT USING (true);

-- 6. Grant usage on the schema to anon and authenticated roles
GRANT USAGE ON SCHEMA seventy_two TO anon, authenticated;
GRANT SELECT ON seventy_two.cities TO anon, authenticated;
GRANT SELECT ON seventy_two.climate TO anon, authenticated;

-- Verify
SELECT 'seventy_two schema ready' AS status;

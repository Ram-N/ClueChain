/**
 * @fileoverview Supabase configuration for ClueChain
 * Contains Supabase client setup and environment configuration
 */

// Supabase configuration
const SUPABASE_CONFIG = {
  // Replace these with your actual Supabase project credentials
  url: "https://hcqmgifbjtzfotbwrdwi.supabase.co", // e.g., 'https://xyzcompany.supabase.co'
  anonKey:
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhjcW1naWZianR6Zm90YndyZHdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0OTQ3ODIsImV4cCI6MjA3OTA3MDc4Mn0.UZJrezVD9nciKsPBJl9QygQCPnjVYVCjZhNFMoGvZO0", // Your anon/public key

  // Optional: Configure additional settings
  auth: {
    persistSession: true,
    detectSessionInUrl: true,
    autoRefreshToken: true,
    flowType: "pkce",
  },

  // Database settings
  db: {
    schema: "public",
  },
};

// Environment detection
const isProduction =
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1";

// Export configuration
window.SUPABASE_CONFIG = SUPABASE_CONFIG;
window.IS_PRODUCTION = isProduction;

// For local development, you might want to override these values
if (!isProduction) {
  console.log("🔧 Development mode detected");
  console.log(
    "📝 Make sure to replace SUPABASE_CONFIG values with your actual credentials"
  );
}

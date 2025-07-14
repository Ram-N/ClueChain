/**
 * @fileoverview Supabase configuration for ClueChain
 * Contains Supabase client setup and environment configuration
 */

// Supabase configuration
const SUPABASE_CONFIG = {
  // Replace these with your actual Supabase project credentials
  url: "https://igciaraalmffljhbbwhi.supabase.co", // e.g., 'https://xyzcompany.supabase.co'
  anonKey:
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlnY2lhcmFhbG1mZmxqaGJid2hpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI1MDgwOTgsImV4cCI6MjA2ODA4NDA5OH0.lkaHPXOkQnsa0b2KPGIxjCJK_vdYXy2A5ryfjD968fY", // Your anon/public key

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

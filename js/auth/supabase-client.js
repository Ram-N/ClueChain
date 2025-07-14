/**
 * @fileoverview Supabase client setup and initialization
 * Handles Supabase client creation and basic configuration
 */

// Supabase client instance
let supabaseClient = null;

/**
 * Initialize Supabase client
 * @returns {Object} Supabase client instance
 */
function initializeSupabaseClient() {
  if (supabaseClient) {
    return supabaseClient;
  }

  // Check if Supabase is loaded
  if (typeof supabase === 'undefined') {
    throw new Error('Supabase library not loaded. Make sure to include the Supabase CDN script.');
  }

  // Check if configuration is available
  if (!window.SUPABASE_CONFIG) {
    throw new Error('Supabase configuration not found. Make sure supabase-config.js is loaded.');
  }

  const { url, anonKey, auth, db } = window.SUPABASE_CONFIG;

  // Validate configuration
  if (!url || url === 'YOUR_SUPABASE_URL') {
    throw new Error('Please configure your Supabase URL in supabase-config.js');
  }

  if (!anonKey || anonKey === 'YOUR_SUPABASE_ANON_KEY') {
    throw new Error('Please configure your Supabase anon key in supabase-config.js');
  }

  try {
    // Create Supabase client
    supabaseClient = supabase.createClient(url, anonKey, {
      auth: {
        persistSession: auth.persistSession,
        detectSessionInUrl: auth.detectSessionInUrl,
        autoRefreshToken: auth.autoRefreshToken,
        flowType: auth.flowType
      },
      db: {
        schema: db.schema
      }
    });

    console.log('✅ Supabase client initialized successfully');
    return supabaseClient;
  } catch (error) {
    console.error('❌ Failed to initialize Supabase client:', error);
    throw error;
  }
}

/**
 * Get Supabase client instance
 * @returns {Object} Supabase client
 */
function getSupabaseClient() {
  if (!supabaseClient) {
    return initializeSupabaseClient();
  }
  return supabaseClient;
}

/**
 * Test Supabase connection
 * @returns {Promise<boolean>} Connection test result
 */
async function testSupabaseConnection() {
  try {
    const client = getSupabaseClient();
    
    // Test connection by trying to get auth user
    const { data: { session }, error } = await client.auth.getSession();
    
    if (error) {
      console.warn('⚠️ Supabase connection test warning:', error.message);
      return false;
    }
    
    console.log('✅ Supabase connection test passed');
    return true;
  } catch (error) {
    console.error('❌ Supabase connection test failed:', error);
    return false;
  }
}

/**
 * Check if required database tables exist
 * @returns {Promise<Object>} Database schema check result
 */
async function checkDatabaseSchema() {
  try {
    const client = getSupabaseClient();
    console.log('🔍 Checking database schema...');
    
    const results = {
      tables: {},
      triggers: {},
      policies: {},
      errors: []
    };
    
    // Check if tables exist
    const tablesToCheck = ['profiles', 'user_activities', 'user_streaks', 'game_scores'];
    
    for (const table of tablesToCheck) {
      try {
        const { data, error } = await client
          .from(table)
          .select('*')
          .limit(1);
        
        if (error) {
          console.error(`❌ Table '${table}' error:`, error.message);
          results.tables[table] = false;
          results.errors.push(`Table '${table}': ${error.message}`);
        } else {
          console.log(`✅ Table '${table}' exists`);
          results.tables[table] = true;
        }
      } catch (err) {
        console.error(`❌ Table '${table}' check failed:`, err);
        results.tables[table] = false;
        results.errors.push(`Table '${table}': ${err.message}`);
      }
    }
    
    // Check if we can query information_schema for more details
    try {
      const { data: tableInfo, error: tableError } = await client
        .rpc('get_table_info')
        .select('*');
      
      if (tableError) {
        console.log('ℹ️ Cannot query table info (expected if RPC not created):', tableError.message);
      } else {
        console.log('📊 Table info:', tableInfo);
      }
    } catch (err) {
      console.log('ℹ️ Table info query not available (this is normal)');
    }
    
    // Summary
    const existingTables = Object.entries(results.tables).filter(([_, exists]) => exists).map(([table]) => table);
    const missingTables = Object.entries(results.tables).filter(([_, exists]) => !exists).map(([table]) => table);
    
    console.log('📋 Database Schema Summary:');
    console.log(`✅ Existing tables: ${existingTables.join(', ') || 'None'}`);
    console.log(`❌ Missing tables: ${missingTables.join(', ') || 'None'}`);
    
    if (results.errors.length > 0) {
      console.log('🚨 Errors found:');
      results.errors.forEach(error => console.log(`  - ${error}`));
    }
    
    return results;
  } catch (error) {
    console.error('❌ Database schema check failed:', error);
    return { error: error.message };
  }
}

/**
 * Test if user can be created (tests the full auth flow)
 * @returns {Promise<boolean>} User creation test result
 */
async function testUserCreation() {
  try {
    const client = getSupabaseClient();
    console.log('🔍 Testing user creation capabilities...');
    
    // Try to access the profiles table specifically
    const { data, error } = await client
      .from('profiles')
      .select('id, email, created_at')
      .limit(1);
    
    if (error) {
      console.error('❌ Profiles table access failed:', error.message);
      console.log('💡 This is likely why OAuth fails - the profiles table needs to be created');
      return false;
    }
    
    console.log('✅ Profiles table is accessible');
    console.log('📊 Sample profiles data:', data);
    return true;
  } catch (error) {
    console.error('❌ User creation test failed:', error);
    return false;
  }
}

/**
 * Test Row Level Security policies
 * @returns {Promise<boolean>} RLS test result
 */
async function testRLSPolicies() {
  try {
    const client = getSupabaseClient();
    console.log('🔍 Testing Row Level Security policies...');
    
    // Test if we can insert into profiles (this is what fails during OAuth)
    const testUserId = '00000000-0000-0000-0000-000000000000'; // Dummy UUID
    
    const { data, error } = await client
      .from('profiles')
      .insert({
        id: testUserId,
        email: 'test@example.com',
        full_name: 'Test User',
        display_name: 'Test User'
      })
      .select();
    
    if (error) {
      console.error('❌ Profile insert test failed:', error.message);
      console.log('💡 This is likely why OAuth fails - RLS policies may be blocking user creation');
      
      // Check if it's an RLS policy issue
      if (error.message.includes('policy') || error.message.includes('RLS') || error.message.includes('permission')) {
        console.log('🚨 This appears to be a Row Level Security (RLS) policy issue');
        console.log('🔧 You may need to check your RLS policies for the profiles table');
      }
      
      return false;
    }
    
    console.log('✅ Profile insert test successful');
    console.log('📊 Inserted test profile:', data);
    
    // Clean up - delete the test record
    const { error: deleteError } = await client
      .from('profiles')
      .delete()
      .eq('id', testUserId);
    
    if (deleteError) {
      console.warn('⚠️ Could not clean up test profile:', deleteError.message);
    } else {
      console.log('🧹 Test profile cleaned up successfully');
    }
    
    return true;
  } catch (error) {
    console.error('❌ RLS test failed:', error);
    return false;
  }
}

/**
 * Test OAuth signup flow simulation
 * @returns {Promise<boolean>} OAuth signup test result
 */
async function testOAuthSignupFlow() {
  try {
    const client = getSupabaseClient();
    console.log('🔍 Testing OAuth signup flow simulation...');
    
    // Simulate what happens during OAuth signup
    // Check if we can access auth.users table indirectly
    const { data: { user }, error } = await client.auth.getUser();
    
    if (error) {
      console.log('ℹ️ No current user (expected):', error.message);
    } else if (user) {
      console.log('ℹ️ Current user exists:', user.email);
    }
    
    return true;
  } catch (error) {
    console.error('❌ OAuth signup flow test failed:', error);
    return false;
  }
}

/**
 * Test if the trigger system is working by manually calling it
 * @returns {Promise<boolean>} Trigger test result
 */
async function testTriggerSystem() {
  try {
    const client = getSupabaseClient();
    console.log('🔍 Testing trigger system...');
    
    // Test if we can call the trigger function directly
    const testUserId = '11111111-1111-1111-1111-111111111111';
    
    // Try to manually call the handle_new_user function
    const { data: triggerData, error: triggerError } = await client
      .rpc('handle_new_user');
    
    if (triggerError) {
      console.log('ℹ️ Cannot call trigger function directly:', triggerError.message);
    } else {
      console.log('📊 Trigger function result:', triggerData);
    }
    
    // Test if we can insert a user manually (this simulates what auth.users INSERT would do)
    console.log('🔍 Testing manual profile creation...');
    
    const { data: insertData, error: insertError } = await client
      .from('profiles')
      .insert({
        id: testUserId,
        email: 'trigger-test@example.com',
        full_name: 'Trigger Test User',
        display_name: 'Trigger Test'
      })
      .select();
    
    if (insertError) {
      console.error('❌ Manual profile creation failed:', insertError.message);
      return false;
    }
    
    console.log('✅ Manual profile creation successful:', insertData);
    
    // Clean up
    const { error: deleteError } = await client
      .from('profiles')
      .delete()
      .eq('id', testUserId);
    
    if (deleteError) {
      console.warn('⚠️ Could not clean up test profile:', deleteError.message);
    } else {
      console.log('🧹 Test profile cleaned up successfully');
    }
    
    return true;
  } catch (error) {
    console.error('❌ Trigger system test failed:', error);
    return false;
  }
}

// Export functions
window.SupabaseClient = {
  initialize: initializeSupabaseClient,
  get: getSupabaseClient,
  testConnection: testSupabaseConnection,
  checkDatabaseSchema: checkDatabaseSchema,
  testUserCreation: testUserCreation,
  testRLSPolicies: testRLSPolicies,
  testOAuthSignupFlow: testOAuthSignupFlow,
  testTriggerSystem: testTriggerSystem
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  try {
    initializeSupabaseClient();
  } catch (error) {
    console.error('Failed to auto-initialize Supabase:', error);
  }
});
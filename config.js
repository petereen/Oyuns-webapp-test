// Supabase Configuration
// Replace these with your actual Supabase credentials
// IMPORTANT: Use the 'anon' (public) key, NOT the 'service_role' key
const SUPABASE_CONFIG = {
    url: "https://fblvzsxuyamfvgrfcstj.supabase.co",
    // Get this from Supabase Dashboard > Settings > API > anon/public key
    anonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZibHZ6c3h1eWFtZnZncmZjc3RqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE2MjM3MjAsImV4cCI6MjA2NzE5OTcyMH0.wcHST0WAuhPXejk5NiDD7Nd8o79KbuUlr4sXi3CfGU4"
};

// Exchange Constants (matching Python bot)
const MIN_RUB = 1000;
const MIN_VOLUME_RUB = 50000;
const MIN_VOLUME_RUB_2 = 100000;
const VOLUME_DISCOUNT_MNT = 0.2;
const VOLUME_DISCOUNT_MNT_2 = 0.3;

// Quick Amount Options
const QUICK_AMOUNTS_RUB = [1000, 5000, 10000, 20000, 30000];
const QUICK_AMOUNTS_MNT = [100000, 250000, 500000, 1000000, 3000000];

// Telegram Auth Bypass (for local testing only)
const TELEGRAM_AUTH_BYPASS = {
    enabled: false,                // Set true to force bypass without query param
    queryParam: 'tg-bypass',       // ?tg-bypass=1 enables, ?tg-bypass=0 disables
    storageKey: 'oyuns-tg-bypass', // Remembers preference between reloads
    skipVerification: true,        // Skip Supabase verification checks when bypassed
    user: {
        id: 999999999,
        first_name: 'Local',
        last_name: 'Tester',
        username: 'oyuns_dev',
        language_code: 'mn'
    }
};


import os
from supabase import create_client

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize database tables if they don't exist
def init_db():
    """
    Initialize database tables if they don't exist
    """
    try:
        # Check if users table exists
        users_query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            coins INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 100,
            max_energy INTEGER DEFAULT 100,
            tap_power INTEGER DEFAULT 1,
            energy_regen_rate INTEGER DEFAULT 1,
            last_energy_update BIGINT,
            referred_by TEXT,
            referral_count INTEGER DEFAULT 0,
            referral_earnings INTEGER DEFAULT 0,
            upi_id TEXT
        );
        """
        
        # Check if withdrawals table exists
        withdrawals_query = """
        CREATE TABLE IF NOT EXISTS withdrawals (
            id TEXT PRIMARY KEY,
            telegram_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            rupee_amount FLOAT NOT NULL,
            fee FLOAT NOT NULL,
            final_amount FLOAT NOT NULL,
            upi_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at BIGINT
        );
        """
        
        # Check if referred_users table exists
        referred_users_query = """
        CREATE TABLE IF NOT EXISTS referred_users (
            id SERIAL PRIMARY KEY,
            referrer_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT,
            name TEXT,
            joined_date BIGINT,
            earnings_from_referral INTEGER DEFAULT 0
        );
        """
        
        # Check if minigame_rewards table exists
        minigame_rewards_query = """
        CREATE TABLE IF NOT EXISTS minigame_rewards (
            id SERIAL PRIMARY KEY,
            telegram_id TEXT NOT NULL,
            game_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            timestamp BIGINT
        );
        """
        
        # Execute queries
        supabase.table('users').select('id').limit(1).execute()
        supabase.table('withdrawals').select('id').limit(1).execute()
        supabase.table('referred_users').select('id').limit(1).execute()
        supabase.table('minigame_rewards').select('id').limit(1).execute()
        
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        
        # Try to create tables using SQL
        try:
            supabase.sql(users_query).execute()
            supabase.sql(withdrawals_query).execute()
            supabase.sql(referred_users_query).execute()
            supabase.sql(minigame_rewards_query).execute()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {str(e)}")

# Initialize database on import
init_db()


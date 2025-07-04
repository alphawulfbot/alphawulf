import os
from supabase import create_client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

# Use service key if available, otherwise use anon key
SUPABASE_KEY = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY

try:
    # Create Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client created successfully")
    
    # Check if tables exist
    try:
        users_response = supabase.table("users").select("id").limit(1).execute()
        logger.info("Users table exists")
    except Exception as e:
        logger.error(f"Error checking users table: {str(e)}")
        logger.error("Please create the users table in Supabase with these columns:")
        logger.error("- id (serial, primary key)")
        logger.error("- telegram_id (text, unique)")
        logger.error("- username (text)")
        logger.error("- first_name (text)")
        logger.error("- coins (integer)")
        logger.error("- energy (integer)")
        logger.error("- max_energy (integer)")
        logger.error("- tap_power (integer)")
        logger.error("- energy_regen_rate (integer)")
        logger.error("- last_energy_update (bigint)")
        logger.error("- referred_by (text)")
        logger.error("- referral_count (integer)")
        logger.error("- referral_earnings (integer)")
        logger.error("- upi_id (text)")
    
    try:
        withdrawals_response = supabase.table("withdrawals").select("id").limit(1).execute()
        logger.info("Withdrawals table exists")
    except Exception as e:
        logger.error(f"Error checking withdrawals table: {str(e)}")
        logger.error("Please create the withdrawals table in Supabase with these columns:")
        logger.error("- id (serial, primary key)")
        logger.error("- user_id (text)")
        logger.error("- amount (integer)")
        logger.error("- upi_id (text)")
        logger.error("- status (text)")
        logger.error("- created_at (timestamp with time zone)")
    
    try:
        referred_users_response = supabase.table("referred_users").select("id").limit(1).execute()
        logger.info("Referred users table exists")
    except Exception as e:
        logger.error(f"Error checking referred_users table: {str(e)}")
        logger.error("Please create the referred_users table in Supabase with these columns:")
        logger.error("- id (serial, primary key)")
        logger.error("- referrer_id (text)")
        logger.error("- user_id (text)")
        logger.error("- username (text)")
        logger.error("- name (text)")
        logger.error("- joined_date (bigint)")
        logger.error("- earnings_from_referral (integer)")
    
    try:
        minigame_rewards_response = supabase.table("minigame_rewards").select("id").limit(1).execute()
        logger.info("Minigame rewards table exists")
    except Exception as e:
        logger.error(f"Error checking minigame_rewards table: {str(e)}")
        logger.error("Please create the minigame_rewards table in Supabase with these columns:")
        logger.error("- id (serial, primary key)")
        logger.error("- telegram_id (text)")
        logger.error("- game_name (text)")
        logger.error("- amount (integer)")
        logger.error("- timestamp (bigint)")
    
except Exception as e:
    logger.error(f"Error creating Supabase client: {str(e)}")
    logger.error(f"SUPABASE_URL: {SUPABASE_URL}")
    logger.error(f"SUPABASE_KEY: {'Set' if SUPABASE_KEY else 'Not set'}")
    
    # Create a mock client for development/testing
    class MockSupabase:
        def table(self, table_name):
            return self
        
        def select(self, *args):
            return self
        
        def insert(self, data):
            return self
        
        def update(self, data):
            return self
        
        def delete(self):
            return self
        
        def eq(self, column, value):
            return self
        
        def order(self, column, desc=False):
            return self
        
        def limit(self, limit):
            return self
        
        def execute(self):
            return type('obj', (object,), {
                'data': []
            })


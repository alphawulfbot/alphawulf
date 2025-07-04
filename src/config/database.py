import os
from supabase import create_client
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # Using the correct environment variable name

# Check if credentials are available
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables are missing!")
    # Try alternative environment variable names
    if not SUPABASE_KEY:
        SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
        if SUPABASE_KEY:
            logger.info("Using SUPABASE_KEY instead of SUPABASE_SERVICE_KEY")

# Create Supabase client
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client created successfully")
except Exception as e:
    logger.error(f"Error creating Supabase client: {str(e)}")
    raise  # Re-raise the exception to ensure the application fails if database connection fails

# Initialize database tables if they don't exist
def init_db():
    """
    Initialize database tables if they don't exist
    """
    try:
        # Create tables using REST API since SQL method is not available
        
        # Create users table with all required fields
        try:
            # First check if the table exists by trying to select from it
            supabase.table('users').select('id').limit(1).execute()
            logger.info("Users table exists")
        except Exception as e:
            logger.warning(f"Error checking users table: {str(e)}")
            logger.info("Creating users table...")
            
            # Create users table using REST API
            # First, we need to create the table in Supabase using the dashboard
            # Then we can add data to it
            
            # For now, let's try to create a test user to see if the table exists
            test_user = {
                'telegram_id': 'test_user',
                'username': 'test_user',
                'first_name': 'Test User',
                'coins': 0,
                'energy': 100,
                'max_energy': 100,
                'tap_power': 1,
                'energy_regen_rate': 1,
                'last_energy_update': int(time.time()),
                'referral_count': 0,
                'referral_earnings': 0,
                'upi_id': ''
            }
            
            try:
                supabase.table('users').insert(test_user).execute()
                logger.info("Test user created successfully")
            except Exception as e:
                logger.error(f"Error creating test user: {str(e)}")
                
                # If the error is about missing columns, we need to add them
                if "Could not find the 'upi_id' column" in str(e):
                    logger.info("Adding missing columns to users table...")
                    
                    # Use REST API to get the current schema
                    try:
                        # First, get a user to see what columns exist
                        response = supabase.table('users').select('*').limit(1).execute()
                        if response.data and len(response.data) > 0:
                            existing_user = response.data[0]
                            logger.info(f"Existing user columns: {existing_user.keys()}")
                            
                            # Check which columns are missing
                            missing_columns = []
                            for column in test_user.keys():
                                if column not in existing_user:
                                    missing_columns.append(column)
                            
                            logger.info(f"Missing columns: {missing_columns}")
                            
                            # For each missing column, we need to add it
                            # This requires direct SQL access, which we don't have
                            # So we'll need to instruct the user to add these columns manually
                            if missing_columns:
                                logger.error("Missing columns detected. Please add these columns to the users table in Supabase:")
                                for column in missing_columns:
                                    logger.error(f"- {column}")
                    except Exception as e2:
                        logger.error(f"Error checking existing columns: {str(e2)}")
        
        # Similarly for other tables
        try:
            # Check if withdrawals table exists
            supabase.table('withdrawals').select('id').limit(1).execute()
            logger.info("Withdrawals table exists")
        except Exception as e:
            logger.warning(f"Error checking withdrawals table: {str(e)}")
            logger.error("Please create the withdrawals table in Supabase with these columns:")
            logger.error("- id (text, primary key)")
            logger.error("- telegram_id (text)")
            logger.error("- amount (integer)")
            logger.error("- rupee_amount (float)")
            logger.error("- fee (float)")
            logger.error("- final_amount (float)")
            logger.error("- upi_id (text)")
            logger.error("- status (text)")
            logger.error("- created_at (bigint)")
        
        try:
            # Check if referred_users table exists
            supabase.table('referred_users').select('id').limit(1).execute()
            logger.info("Referred users table exists")
        except Exception as e:
            logger.warning(f"Error checking referred_users table: {str(e)}")
            logger.error("Please create the referred_users table in Supabase with these columns:")
            logger.error("- id (serial, primary key)")
            logger.error("- referrer_id (text)")
            logger.error("- user_id (text)")
            logger.error("- username (text)")
            logger.error("- name (text)")
            logger.error("- joined_date (bigint)")
            logger.error("- earnings_from_referral (integer)")
        
        try:
            # Check if minigame_rewards table exists
            supabase.table('minigame_rewards').select('id').limit(1).execute()
            logger.info("Minigame rewards table exists")
        except Exception as e:
            logger.warning(f"Error checking minigame_rewards table: {str(e)}")
            logger.error("Please create the minigame_rewards table in Supabase with these columns:")
            logger.error("- id (serial, primary key)")
            logger.error("- telegram_id (text)")
            logger.error("- game_name (text)")
            logger.error("- amount (integer)")
            logger.error("- timestamp (bigint)")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

# Initialize database on import
try:
    init_db()
except Exception as e:
    logger.error(f"Database initialization failed: {str(e)}")
    logger.warning("Application will run in limited mode without database functionality")


import os
import time
from datetime import datetime
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def safe_int_conversion(value, default=0):
    """Safely convert value to integer, handling various input types"""
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        return int(value)
    
    if isinstance(value, str):
        try:
            # Handle datetime strings by converting to Unix timestamp
            if 'T' in value or '-' in value:
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                except:
                    pass
            
            # Try direct conversion
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    return default

def safe_timestamp_conversion(value):
    """Safely convert value to Unix timestamp"""
    if value is None:
        return int(time.time())
    
    if isinstance(value, (int, float)):
        # If it's already a reasonable timestamp, return it
        if value > 1000000000:  # After year 2001
            return int(value)
        else:
            return int(time.time())
    
    if isinstance(value, str):
        try:
            # Handle datetime strings
            if 'T' in value or '-' in value:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return int(dt.timestamp())
            else:
                # Try direct conversion
                timestamp = int(float(value))
                return timestamp if timestamp > 1000000000 else int(time.time())
        except (ValueError, TypeError):
            return int(time.time())
    
    return int(time.time())

class User:
    def __init__(self, telegram_id, username=None, first_name=None, last_name=None):
        self.telegram_id = safe_int_conversion(telegram_id)
        self.username = username or ""
        self.first_name = first_name or ""
        self.last_name = last_name or ""
        
        # Game stats with 1000 coin joining bonus
        self.coins = 1000
        self.energy = 100
        self.max_energy = 100
        self.tap_power = 1
        self.power = 1
        self.energy_regen_rate = 1
        
        # Timestamps
        self.last_energy_update = int(time.time())
        self.last_tap_time = int(time.time())
        self.created_at = int(time.time())
        self.updated_at = int(time.time())
        
        # Additional fields
        self.is_admin = False
        self.referral_code = ""
        self.referred_by = None
        self.referral_count = 0
        self.referral_earnings = 0
        self.referrals = ""
        
        logger.info(f"User initialized: {self.telegram_id} with 1000 coins joining bonus")

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by Telegram ID"""
        try:
            telegram_id = safe_int_conversion(telegram_id)
            logger.info(f"Fetching user with telegram_id: {telegram_id}")
            
            response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"User found: {telegram_id}")
                
                # Create user instance
                user = cls.__new__(cls)
                user.telegram_id = safe_int_conversion(user_data.get('telegram_id'))
                user.username = user_data.get('username', '')
                user.first_name = user_data.get('first_name', '')
                user.last_name = user_data.get('last_name', '')
                
                # Game stats
                user.coins = safe_int_conversion(user_data.get('coins'), 1000)
                user.energy = safe_int_conversion(user_data.get('energy'), 100)
                user.max_energy = safe_int_conversion(user_data.get('max_energy'), 100)
                user.tap_power = safe_int_conversion(user_data.get('tap_power'), 1)
                user.power = safe_int_conversion(user_data.get('power'), 1)
                user.energy_regen_rate = safe_int_conversion(user_data.get('energy_regen_rate'), 1)
                
                # Timestamps
                user.last_energy_update = safe_timestamp_conversion(user_data.get('last_energy_update'))
                user.last_tap_time = safe_timestamp_conversion(user_data.get('last_tap_time'))
                user.created_at = safe_timestamp_conversion(user_data.get('created_at'))
                user.updated_at = safe_timestamp_conversion(user_data.get('updated_at'))
                
                # Additional fields
                user.is_admin = bool(user_data.get('is_admin', False))
                user.referral_code = user_data.get('referral_code', '')
                user.referred_by = safe_int_conversion(user_data.get('referred_by')) if user_data.get('referred_by') else None
                user.referral_count = safe_int_conversion(user_data.get('referral_count'), 0)
                user.referral_earnings = safe_int_conversion(user_data.get('referral_earnings'), 0)
                user.referrals = user_data.get('referrals', '')
                
                return user
            else:
                logger.info(f"User not found: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {str(e)}")
            return None

    def save(self):
        """Save user to database"""
        try:
            current_time = int(time.time())
            self.updated_at = current_time
            
            # Prepare data with explicit type conversion
            user_data = {
                'telegram_id': int(self.telegram_id),
                'username': str(self.username),
                'first_name': str(self.first_name),
                'last_name': str(self.last_name),
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'power': int(self.power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'last_energy_update': int(self.last_energy_update),
                'last_tap_time': int(self.last_tap_time),
                'created_at': int(self.created_at),
                'updated_at': int(self.updated_at),
                'is_admin': bool(self.is_admin),
                'referral_code': str(self.referral_code),
                'referred_by': int(self.referred_by) if self.referred_by else None,
                'referral_count': int(self.referral_count),
                'referral_earnings': int(self.referral_earnings),
                'referrals': str(self.referrals)
            }
            
            logger.info(f"Saving user {self.telegram_id} with timestamps: last_energy_update={self.last_energy_update} last_tap_time={self.last_tap_time} updated_at={self.updated_at}")
            
            # Try to update existing user first
            response = supabase.table('users').update(user_data).eq('telegram_id', self.telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"User {self.telegram_id} updated successfully")
                return True
            else:
                # If update didn't affect any rows, try insert
                response = supabase.table('users').insert(user_data).execute()
                if response.data and len(response.data) > 0:
                    logger.info(f"User {self.telegram_id} created successfully")
                    return True
                else:
                    logger.error(f"Failed to save user {self.telegram_id}: No data returned")
                    return False
                    
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {str(e)}")
            return False

    def update_energy(self):
        """Update energy based on time passed"""
        try:
            current_time = int(time.time())
            time_diff = current_time - self.last_energy_update
            
            if time_diff > 0:
                # Regenerate energy (2 energy per minute based on regen rate)
                minutes_passed = time_diff / 60
                energy_to_add = int(minutes_passed * self.energy_regen_rate * 2)
                
                if energy_to_add > 0:
                    old_energy = self.energy
                    self.energy = min(self.max_energy, self.energy + energy_to_add)
                    self.last_energy_update = current_time
                    
                    logger.info(f"Energy updated for user {self.telegram_id}: {old_energy} -> {self.energy} (+{energy_to_add} energy)")
                    
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {str(e)}")

    def tap(self):
        """Process a tap action"""
        try:
            # Update energy first
            self.update_energy()
            
            if self.energy <= 0:
                return False, "Not enough energy"
            
            # Process tap
            self.energy = max(0, self.energy - 1)
            self.coins += self.tap_power
            self.last_tap_time = int(time.time())
            
            logger.info(f"User {self.telegram_id} tapped: +{self.tap_power} coins, energy: {self.energy}")
            
            # Save to database
            if self.save():
                return True, f"Earned {self.tap_power} coins"
            else:
                return False, "Failed to save tap result"
                
        except Exception as e:
            logger.error(f"Error processing tap for user {self.telegram_id}: {str(e)}")
            return False, "Tap processing failed"

    def play_game(self, game_type, actions_count):
        """Process game result"""
        try:
            game_configs = {
                'wolfHunt': {'min_reward': 50, 'max_reward': 150},
                'packLeader': {'min_reward': 100, 'max_reward': 250},
                'howlChallenge': {'min_reward': 75, 'max_reward': 300}
            }
            
            if game_type not in game_configs:
                return False, "Invalid game type"
            
            config = game_configs[game_type]
            
            # Calculate reward based on actions
            base_reward = config['min_reward']
            bonus_reward = min(config['max_reward'] - config['min_reward'], actions_count * 10)
            total_reward = base_reward + bonus_reward
            
            # Award coins
            old_coins = self.coins
            self.coins += total_reward
            
            logger.info(f"User {self.telegram_id} completed {game_type}: +{total_reward} coins ({old_coins} -> {self.coins})")
            
            # Save to database
            if self.save():
                return True, f"Game completed! Earned {total_reward} coins"
            else:
                return False, "Failed to save game result"
                
        except Exception as e:
            logger.error(f"Error processing game for user {self.telegram_id}: {str(e)}")
            return False, "Game processing failed"

    def upgrade_feature(self, feature):
        """Upgrade a feature"""
        try:
            cost = 0
            success = False
            
            if feature == 'tap_power':
                cost = self.tap_power * 100
                if self.coins >= cost:
                    self.coins -= cost
                    self.tap_power += 1
                    self.power = self.tap_power  # Keep power in sync
                    success = True
                    
            elif feature == 'energy_capacity':
                energy_level = (self.max_energy // 10) - 9
                cost = energy_level * 200
                if self.coins >= cost:
                    self.coins -= cost
                    self.max_energy += 10
                    self.energy = min(self.energy, self.max_energy)
                    success = True
                    
            elif feature == 'energy_regen':
                cost = self.energy_regen_rate * 150
                if self.coins >= cost:
                    self.coins -= cost
                    self.energy_regen_rate += 1
                    success = True
            
            if success:
                logger.info(f"User {self.telegram_id} upgraded {feature}: cost={cost}, new_coins={self.coins}")
                
                # Save to database
                if self.save():
                    return True, f"Upgraded {feature} for {cost} coins"
                else:
                    return False, "Failed to save upgrade"
            else:
                return False, "Not enough coins for upgrade"
                
        except Exception as e:
            logger.error(f"Error upgrading {feature} for user {self.telegram_id}: {str(e)}")
            return False, "Upgrade processing failed"

    def process_withdrawal(self, amount, upi_id):
        """Process withdrawal request"""
        try:
            if amount < 1000:
                return False, "Minimum withdrawal amount is 1,000 coins"
            
            if amount > self.coins:
                return False, "Insufficient balance"
            
            # Calculate fee (2% minimum 50 coins)
            fee = max(50, int(amount * 0.02))
            
            # Deduct amount
            self.coins -= amount
            
            logger.info(f"User {self.telegram_id} withdrawal: amount={amount}, fee={fee}, remaining_coins={self.coins}")
            
            # Save to database
            if self.save():
                return True, f"Withdrawal of {amount} coins processed (fee: {fee} coins)"
            else:
                return False, "Failed to process withdrawal"
                
        except Exception as e:
            logger.error(f"Error processing withdrawal for user {self.telegram_id}: {str(e)}")
            return False, "Withdrawal processing failed"

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'coins': self.coins,
            'energy': self.energy,
            'max_energy': self.max_energy,
            'tap_power': self.tap_power,
            'power': self.power,
            'energy_regen_rate': self.energy_regen_rate,
            'last_energy_update': self.last_energy_update,
            'last_tap_time': self.last_tap_time,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_admin': self.is_admin,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'referral_count': self.referral_count,
            'referral_earnings': self.referral_earnings,
            'referrals': self.referrals
        }

class Transaction:
    """Transaction model for logging all coin activities"""
    
    @staticmethod
    def log_transaction(user_id, transaction_type, description, amount, balance_before, balance_after):
        """Log a transaction"""
        try:
            transaction_data = {
                'user_id': int(user_id),
                'transaction_type': str(transaction_type),
                'description': str(description),
                'amount': int(amount),
                'balance_before': int(balance_before),
                'balance_after': int(balance_after),
                'created_at': int(time.time()),
                'status': 'completed'
            }
            
            response = supabase.table('transactions').insert(transaction_data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Transaction logged for user {user_id}: {description} ({amount} coins)")
                return True
            else:
                logger.error(f"Failed to log transaction for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error logging transaction for user {user_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_user_transactions(user_id, limit=50):
        """Get user transactions"""
        try:
            response = supabase.table('transactions').select('*').eq('user_id', int(user_id)).order('created_at', desc=True).limit(limit).execute()
            
            if response.data:
                return response.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error fetching transactions for user {user_id}: {str(e)}")
            return []

# Helper functions for API endpoints
def create_user_from_telegram_data(telegram_data):
    """Create user from Telegram data"""
    try:
        user = User(
            telegram_id=telegram_data.get('telegram_id'),
            username=telegram_data.get('username'),
            first_name=telegram_data.get('first_name'),
            last_name=telegram_data.get('last_name')
        )
        
        if user.save():
            # Log joining bonus transaction
            Transaction.log_transaction(
                user.telegram_id,
                'bonus',
                'Joining Bonus',
                1000,
                0,
                1000
            )
            return user
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error creating user from Telegram data: {str(e)}")
        return None

def validate_user_data(data):
    """Validate user data before processing"""
    required_fields = ['telegram_id']
    
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"
    
    # Validate telegram_id is a valid integer
    try:
        int(data['telegram_id'])
    except (ValueError, TypeError):
        return False, "Invalid telegram_id format"
    
    return True, "Valid"

# Database initialization
def init_database():
    """Initialize database tables if they don't exist"""
    try:
        # Check if tables exist by trying to select from them
        supabase.table('users').select('telegram_id').limit(1).execute()
        supabase.table('transactions').select('id').limit(1).execute()
        logger.info("Database tables verified")
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        logger.info("Please ensure the following tables exist in your Supabase database:")
        logger.info("""
        CREATE TABLE users (
            telegram_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            coins BIGINT DEFAULT 1000,
            energy BIGINT DEFAULT 100,
            max_energy BIGINT DEFAULT 100,
            tap_power BIGINT DEFAULT 1,
            power BIGINT DEFAULT 1,
            energy_regen_rate BIGINT DEFAULT 1,
            last_energy_update BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
            last_tap_time BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
            created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
            updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
            is_admin BOOLEAN DEFAULT FALSE,
            referral_code TEXT DEFAULT '',
            referred_by BIGINT,
            referral_count BIGINT DEFAULT 0,
            referral_earnings BIGINT DEFAULT 0,
            referrals TEXT DEFAULT ''
        );
        
        CREATE TABLE transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_before INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            created_at BIGINT NOT NULL,
            status TEXT DEFAULT 'completed'
        );
        """)
        return False


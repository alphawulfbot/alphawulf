"""
Comprehensive User Model for Alpha Wulf
Ensures real-time data synchronization across all sections
Handles PostgreSQL type compatibility and error prevention
"""

import os
import time
from datetime import datetime
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User:
    def __init__(self, **kwargs):
        """Initialize User with safe type conversion"""
        # Core user identification
        self.telegram_id = int(kwargs.get('telegram_id', 0))
        self.username = str(kwargs.get('username', ''))
        self.first_name = str(kwargs.get('first_name', ''))
        self.last_name = str(kwargs.get('last_name', ''))
        
        # Game state with safe type conversion
        self.coins = int(float(kwargs.get('coins', 2500)))
        self.energy = int(float(kwargs.get('energy', 100)))
        self.max_energy = int(float(kwargs.get('max_energy', 100)))
        self.tap_power = int(float(kwargs.get('tap_power', 1)))
        self.energy_regen_rate = int(float(kwargs.get('energy_regen_rate', 1)))
        
        # Timestamps as integers (Unix timestamps)
        current_time = int(time.time())
        self.created_at = int(kwargs.get('created_at', current_time))
        self.updated_at = int(kwargs.get('updated_at', current_time))
        self.last_energy_update = int(kwargs.get('last_energy_update', current_time))
        
        # Referral system
        self.referral_code = str(kwargs.get('referral_code', ''))
        self.referred_by = kwargs.get('referred_by')  # Can be None
        self.total_referrals = int(kwargs.get('total_referrals', 0))
        self.referral_earnings = int(float(kwargs.get('referral_earnings', 0)))
        
        # Upgrades
        self.upgrade_level = int(kwargs.get('upgrade_level', 1))
        self.upgrade_cost = int(float(kwargs.get('upgrade_cost', 100)))
        
        # Admin flags
        self.is_admin = bool(kwargs.get('is_admin', False))
        self.is_banned = bool(kwargs.get('is_banned', False))
        
        # Initialize Supabase client
        self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase client with error handling"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logger.error("Missing Supabase credentials")
                self.supabase = None
                return
            
            self.supabase: Client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.supabase = None
    
    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by Telegram ID with error handling"""
        try:
            # Create temporary instance to access Supabase
            temp_user = cls()
            if not temp_user.supabase:
                logger.error("Supabase client not available")
                return None
            
            response = temp_user.supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"Found existing user: {telegram_id}")
                return cls(**user_data)
            else:
                logger.info(f"User not found: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
            return None
    
    @classmethod
    def create_user(cls, telegram_id, username='', first_name='', last_name=''):
        """Create new user with proper error handling"""
        try:
            # Generate referral code
            import random
            import string
            referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Create user data
            user_data = {
                'telegram_id': int(telegram_id),
                'username': str(username),
                'first_name': str(first_name),
                'last_name': str(last_name) if last_name else '',
                'coins': 2500,
                'energy': 100,
                'max_energy': 100,
                'tap_power': 1,
                'energy_regen_rate': 1,
                'created_at': int(time.time()),
                'updated_at': int(time.time()),
                'last_energy_update': int(time.time()),
                'referral_code': referral_code,
                'total_referrals': 0,
                'referral_earnings': 0,
                'upgrade_level': 1,
                'upgrade_cost': 100,
                'is_admin': False,
                'is_banned': False
            }
            
            # Create user instance
            user = cls(**user_data)
            
            # Save to database
            if user.save():
                logger.info(f"Created new user: {telegram_id}")
                return user
            else:
                logger.error(f"Failed to save new user: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None
    
    def save(self):
        """Save user data to database with comprehensive error handling"""
        try:
            if not self.supabase:
                logger.error("Supabase client not available for save")
                return False
            
            # Update timestamp
            self.updated_at = int(time.time())
            
            # Prepare data for database (ensure all types are correct)
            save_data = {
                'telegram_id': int(self.telegram_id),
                'username': str(self.username),
                'first_name': str(self.first_name),
                'last_name': str(self.last_name),
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'created_at': int(self.created_at),
                'updated_at': int(self.updated_at),
                'last_energy_update': int(self.last_energy_update),
                'referral_code': str(self.referral_code),
                'total_referrals': int(self.total_referrals),
                'referral_earnings': int(self.referral_earnings),
                'upgrade_level': int(self.upgrade_level),
                'upgrade_cost': int(self.upgrade_cost),
                'is_admin': bool(self.is_admin),
                'is_banned': bool(self.is_banned)
            }
            
            # Add referred_by only if it's not None
            if self.referred_by is not None:
                save_data['referred_by'] = int(self.referred_by)
            
            # Try to update existing user first
            response = self.supabase.table('users').update(save_data).eq('telegram_id', self.telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Updated user: {self.telegram_id}")
                return True
            else:
                # If update failed, try insert (for new users)
                response = self.supabase.table('users').insert(save_data).execute()
                if response.data and len(response.data) > 0:
                    logger.info(f"Inserted new user: {self.telegram_id}")
                    return True
                else:
                    logger.error(f"Failed to save user: {self.telegram_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {e}")
            return False
    
    def update_energy(self):
        """Update energy based on time elapsed"""
        try:
            current_time = int(time.time())
            time_diff = current_time - self.last_energy_update
            
            # Regenerate energy (1 per 30 seconds)
            energy_to_add = time_diff // 30
            
            if energy_to_add > 0:
                self.energy = min(self.max_energy, self.energy + energy_to_add)
                self.last_energy_update = current_time
                logger.info(f"Updated energy for user {self.telegram_id}: +{energy_to_add} energy")
            
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {e}")
    
    def tap(self, taps=1):
        """Process tap with energy validation"""
        try:
            # Update energy first
            self.update_energy()
            
            # Check if user has enough energy
            if self.energy >= taps:
                self.energy -= taps
                self.coins += (taps * self.tap_power)
                
                # Save changes
                if self.save():
                    logger.info(f"User {self.telegram_id} tapped {taps} times")
                    return True
                else:
                    logger.error(f"Failed to save tap for user {self.telegram_id}")
                    return False
            else:
                logger.warning(f"User {self.telegram_id} has insufficient energy for {taps} taps")
                return False
                
        except Exception as e:
            logger.error(f"Error processing tap for user {self.telegram_id}: {e}")
            return False
    
    def can_tap(self, taps=1):
        """Check if user can tap"""
        try:
            self.update_energy()
            return self.energy >= taps
        except Exception as e:
            logger.error(f"Error checking tap ability for user {self.telegram_id}: {e}")
            return False
    
    def upgrade_tap_power(self):
        """Upgrade tap power if user has enough coins"""
        try:
            if self.coins >= self.upgrade_cost:
                self.coins -= self.upgrade_cost
                self.tap_power += 1
                self.upgrade_level += 1
                self.upgrade_cost = int(self.upgrade_cost * 1.5)  # Increase cost by 50%
                
                if self.save():
                    logger.info(f"User {self.telegram_id} upgraded tap power to {self.tap_power}")
                    return True
                else:
                    logger.error(f"Failed to save upgrade for user {self.telegram_id}")
                    return False
            else:
                logger.warning(f"User {self.telegram_id} has insufficient coins for upgrade")
                return False
                
        except Exception as e:
            logger.error(f"Error upgrading tap power for user {self.telegram_id}: {e}")
            return False
    
    def add_referral(self, referred_user_id):
        """Add a referral and give bonus"""
        try:
            self.total_referrals += 1
            referral_bonus = 500  # Bonus coins for referral
            self.coins += referral_bonus
            self.referral_earnings += referral_bonus
            
            if self.save():
                logger.info(f"User {self.telegram_id} got referral bonus for user {referred_user_id}")
                return True
            else:
                logger.error(f"Failed to save referral bonus for user {self.telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding referral for user {self.telegram_id}: {e}")
            return False
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        try:
            return {
                'telegram_id': self.telegram_id,
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'coins': self.coins,
                'energy': self.energy,
                'max_energy': self.max_energy,
                'tap_power': self.tap_power,
                'energy_regen_rate': self.energy_regen_rate,
                'created_at': self.created_at,
                'updated_at': self.updated_at,
                'last_energy_update': self.last_energy_update,
                'referral_code': self.referral_code,
                'referred_by': self.referred_by,
                'total_referrals': self.total_referrals,
                'referral_earnings': self.referral_earnings,
                'upgrade_level': self.upgrade_level,
                'upgrade_cost': self.upgrade_cost,
                'is_admin': self.is_admin,
                'is_banned': self.is_banned
            }
        except Exception as e:
            logger.error(f"Error converting user {self.telegram_id} to dict: {e}")
            return {}
    
    @classmethod
    def get_all_users(cls, limit=100, offset=0):
        """Get all users for admin panel"""
        try:
            temp_user = cls()
            if not temp_user.supabase:
                logger.error("Supabase client not available")
                return []
            
            response = temp_user.supabase.table('users').select('*').range(offset, offset + limit - 1).execute()
            
            if response.data:
                users = [cls(**user_data) for user_data in response.data]
                logger.info(f"Retrieved {len(users)} users")
                return users
            else:
                logger.info("No users found")
                return []
                
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    @classmethod
    def get_user_count(cls):
        """Get total user count"""
        try:
            temp_user = cls()
            if not temp_user.supabase:
                logger.error("Supabase client not available")
                return 0
            
            response = temp_user.supabase.table('users').select('telegram_id', count='exact').execute()
            return response.count if response.count else 0
            
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0


"""
Working Comprehensive User Model for Alpha Wulf
Uses regular Supabase client with proper timestamp handling
Ensures data persistence and synchronization
"""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
def get_supabase_client() -> Optional[Client]:
    """Initialize Supabase client with error handling"""
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables not set")
            return None
            
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        return None

def safe_int_conversion(value, default=0):
    """Safely convert value to int"""
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            if not value.strip():
                return default
            # Handle timestamp strings
            if 'T' in value or '+' in value or 'Z' in value:
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                except:
                    pass
            return int(float(value))
        return default
    except (ValueError, TypeError):
        return default

def safe_bool_conversion(value, default=False):
    """Safely convert value to bool"""
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    except:
        return default

def safe_string_conversion(value, default=''):
    """Safely convert value to string"""
    try:
        if value is None:
            return default
        return str(value)
    except:
        return default

class User:
    """User model with working database operations using Supabase client"""
    
    def __init__(self, telegram_id: int, username: str = '', first_name: str = '', last_name: str = ''):
        self.telegram_id = int(telegram_id)
        self.username = username or ''
        self.first_name = first_name or ''
        self.last_name = last_name or ''
        
        # Game attributes with default values
        self.coins = 2500
        self.energy = 100
        self.max_energy = 100
        self.tap_power = 1
        self.power = 1
        self.energy_regen_rate = 1
        self.energy_recharge_rate = 1
        
        # Timestamp attributes (stored as Unix timestamps)
        current_time = int(time.time())
        self.last_energy_update = current_time
        self.last_tap_time = current_time
        self.created_at = current_time
        self.updated_at = current_time
        
        # Additional attributes
        self.is_admin = False
        self.referral_code = ''
        self.referred_by = None
        self.total_taps = 0
        self.referral_count = 0
        self.referral_earnings = 0
        self.referrals = ''
    
    @classmethod
    def get_by_telegram_id(cls, telegram_id: int):
        """Get user by telegram ID with proper error handling"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return None
                
            response = supabase.table('users').select('*').eq('telegram_id', int(telegram_id)).execute()
            
            if response.data and len(response.data) > 0:
                row = response.data[0]
                user = cls(
                    telegram_id=row['telegram_id'],
                    username=safe_string_conversion(row.get('username', '')),
                    first_name=safe_string_conversion(row.get('first_name', '')),
                    last_name=safe_string_conversion(row.get('last_name', ''))
                )
                
                # Load game data with safe type conversion
                user.coins = safe_int_conversion(row.get('coins', 2500))
                user.energy = safe_int_conversion(row.get('energy', 100))
                user.max_energy = safe_int_conversion(row.get('max_energy', 100))
                user.tap_power = safe_int_conversion(row.get('tap_power', 1))
                user.power = safe_int_conversion(row.get('power', 1))
                user.energy_regen_rate = safe_int_conversion(row.get('energy_regen_rate', 1))
                user.energy_recharge_rate = safe_int_conversion(row.get('energy_recharge_rate', 1))
                
                # Load timestamp fields with safe conversion
                current_time = int(time.time())
                user.last_energy_update = safe_int_conversion(row.get('last_energy_update', current_time))
                user.last_tap_time = safe_int_conversion(row.get('last_tap_time', current_time))
                user.created_at = safe_int_conversion(row.get('created_at', current_time))
                user.updated_at = safe_int_conversion(row.get('updated_at', current_time))
                
                # Load additional attributes
                user.is_admin = safe_bool_conversion(row.get('is_admin', False))
                user.referral_code = safe_string_conversion(row.get('referral_code', ''))
                user.referred_by = row.get('referred_by')
                user.total_taps = safe_int_conversion(row.get('total_taps', 0))
                user.referral_count = safe_int_conversion(row.get('referral_count', 0))
                user.referral_earnings = safe_int_conversion(row.get('referral_earnings', 0))
                user.referrals = safe_string_conversion(row.get('referrals', ''))
                
                logger.info(f"User found: {telegram_id}")
                return user
            else:
                logger.info(f"User not found: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None
    
    @classmethod
    def create_user(cls, telegram_id: int, username: str = '', first_name: str = '', last_name: str = ''):
        """Create new user with proper error handling"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return None
                
            user = cls(telegram_id, username, first_name, last_name)
            current_time = int(time.time())
            
            user_data = {
                'telegram_id': int(user.telegram_id),
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'coins': int(user.coins),
                'energy': int(user.energy),
                'max_energy': int(user.max_energy),
                'tap_power': int(user.tap_power),
                'power': int(user.power),
                'energy_regen_rate': int(user.energy_regen_rate),
                'energy_recharge_rate': int(user.energy_recharge_rate),
                'last_energy_update': current_time,
                'last_tap_time': current_time,
                'created_at': current_time,
                'updated_at': current_time,
                'is_admin': bool(user.is_admin),
                'referral_code': user.referral_code,
                'referred_by': user.referred_by,
                'total_taps': int(user.total_taps),
                'referral_count': int(user.referral_count),
                'referral_earnings': int(user.referral_earnings),
                'referrals': user.referrals
            }
            
            response = supabase.table('users').insert(user_data).execute()
            
            if response.data:
                logger.info(f"User created: {telegram_id}")
                return user
            else:
                logger.error(f"Failed to create user: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None
    
    def save(self):
        """Save user data with proper timestamp handling"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                logger.error("Failed to get Supabase client")
                return False
                
            # Update timestamp
            current_time = int(time.time())
            self.updated_at = current_time
            
            # Ensure all timestamps are integers
            self.last_energy_update = int(self.last_energy_update)
            self.last_tap_time = int(self.last_tap_time)
            self.created_at = int(self.created_at)
            self.updated_at = int(self.updated_at)
            
            # Prepare update data
            update_data = {
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'power': int(self.power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'energy_recharge_rate': int(self.energy_recharge_rate),
                'last_energy_update': int(self.last_energy_update),
                'last_tap_time': int(self.last_tap_time),
                'updated_at': int(self.updated_at),
                'is_admin': bool(self.is_admin),
                'referral_code': self.referral_code,
                'referred_by': self.referred_by,
                'total_taps': int(self.total_taps),
                'referral_count': int(self.referral_count),
                'referral_earnings': int(self.referral_earnings),
                'referrals': self.referrals
            }
            
            logger.info(f"Saving user {self.telegram_id} with data: coins={self.coins}, energy={self.energy}")
            
            response = supabase.table('users').update(update_data).eq('telegram_id', int(self.telegram_id)).execute()
            
            if response.data:
                logger.info(f"User saved successfully: {self.telegram_id}")
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
            now = int(time.time())
            time_diff = now - int(self.last_energy_update)
            minutes_passed = time_diff / 60
            
            # Regenerate energy (1 energy per 30 seconds = 2 energy per minute)
            energy_to_add = int(minutes_passed * 2)
            
            if energy_to_add > 0:
                self.energy = min(self.max_energy, self.energy + energy_to_add)
                self.last_energy_update = now
                logger.info(f"Energy updated for user {self.telegram_id}: +{energy_to_add} energy")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {e}")
            return False
    
    def can_tap(self):
        """Check if user can tap"""
        return self.energy > 0
    
    def tap(self, taps: int = 1):
        """Process tap with proper validation"""
        try:
            if not self.can_tap():
                return False, "No energy available"
            
            # Update energy first
            self.update_energy()
            
            # Process taps
            actual_taps = min(taps, self.energy)
            self.energy = max(0, self.energy - actual_taps)
            self.coins += actual_taps * self.tap_power
            self.total_taps += actual_taps
            self.last_tap_time = int(time.time())
            
            # Save to database
            if self.save():
                logger.info(f"Tap processed for user {self.telegram_id}: {actual_taps} taps, {self.coins} total coins")
                return True, f"Tapped {actual_taps} times"
            else:
                return False, "Failed to save tap data"
                
        except Exception as e:
            logger.error(f"Error processing tap for user {self.telegram_id}: {e}")
            return False, f"Tap error: {str(e)}"
    
    def to_dict(self):
        """Convert user to dictionary"""
        try:
            return {
                'telegram_id': int(self.telegram_id),
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'power': int(self.power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'energy_recharge_rate': int(self.energy_recharge_rate),
                'last_energy_update': int(self.last_energy_update),
                'last_tap_time': int(self.last_tap_time),
                'created_at': int(self.created_at),
                'updated_at': int(self.updated_at),
                'is_admin': bool(self.is_admin),
                'referral_code': self.referral_code,
                'referred_by': self.referred_by,
                'total_taps': int(self.total_taps),
                'referral_count': int(self.referral_count),
                'referral_earnings': int(self.referral_earnings),
                'referrals': self.referrals
            }
        except Exception as e:
            logger.error(f"Error converting user to dict: {e}")
            return {
                'telegram_id': int(self.telegram_id),
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'coins': 2500,
                'energy': 100,
                'max_energy': 100,
                'tap_power': 1,
                'power': 1,
                'energy_regen_rate': 1,
                'energy_recharge_rate': 1,
                'last_energy_update': int(time.time()),
                'last_tap_time': int(time.time()),
                'created_at': int(time.time()),
                'updated_at': int(time.time())
            }


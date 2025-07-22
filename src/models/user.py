from datetime import datetime, timezone
import logging
from src.config.database import supabase

logger = logging.getLogger(__name__)

class User:
    def __init__(self, id=None, telegram_id=None, username=None, first_name=None, 
                 last_name=None, coins=0, energy=100, max_energy=100, tap_power=1, 
                 energy_regen_rate=1, total_taps=0, referral_code=None, referred_by=None, 
                 referral_count=0, referral_earnings=0, created_at=None, updated_at=None, 
                 upi_id=None, last_energy_update=None):
        self.id = id
        self.telegram_id = int(telegram_id) if telegram_id else None
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.coins = int(float(coins)) if coins is not None else 0
        self.energy = int(float(energy)) if energy is not None else 100
        self.max_energy = int(float(max_energy)) if max_energy is not None else 100
        self.tap_power = int(float(tap_power)) if tap_power is not None else 1
        self.energy_regen_rate = int(float(energy_regen_rate)) if energy_regen_rate is not None else 1
        self.total_taps = int(float(total_taps)) if total_taps is not None else 0
        self.referral_code = referral_code
        self.referred_by = referred_by
        self.referral_count = int(float(referral_count)) if referral_count is not None else 0
        self.referral_earnings = int(float(referral_earnings)) if referral_earnings is not None else 0
        self.created_at = created_at
        self.updated_at = updated_at
        self.upi_id = upi_id
        # Handle last_energy_update from database
        if last_energy_update is not None:
            if isinstance(last_energy_update, (int, float)):
                self.last_energy_update = int(last_energy_update)
            else:
                self.last_energy_update = int(datetime.now(timezone.utc).timestamp())
        else:
            self.last_energy_update = int(datetime.now(timezone.utc).timestamp())
        
        logger.info(f"User initialized: {self.telegram_id}, coins: {self.coins}, energy: {self.energy}")

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by telegram ID"""
        try:
            telegram_id = int(telegram_id)
            logger.info(f"Searching for user with telegram_id: {telegram_id}")
            
            response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"User found: {user_data}")
                return cls(**user_data)
            else:
                logger.info(f"No user found with telegram_id: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {str(e)}")
            return None

    @classmethod
    def create_user(cls, telegram_id, username=None, first_name=None, last_name=None):
        """Create a new user"""
        try:
            telegram_id = int(telegram_id)
            
            user_data = {
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'coins': 2500,  # Starting coins
                'energy': 100,
                'max_energy': 100,
                'tap_power': 1,
                'energy_regen_rate': 1,
                'total_taps': 0,
                'referral_count': 0,
                'referral_earnings': 0,
                'last_energy_update': int(datetime.now(timezone.utc).timestamp())
            }
            
            response = supabase.table('users').insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"User created: {response.data[0]}")
                return cls(**response.data[0])
            else:
                logger.error(f"Failed to create user: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None

    @classmethod
    def get_all_users(cls):
        """Get all users"""
        try:
            response = supabase.table('users').select('*').execute()
            
            users = []
            if response.data:
                for user_data in response.data:
                    try:
                        user = cls(**user_data)
                        users.append(user)
                    except Exception as e:
                        logger.error(f"Error processing user data: {user_data}, error: {str(e)}")
                        continue
            
            logger.info(f"Retrieved {len(users)} users")
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

    def update_energy(self):
        """Update energy based on time passed"""
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())
            time_passed = current_time - self.last_energy_update
            
            # Regenerate 1 energy per 30 seconds
            energy_to_add = time_passed // 30
            
            if energy_to_add > 0:
                self.energy = min(self.energy + energy_to_add, self.max_energy)
                self.last_energy_update = current_time
                logger.info(f"Energy updated for user {self.telegram_id}: +{energy_to_add}, current: {self.energy}")
                
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {str(e)}")

    def can_tap(self):
        """Check if user can tap"""
        return self.energy >= 1

    def tap(self):
        """Perform tap action"""
        try:
            if not self.can_tap():
                return False
            
            self.coins += self.tap_power
            self.energy -= 1
            self.total_taps += 1
            
            # Update energy before saving
            self.update_energy()
            
            # Save to database
            if self.save():
                logger.info(f"Tap successful for user {self.telegram_id}: coins={self.coins}, energy={self.energy}")
                return True
            else:
                logger.error(f"Failed to save tap for user {self.telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error in tap for user {self.telegram_id}: {str(e)}")
            return False

    def add_coins(self, amount):
        """Add coins to user"""
        try:
            amount = int(float(amount))
            self.coins += amount
            return self.save()
        except Exception as e:
            logger.error(f"Error adding coins to user {self.telegram_id}: {str(e)}")
            return False

    def subtract_coins(self, amount):
        """Subtract coins from user"""
        try:
            amount = int(float(amount))
            if self.coins >= amount:
                self.coins -= amount
                return self.save()
            else:
                logger.warning(f"Insufficient coins for user {self.telegram_id}: has {self.coins}, needs {amount}")
                return False
        except Exception as e:
            logger.error(f"Error subtracting coins from user {self.telegram_id}: {str(e)}")
            return False

    def upgrade_tap_power(self, cost):
        """Upgrade tap power"""
        try:
            cost = int(float(cost))
            if self.coins >= cost:
                self.coins -= cost
                self.tap_power += 1
                return self.save()
            else:
                return False
        except Exception as e:
            logger.error(f"Error upgrading tap power for user {self.telegram_id}: {str(e)}")
            return False

    def reset_user_data(self):
        """Reset user data to defaults"""
        try:
            self.coins = 2500
            self.energy = 100
            self.tap_power = 1
            self.total_taps = 0
            self.last_energy_update = int(datetime.now(timezone.utc).timestamp())
            return self.save()
        except Exception as e:
            logger.error(f"Error resetting user data for {self.telegram_id}: {str(e)}")
            return False

    def save(self):
        """Save user to database - only saves fields that exist in database"""
        try:
            logger.info(f"Saving user: {self.telegram_id}")
            
            # Only include fields that exist in the database schema
            user_data = {
                'telegram_id': int(self.telegram_id),
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'total_taps': int(self.total_taps),
                'referral_code': self.referral_code,
                'referred_by': self.referred_by,
                'referral_count': int(self.referral_count),
                'referral_earnings': int(self.referral_earnings),
                'upi_id': self.upi_id,
                'last_energy_update': int(self.last_energy_update),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Remove None values
            user_data = {k: v for k, v in user_data.items() if v is not None}
            
            logger.info(f"User data to save: {user_data}")
            
            response = supabase.table('users').update(user_data).eq('telegram_id', self.telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"User {self.telegram_id} saved successfully")
                return True
            else:
                logger.error(f"Failed to save user {self.telegram_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {str(e)}")
            return False

    def delete(self):
        """Delete user from database"""
        try:
            response = supabase.table('users').delete().eq('telegram_id', self.telegram_id).execute()
            
            if response.data is not None:
                logger.info(f"User {self.telegram_id} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete user {self.telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user {self.telegram_id}: {str(e)}")
            return False

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'coins': self.coins,
            'energy': self.energy,
            'max_energy': self.max_energy,
            'tap_power': self.tap_power,
            'energy_regen_rate': self.energy_regen_rate,
            'total_taps': self.total_taps,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'referral_count': self.referral_count,
            'referral_earnings': self.referral_earnings,
            'referrals': self.referral_count,  # Alias for compatibility
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_active': datetime.now(timezone.utc).isoformat(),  # Always current time
            'upi_id': self.upi_id,
            'last_energy_update': self.last_energy_update
        }


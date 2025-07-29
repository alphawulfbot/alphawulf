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
        """Get user by telegram ID with real-time energy update"""
        try:
            telegram_id = int(telegram_id)
            logger.info(f"Searching for user with telegram_id: {telegram_id}")
            
            response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"User found: {user_data}")
                user = cls(**user_data)
                
                # Update energy in real-time
                user.update_energy()
                user.save()
                
                return user
            else:
                logger.info(f"No user found with telegram_id: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {str(e)}")
            return None

    @classmethod
    def create_user(cls, telegram_id, username=None, first_name=None, last_name=None):
        """Create a new user with default values"""
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
        """Get all users with real-time energy updates"""
        try:
            response = supabase.table('users').select('*').execute()
            
            users = []
            if response.data:
                for user_data in response.data:
                    try:
                        user = cls(**user_data)
                        # Update energy for each user
                        user.update_energy()
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
        """Update energy based on time passed - real-time regeneration"""
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())
            time_passed = current_time - self.last_energy_update
            
            # Regenerate 1 energy per 30 seconds
            energy_to_add = time_passed // 30
            
            if energy_to_add > 0:
                old_energy = self.energy
                self.energy = min(self.energy + energy_to_add, self.max_energy)
                self.last_energy_update = current_time
                logger.info(f"Energy updated for user {self.telegram_id}: {old_energy} -> {self.energy} (+{energy_to_add})")
                
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {str(e)}")

    def can_tap(self):
        """Check if user can tap"""
        self.update_energy()  # Always update energy before checking
        return self.energy >= 1

    def tap(self):
        """Perform tap action with real-time updates"""
        try:
            # Update energy first
            self.update_energy()
            
            if not self.can_tap():
                logger.warning(f"User {self.telegram_id} cannot tap: energy={self.energy}")
                return False
            
            # Perform tap
            old_coins = self.coins
            old_energy = self.energy
            
            self.coins += self.tap_power
            self.energy -= 1
            self.total_taps += 1
            
            # Save to database immediately for real-time sync
            if self.save():
                logger.info(f"Tap successful for user {self.telegram_id}: coins {old_coins}->{self.coins}, energy {old_energy}->{self.energy}")
                return True
            else:
                # Rollback on save failure
                self.coins = old_coins
                self.energy = old_energy
                self.total_taps -= 1
                logger.error(f"Failed to save tap for user {self.telegram_id}, rolled back")
                return False
                
        except Exception as e:
            logger.error(f"Error in tap for user {self.telegram_id}: {str(e)}")
            return False

    def add_coins(self, amount):
        """Add coins to user with real-time sync"""
        try:
            amount = int(float(amount))
            old_coins = self.coins
            self.coins += amount
            
            if self.save():
                logger.info(f"Added {amount} coins to user {self.telegram_id}: {old_coins} -> {self.coins}")
                return True
            else:
                self.coins = old_coins  # Rollback
                return False
        except Exception as e:
            logger.error(f"Error adding coins to user {self.telegram_id}: {str(e)}")
            return False

    def subtract_coins(self, amount):
        """Subtract coins from user with real-time sync"""
        try:
            amount = int(float(amount))
            if self.coins >= amount:
                old_coins = self.coins
                self.coins -= amount
                
                if self.save():
                    logger.info(f"Subtracted {amount} coins from user {self.telegram_id}: {old_coins} -> {self.coins}")
                    return True
                else:
                    self.coins = old_coins  # Rollback
                    return False
            else:
                logger.warning(f"Insufficient coins for user {self.telegram_id}: has {self.coins}, needs {amount}")
                return False
        except Exception as e:
            logger.error(f"Error subtracting coins from user {self.telegram_id}: {str(e)}")
            return False

    def upgrade_tap_power(self, cost):
        """Upgrade tap power with real-time sync"""
        try:
            cost = int(float(cost))
            if self.coins >= cost:
                old_coins = self.coins
                old_tap_power = self.tap_power
                
                self.coins -= cost
                self.tap_power += 1
                
                if self.save():
                    logger.info(f"Upgraded tap power for user {self.telegram_id}: power {old_tap_power}->{self.tap_power}, coins {old_coins}->{self.coins}")
                    return True
                else:
                    # Rollback
                    self.coins = old_coins
                    self.tap_power = old_tap_power
                    return False
            else:
                logger.warning(f"Insufficient coins for upgrade: user {self.telegram_id} has {self.coins}, needs {cost}")
                return False
        except Exception as e:
            logger.error(f"Error upgrading tap power for user {self.telegram_id}: {str(e)}")
            return False

    def reset_user_data(self):
        """Reset user data to defaults with real-time sync"""
        try:
            self.coins = 2500
            self.energy = 100
            self.tap_power = 1
            self.total_taps = 0
            self.last_energy_update = int(datetime.now(timezone.utc).timestamp())
            
            if self.save():
                logger.info(f"Reset user data for {self.telegram_id}")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error resetting user data for {self.telegram_id}: {str(e)}")
            return False

    def save(self):
        """Save user to database - bulletproof with real-time sync"""
        try:
            logger.info(f"Saving user: {self.telegram_id}")
            
            # Prepare data for database (only existing columns)
            user_data = {
                'telegram_id': int(self.telegram_id),
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'total_taps': int(self.total_taps),
                'referral_count': int(self.referral_count),
                'referral_earnings': int(self.referral_earnings),
                'last_energy_update': int(self.last_energy_update),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional fields only if they have values
            if self.username:
                user_data['username'] = self.username
            if self.first_name:
                user_data['first_name'] = self.first_name
            if self.last_name:
                user_data['last_name'] = self.last_name
            if self.referral_code:
                user_data['referral_code'] = self.referral_code
            if self.referred_by:
                user_data['referred_by'] = self.referred_by
            if self.upi_id:
                user_data['upi_id'] = self.upi_id
            
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
        """Convert user to dictionary for API responses"""
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

    def get_real_time_data(self):
        """Get real-time user data with energy updates"""
        self.update_energy()
        return self.to_dict()


import logging
from datetime import datetime
from typing import Optional, Dict, Any
from src.config.database import supabase

logger = logging.getLogger(__name__)

class User:
    def __init__(self, data: Dict[str, Any]):
        """Initialize User with data from database or API"""
        self.id = data.get('id')
        self.telegram_id = data.get('telegram_id')
        self.username = data.get('username', '')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        
        # Convert float values to integers for database compatibility
        self.coins = int(float(data.get('coins', 2500)))
        self.energy = int(float(data.get('energy', 100)))
        self.max_energy = int(float(data.get('max_energy', 100)))
        self.tap_power = int(float(data.get('tap_power', 1)))
        self.referral_count = int(float(data.get('referral_count', 0)))
        self.referral_earnings = int(float(data.get('referral_earnings', 0)))
        
        self.last_energy_update = data.get('last_energy_update')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @classmethod
    def find_by_telegram_id(cls, telegram_id: int) -> Optional['User']:
        """Find user by telegram ID"""
        try:
            response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            if response.data:
                return cls(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error finding user by telegram_id {telegram_id}: {e}")
            return None

    @classmethod
    def create(cls, telegram_id: int, username: str = '', first_name: str = '', last_name: str = '') -> Optional['User']:
        """Create new user"""
        try:
            user_data = {
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'coins': 2500,  # Integer default
                'energy': 100,  # Integer default
                'max_energy': 100,  # Integer default
                'tap_power': 1,  # Integer default
                'referral_count': 0,  # Integer default
                'referral_earnings': 0,  # Integer default
                'last_energy_update': datetime.utcnow().isoformat()
            }
            
            response = supabase.table('users').insert(user_data).execute()
            if response.data:
                logger.info(f"Created new user: {telegram_id}")
                return cls(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None

    def save(self) -> bool:
        """Save user to database with proper type conversion"""
        try:
            # Ensure all numeric values are integers
            update_data = {
                'username': self.username,
                'first_name': self.first_name,
                'coins': int(float(self.coins)),  # Convert to int
                'energy': int(float(self.energy)),  # Convert to int
                'max_energy': int(float(self.max_energy)),  # Convert to int
                'tap_power': int(float(self.tap_power)),  # Convert to int
                'referral_count': int(float(self.referral_count)),  # Convert to int
                'referral_earnings': int(float(self.referral_earnings)),  # Convert to int
                'last_energy_update': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Only include last_name if it exists and is not empty
            if hasattr(self, 'last_name') and self.last_name:
                update_data['last_name'] = self.last_name
            
            logger.info(f"Saving user {self.telegram_id} with data: {update_data}")
            
            response = supabase.table('users').update(update_data).eq('id', self.id).execute()
            
            if response.data:
                logger.info(f"Successfully saved user {self.telegram_id}")
                return True
            else:
                logger.error(f"No data returned when saving user {self.telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error in save: {e}")
            # Retry once with minimal data
            try:
                minimal_data = {
                    'coins': int(float(self.coins)),
                    'energy': int(float(self.energy)),
                    'updated_at': datetime.utcnow().isoformat()
                }
                logger.info(f"Retrying save with minimal data: {minimal_data}")
                response = supabase.table('users').update(minimal_data).eq('id', self.id).execute()
                if response.data:
                    logger.info(f"Successfully saved user {self.telegram_id} on retry")
                    return True
                else:
                    logger.error(f"Error in save (retry): No data returned")
                    return False
            except Exception as retry_error:
                logger.error(f"Error in save (retry): {retry_error}")
                logger.warning(f"Failed to save user {self.telegram_id} to database")
                return False

    def tap(self) -> Dict[str, Any]:
        """Handle tap action"""
        if self.energy >= self.tap_power:
            self.coins += self.tap_power
            self.energy -= self.tap_power
            
            # Save to database
            if self.save():
                return {
                    'success': True,
                    'coins': self.coins,
                    'energy': self.energy,
                    'message': 'Tap successful'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to save tap data'
                }
        else:
            return {
                'success': False,
                'message': 'Not enough energy'
            }

    def can_tap(self) -> bool:
        """Check if user can tap"""
        return self.energy >= self.tap_power

    def update_energy(self) -> None:
        """Update energy based on time passed"""
        try:
            if self.last_energy_update:
                last_update = datetime.fromisoformat(self.last_energy_update.replace('Z', '+00:00'))
                now = datetime.utcnow()
                time_diff = (now - last_update).total_seconds()
                
                # Regenerate 1 energy per 30 seconds
                energy_to_add = int(time_diff // 30)
                
                if energy_to_add > 0:
                    self.energy = min(self.max_energy, self.energy + energy_to_add)
                    self.last_energy_update = now.isoformat()
                    logger.info(f"Updated energy for user {self.telegram_id}: +{energy_to_add} energy")
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': getattr(self, 'last_name', ''),
            'coins': int(self.coins),
            'energy': int(self.energy),
            'max_energy': int(self.max_energy),
            'tap_power': int(self.tap_power),
            'referral_count': int(self.referral_count),
            'referral_earnings': int(self.referral_earnings),
            'last_energy_update': self.last_energy_update,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __str__(self):
        return f"User(telegram_id={self.telegram_id}, username={self.username}, coins={self.coins})"


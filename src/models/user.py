import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.config.database import supabase

logger = logging.getLogger(__name__)

class User:
    def __init__(self, telegram_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, coins: int = 2500, energy: int = 100, 
                 tap_power: int = 1, referrals: int = 0, referred_by: int = None,
                 last_active: datetime = None, created_at: datetime = None):
        self.telegram_id = int(telegram_id)
        self.username = username or ""
        self.first_name = first_name or ""
        self.last_name = last_name or ""
        self.coins = int(float(coins)) if coins is not None else 2500
        self.energy = int(float(energy)) if energy is not None else 100
        self.tap_power = int(float(tap_power)) if tap_power is not None else 1
        self.referrals = int(float(referrals)) if referrals is not None else 0
        self.referred_by = int(float(referred_by)) if referred_by is not None else None
        self.last_active = last_active or datetime.now(timezone.utc)
        self.created_at = created_at or datetime.now(timezone.utc)
        
        logger.info(f"User initialized: {self.telegram_id}, coins: {self.coins}, energy: {self.energy}")

    @classmethod
    def get_by_telegram_id(cls, telegram_id: int) -> Optional['User']:
        """Get user by telegram ID"""
        try:
            telegram_id = int(telegram_id)
            logger.info(f"Searching for user with telegram_id: {telegram_id}")
            
            response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"User found: {user_data}")
                
                # Convert datetime strings to datetime objects
                last_active = None
                created_at = None
                
                if user_data.get('last_active'):
                    try:
                        last_active = datetime.fromisoformat(user_data['last_active'].replace('Z', '+00:00'))
                    except:
                        last_active = datetime.now(timezone.utc)
                
                if user_data.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                    except:
                        created_at = datetime.now(timezone.utc)
                
                return cls(
                    telegram_id=user_data['telegram_id'],
                    username=user_data.get('username', ''),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    coins=user_data.get('coins', 2500),
                    energy=user_data.get('energy', 100),
                    tap_power=user_data.get('tap_power', 1),
                    referrals=user_data.get('referrals', 0),
                    referred_by=user_data.get('referred_by'),
                    last_active=last_active,
                    created_at=created_at
                )
            else:
                logger.info(f"No user found with telegram_id: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {str(e)}")
            return None

    @classmethod
    def create_user(cls, telegram_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None, referred_by: int = None) -> Optional['User']:
        """Create a new user"""
        try:
            telegram_id = int(telegram_id)
            logger.info(f"Creating new user: {telegram_id}")
            
            user_data = {
                'telegram_id': telegram_id,
                'username': username or "",
                'first_name': first_name or "",
                'last_name': last_name or "",
                'coins': 2500,
                'energy': 100,
                'tap_power': 1,
                'referrals': 0,
                'referred_by': int(referred_by) if referred_by else None,
                'last_active': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = supabase.table('users').insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"User created successfully: {response.data[0]}")
                return cls.get_by_telegram_id(telegram_id)
            else:
                logger.error(f"Failed to create user: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {str(e)}")
            return None

    def save(self) -> bool:
        """Save user data to database"""
        try:
            logger.info(f"Saving user: {self.telegram_id}")
            
            # Ensure all numeric values are integers
            user_data = {
                'telegram_id': int(self.telegram_id),
                'username': str(self.username or ""),
                'first_name': str(self.first_name or ""),
                'last_name': str(self.last_name or ""),
                'coins': int(float(self.coins)) if self.coins is not None else 2500,
                'energy': int(float(self.energy)) if self.energy is not None else 100,
                'tap_power': int(float(self.tap_power)) if self.tap_power is not None else 1,
                'referrals': int(float(self.referrals)) if self.referrals is not None else 0,
                'referred_by': int(float(self.referred_by)) if self.referred_by is not None else None,
                'last_active': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"User data to save: {user_data}")
            
            response = supabase.table('users').update(user_data).eq('telegram_id', self.telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"User saved successfully: {response.data[0]}")
                return True
            else:
                logger.error(f"Failed to save user: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {str(e)}")
            return False

    def update_energy(self) -> bool:
        """Update energy based on time passed"""
        try:
            # Simple energy regeneration - 1 energy per 30 seconds
            current_time = datetime.now(timezone.utc)
            if hasattr(self, 'last_active') and self.last_active:
                time_diff = (current_time - self.last_active).total_seconds()
                energy_to_add = int(time_diff // 30)  # 1 energy per 30 seconds
                
                if energy_to_add > 0:
                    self.energy = min(100, self.energy + energy_to_add)  # Max 100 energy
                    logger.info(f"Energy updated for user {self.telegram_id}: +{energy_to_add}, total: {self.energy}")
            
            self.last_active = current_time
            return True
            
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {str(e)}")
            return False

    def can_tap(self) -> bool:
        """Check if user can tap (has energy)"""
        return self.energy > 0

    def tap(self) -> bool:
        """Perform a tap action"""
        try:
            if not self.can_tap():
                logger.warning(f"User {self.telegram_id} cannot tap - no energy")
                return False
            
            self.coins += self.tap_power
            self.energy -= 1
            
            logger.info(f"User {self.telegram_id} tapped: +{self.tap_power} coins, -{1} energy")
            return self.save()
            
        except Exception as e:
            logger.error(f"Error processing tap for user {self.telegram_id}: {str(e)}")
            return False

    def add_coins(self, amount: int) -> bool:
        """Add coins to user"""
        try:
            amount = int(float(amount))
            self.coins += amount
            logger.info(f"Added {amount} coins to user {self.telegram_id}, total: {self.coins}")
            return self.save()
            
        except Exception as e:
            logger.error(f"Error adding coins to user {self.telegram_id}: {str(e)}")
            return False

    def subtract_coins(self, amount: int) -> bool:
        """Subtract coins from user"""
        try:
            amount = int(float(amount))
            if self.coins >= amount:
                self.coins -= amount
                logger.info(f"Subtracted {amount} coins from user {self.telegram_id}, total: {self.coins}")
                return self.save()
            else:
                logger.warning(f"User {self.telegram_id} doesn't have enough coins: {self.coins} < {amount}")
                return False
                
        except Exception as e:
            logger.error(f"Error subtracting coins from user {self.telegram_id}: {str(e)}")
            return False

    def upgrade_tap_power(self, cost: int) -> bool:
        """Upgrade tap power"""
        try:
            cost = int(float(cost))
            if self.coins >= cost:
                self.coins -= cost
                self.tap_power += 1
                logger.info(f"User {self.telegram_id} upgraded tap power to {self.tap_power}")
                return self.save()
            else:
                logger.warning(f"User {self.telegram_id} cannot afford upgrade: {self.coins} < {cost}")
                return False
                
        except Exception as e:
            logger.error(f"Error upgrading tap power for user {self.telegram_id}: {str(e)}")
            return False

    def add_referral(self) -> bool:
        """Add a referral"""
        try:
            self.referrals += 1
            logger.info(f"User {self.telegram_id} got a referral, total: {self.referrals}")
            return self.save()
            
        except Exception as e:
            logger.error(f"Error adding referral to user {self.telegram_id}: {str(e)}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'coins': self.coins,
            'energy': self.energy,
            'tap_power': self.tap_power,
            'referrals': self.referrals,
            'referred_by': self.referred_by,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_all_users(cls):
        """Get all users"""
        try:
            response = supabase.table('users').select('*').execute()
            users = []
            
            if response.data:
                for user_data in response.data:
                    try:
                        # Convert datetime strings
                        last_active = None
                        created_at = None
                        
                        if user_data.get('last_active'):
                            try:
                                last_active = datetime.fromisoformat(user_data['last_active'].replace('Z', '+00:00'))
                            except:
                                last_active = datetime.now(timezone.utc)
                        
                        if user_data.get('created_at'):
                            try:
                                created_at = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                            except:
                                created_at = datetime.now(timezone.utc)
                        
                        user = cls(
                            telegram_id=user_data['telegram_id'],
                            username=user_data.get('username', ''),
                            first_name=user_data.get('first_name', ''),
                            last_name=user_data.get('last_name', ''),
                            coins=user_data.get('coins', 2500),
                            energy=user_data.get('energy', 100),
                            tap_power=user_data.get('tap_power', 1),
                            referrals=user_data.get('referrals', 0),
                            referred_by=user_data.get('referred_by'),
                            last_active=last_active,
                            created_at=created_at
                        )
                        users.append(user)
                    except Exception as e:
                        logger.error(f"Error processing user data: {user_data}, error: {str(e)}")
                        continue
            
            logger.info(f"Retrieved {len(users)} users")
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

    def delete(self) -> bool:
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

    def reset_user_data(self) -> bool:
        """Reset user data to defaults"""
        try:
            self.coins = 2500
            self.energy = 100
            self.tap_power = 1
            self.referrals = 0
            
            logger.info(f"User {self.telegram_id} data reset to defaults")
            return self.save()
            
        except Exception as e:
            logger.error(f"Error resetting user {self.telegram_id}: {str(e)}")
            return False


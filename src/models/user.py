from src.config.database import supabase
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User:
    def __init__(self, telegram_id, username=None, first_name=None, coins=2500, energy=100, 
                 max_energy=100, tap_power=1, energy_regen_rate=1, last_energy_update=None,
                 referred_by=None, referral_count=0, referral_earnings=0, upi_id=None):
        self.telegram_id = str(telegram_id)
        self.username = username
        self.first_name = first_name
        self.coins = int(coins) if coins is not None else 2500  # Default 2500 coins for new users
        self.energy = float(energy) if energy is not None else 100.0
        self.max_energy = int(max_energy) if max_energy is not None else 100
        self.tap_power = int(tap_power) if tap_power is not None else 1
        self.energy_regen_rate = int(energy_regen_rate) if energy_regen_rate is not None else 1
        self.last_energy_update = int(last_energy_update) if last_energy_update else int(time.time())
        self.referred_by = referred_by
        self.referral_count = int(referral_count) if referral_count is not None else 0
        self.referral_earnings = int(referral_earnings) if referral_earnings is not None else 0
        self.upi_id = upi_id

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by telegram ID"""
        try:
            telegram_id = str(telegram_id)
            logger.debug(f"Fetching user with telegram_id: {telegram_id}")
            
            response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.debug(f"User found: {user_data}")
                
                return cls(
                    telegram_id=user_data.get("telegram_id"),
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    coins=user_data.get("coins", 2500),  # Default to 2500 if not set
                    energy=user_data.get("energy", 100.0),
                    max_energy=user_data.get("max_energy", 100),
                    tap_power=user_data.get("tap_power", 1),
                    energy_regen_rate=user_data.get("energy_regen_rate", 1),
                    last_energy_update=user_data.get("last_energy_update"),
                    referred_by=user_data.get("referred_by"),
                    referral_count=user_data.get("referral_count", 0),
                    referral_earnings=user_data.get("referral_earnings", 0),
                    upi_id=user_data.get("upi_id")
                )
            else:
                logger.debug(f"No user found with telegram_id: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {str(e)}")
            return None

    def save(self):
        """Save user to database"""
        try:
            # Ensure data types are correct
            user_data = {
                "telegram_id": str(self.telegram_id),
                "username": self.username,
                "first_name": self.first_name,
                "coins": int(self.coins),
                "energy": float(self.energy),
                "max_energy": int(self.max_energy),
                "tap_power": int(self.tap_power),
                "energy_regen_rate": int(self.energy_regen_rate),
                "last_energy_update": int(self.last_energy_update),
                "referred_by": self.referred_by,
                "referral_count": int(self.referral_count),
                "referral_earnings": int(self.referral_earnings),
                "upi_id": self.upi_id
            }
            
            logger.debug(f"Saving user data: {user_data}")
            
            # Try to update first
            response = supabase.table("users").update(user_data).eq("telegram_id", self.telegram_id).execute()
            
            # If no rows were updated, insert new user
            if not response.data or len(response.data) == 0:
                logger.info(f"Creating new user: {self.telegram_id}")
                response = supabase.table("users").insert(user_data).execute()
                
                if not response.data or len(response.data) == 0:
                    raise Exception("Failed to create new user")
            else:
                logger.debug(f"Updated existing user: {self.telegram_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {str(e)}")
            raise e

    def update_energy(self):
        """Update energy based on regeneration rate"""
        try:
            current_time = int(time.time())
            if self.last_energy_update:
                time_diff = current_time - self.last_energy_update
                # Energy regenerates 1 per 30 seconds
                energy_regen = (time_diff / 30) * self.energy_regen_rate
                
                self.energy = min(self.max_energy, self.energy + energy_regen)
                self.last_energy_update = current_time
                
                logger.debug(f"Energy updated for user {self.telegram_id}: {self.energy}/{self.max_energy}")
            
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {str(e)}")

    def can_tap(self):
        """Check if user can tap (has enough energy)"""
        return self.energy >= 1

    def tap(self):
        """Perform a tap action"""
        if not self.can_tap():
            return False
        
        try:
            self.energy -= 1
            self.coins += self.tap_power
            self.last_energy_update = int(time.time())
            
            logger.debug(f"User {self.telegram_id} tapped: coins={self.coins}, energy={self.energy}")
            return True
            
        except Exception as e:
            logger.error(f"Error during tap for user {self.telegram_id}: {str(e)}")
            return False

    def add_referral(self):
        """Add a referral to this user"""
        try:
            self.referral_count += 1
            self.referral_earnings += 100  # Bonus for referring a user
            self.coins += 100
            
            logger.info(f"Referral added for user {self.telegram_id}: count={self.referral_count}, earnings={self.referral_earnings}")
            
        except Exception as e:
            logger.error(f"Error adding referral for user {self.telegram_id}: {str(e)}")

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "coins": self.coins,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "tap_power": self.tap_power,
            "energy_regen_rate": self.energy_regen_rate,
            "last_energy_update": self.last_energy_update,
            "referred_by": self.referred_by,
            "referral_count": self.referral_count,
            "referral_earnings": self.referral_earnings,
            "upi_id": self.upi_id
        }


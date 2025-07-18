from src.config.database import supabase
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User:
    def __init__(self, telegram_id, username=None, first_name=None, coins=0, energy=100, max_energy=100, 
                 tap_power=1, energy_regen_rate=1, last_energy_update=None, referred_by=None, 
                 referral_count=0, referral_earnings=0, upi_id=None, id=None):
        self.id = id
        self.telegram_id = str(telegram_id) # Ensure telegram_id is string
        self.username = username
        self.first_name = first_name
        self.coins = int(coins) # Ensure coins are integer
        self.energy = float(energy) # Ensure energy is float
        self.max_energy = int(max_energy) # Ensure max_energy is integer
        self.tap_power = int(tap_power) # Ensure tap_power is integer
        self.energy_regen_rate = float(energy_regen_rate) # Ensure energy_regen_rate is float
        self.last_energy_update = last_energy_update or int(time.time())
        self.referred_by = str(referred_by) if referred_by else None # Ensure referred_by is string
        self.referral_count = int(referral_count) # Ensure referral_count is integer
        self.referral_earnings = int(referral_earnings) # Ensure referral_earnings is integer
        self.upi_id = upi_id

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """
        Get user by Telegram ID
        """
        try:
            response = supabase.table("users").select("*").eq("telegram_id", str(telegram_id)).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                return cls(
                    id=user_data.get("id"),
                    telegram_id=user_data.get("telegram_id"),
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    coins=user_data.get("coins", 0),
                    energy=user_data.get("energy", 100),
                    max_energy=user_data.get("max_energy", 100),
                    tap_power=user_data.get("tap_power", 1),
                    energy_regen_rate=user_data.get("energy_regen_rate", 1),
                    last_energy_update=user_data.get("last_energy_update"),
                    referred_by=user_data.get("referred_by"),
                    referral_count=user_data.get("referral_count", 0),
                    referral_earnings=user_data.get("referral_earnings", 0),
                    upi_id=user_data.get("upi_id")
                )
            return None
        except Exception as e:
            logger.error(f"Error in get_by_telegram_id: {str(e)}")
            # Return a default user for development/testing
            logger.warning(f"Returning default user for telegram_id: {telegram_id}")
            return cls(
                telegram_id=telegram_id,
                username=f"user_{telegram_id}",
                first_name="Test User",
                coins=1000,
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=int(time.time())
            )

    def save(self):
        """
        Save user to database
        """
        try:
            user_data = self.to_dict()
            
            # Remove id from dict if it's None
            if "id" in user_data and user_data["id"] is None:
                del user_data["id"]
            
            # Ensure last_energy_update is an integer
            if "last_energy_update" in user_data and user_data["last_energy_update"] is not None:
                user_data["last_energy_update"] = int(user_data["last_energy_update"])
            
            # Check if user already exists
            existing_user = None
            if self.id:
                existing_user = self.id
            else:
                existing_response = supabase.table("users").select("id").eq("telegram_id", self.telegram_id).execute()
                if existing_response.data and len(existing_response.data) > 0:
                    existing_user = existing_response.data[0].get("id")
            
            if existing_user:
                # Update existing user
                response = supabase.table("users").update(user_data).eq("id", existing_user).execute()
            else:
                # Create new user
                response = supabase.table("users").insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                self.id = response.data[0].get("id")
            
            return self
        except Exception as e:
            logger.error(f"Error in save: {str(e)}")
            
            # Try again without problematic fields if there's an error
            try:
                user_data = self.to_dict()
                
                # Remove id from dict if it's None
                if "id" in user_data and user_data["id"] is None:
                    del user_data["id"]
                
                # Remove problematic fields
                if "last_energy_update" in user_data:
                    user_data["last_energy_update"] = int(time.time())
                
                if "upi_id" in user_data and "upi_id" in str(e):
                    del user_data["upi_id"]
                
                # Check if user already exists
                existing_user = None
                if self.id:
                    existing_user = self.id
                else:
                    existing_response = supabase.table("users").select("id").eq("telegram_id", self.telegram_id).execute()
                    if existing_response.data and len(existing_response.data) > 0:
                        existing_user = existing_response.data[0].get("id")
                
                if existing_user:
                    # Update existing user
                    response = supabase.table("users").update(user_data).eq("id", existing_user).execute()
                else:
                    # Create new user
                    response = supabase.table("users").insert(user_data).execute()
                
                if response.data and len(response.data) > 0:
                    self.id = response.data[0].get("id")
                
                return self
            except Exception as e2:
                logger.error(f"Error in save (retry): {str(e2)}")
            
            logger.warning(f"Failed to save user {self.telegram_id} to database")
            return self

    def to_dict(self):
        """
        Convert user to dictionary
        """
        return {
            "id": self.id,
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




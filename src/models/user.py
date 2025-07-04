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
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.coins = coins
        self.energy = energy
        self.max_energy = max_energy
        self.tap_power = tap_power
        self.energy_regen_rate = energy_regen_rate
        self.last_energy_update = last_energy_update or int(time.time())
        self.referred_by = referred_by
        self.referral_count = referral_count
        self.referral_earnings = referral_earnings
        self.upi_id = upi_id

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """
        Get user by Telegram ID
        """
        try:
            response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            
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
            
            # Convert Unix timestamp to ISO format for PostgreSQL
            if "last_energy_update" in user_data and user_data["last_energy_update"] is not None:
                # Convert to ISO format string that PostgreSQL can handle
                # This assumes last_energy_update is stored as a bigint in the database
                # If it's stored as a timestamp, use this instead:
                # from datetime import datetime
                # user_data["last_energy_update"] = datetime.fromtimestamp(user_data["last_energy_update"]).isoformat()
                
                # For now, we'll keep it as an integer since that's what the error suggests
                # Make sure it's within the valid range for PostgreSQL timestamps
                # PostgreSQL can handle timestamps from 4713 BC to 294276 AD
                # For safety, we'll cap it at a reasonable value if it's too large
                if isinstance(user_data["last_energy_update"], int) and user_data["last_energy_update"] > 2147483647:
                    logger.warning(f"Timestamp too large: {user_data['last_energy_update']}, capping at current time")
                    user_data["last_energy_update"] = int(time.time())
            
            if self.id:
                # Update existing user
                response = supabase.table("users").update(user_data).eq("id", self.id).execute()
            else:
                # Check if user already exists by telegram_id
                existing_user = User.get_by_telegram_id(self.telegram_id)
                if existing_user and existing_user.id:
                    # Update existing user
                    response = supabase.table("users").update(user_data).eq("telegram_id", self.telegram_id).execute()
                else:
                    # Create new user
                    response = supabase.table("users").insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                self.id = response.data[0].get("id")
            
            return self
        except Exception as e:
            logger.error(f"Error in save: {str(e)}")
            
            # Try again without upi_id if that's the issue
            if "Could not find the 'upi_id' column" in str(e):
                try:
                    user_data = self.to_dict()
                    
                    # Remove id from dict if it's None
                    if "id" in user_data and user_data["id"] is None:
                        del user_data["id"]
                    
                    # Remove upi_id
                    if "upi_id" in user_data:
                        del user_data["upi_id"]
                    
                    # Handle timestamp again
                    if "last_energy_update" in user_data and user_data["last_energy_update"] is not None:
                        if isinstance(user_data["last_energy_update"], int) and user_data["last_energy_update"] > 2147483647:
                            logger.warning(f"Timestamp too large: {user_data['last_energy_update']}, capping at current time")
                            user_data["last_energy_update"] = int(time.time())
                    
                    if self.id:
                        # Update existing user
                        response = supabase.table("users").update(user_data).eq("id", self.id).execute()
                    else:
                        # Check if user already exists by telegram_id
                        existing_user = User.get_by_telegram_id(self.telegram_id)
                        if existing_user and existing_user.id:
                            # Update existing user
                            response = supabase.table("users").update(user_data).eq("telegram_id", self.telegram_id).execute()
                        else:
                            # Create new user
                            response = supabase.table("users").insert(user_data).execute()
                    
                    if response.data and len(response.data) > 0:
                        self.id = response.data[0].get("id")
                    
                    return self
                except Exception as e2:
                    logger.error(f"Error in save (retry without upi_id): {str(e2)}")
            
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


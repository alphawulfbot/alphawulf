"""
Comprehensive User Model for Alpha Wulf Flask Application

This model handles all user-related data, including authentication, game mechanics,
and database interactions with Supabase.
"""

import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to get Supabase client, ensuring environment variables are loaded
def get_supabase_client():
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") # Changed to SUPABASE_SERVICE_KEY

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase URL or Key not found in environment variables.")
        raise ValueError("Supabase URL or Key not found")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

class User:
    """Represents a user in the Alpha Wulf application."""

    def __init__(self, data):
        self.telegram_id = data["telegram_id"]
        self.username = data.get("username", "")
        self.first_name = data.get("first_name", "")
        self.last_name = data.get("last_name", "")
        self.coins = data.get("coins", 0)
        self.energy = data.get("energy", 100)  # Default energy
        self.last_energy_update = datetime.fromisoformat(data["last_energy_update"]) if isinstance(data.get("last_energy_update"), str) else data.get("last_energy_update", datetime.now())
        self.max_energy = data.get("max_energy", 100)
        self.energy_recharge_rate = data.get("energy_recharge_rate", 1) # Energy per minute
        self.power = data.get("power", 1)
        self.referrals = data.get("referrals", 0)
        self.last_tap_time = datetime.fromisoformat(data["last_tap_time"]) if isinstance(data.get("last_tap_time"), str) else data.get("last_tap_time", datetime.now())
        self.is_admin = data.get("is_admin", False)

    def to_dict(self):
        """Converts user object to a dictionary for JSON serialization."""
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "coins": self.coins,
            "energy": self.energy,
            "last_energy_update": self.last_energy_update.isoformat(),
            "max_energy": self.max_energy,
            "energy_recharge_rate": self.energy_recharge_rate,
            "power": self.power,
            "referrals": self.referrals,
            "last_tap_time": self.last_tap_time.isoformat(),
            "is_admin": self.is_admin
        }

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Retrieves a user by their Telegram ID."""
        try:
            supabase_client = get_supabase_client()
            response = supabase_client.from_("users").select("*").eq("telegram_id", telegram_id).single().execute()
            if response.data:
                return cls(response.data)
            return None
        except Exception as e:
            logger.error(f"Error getting user by Telegram ID {telegram_id}: {e}")
            return None

    @classmethod
    def create_user(cls, telegram_id, username, first_name, last_name):
        """Creates a new user."""
        try:
            supabase_client = get_supabase_client()
            new_user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "coins": 0,
                "energy": 100,
                "last_energy_update": datetime.now().isoformat(),
                "max_energy": 100,
                "energy_recharge_rate": 1,
                "power": 1,
                "referrals": 0,
                "last_tap_time": datetime.now().isoformat(),
                "is_admin": False
            }
            response = supabase_client.from_("users").insert(new_user_data).execute()
            if response.data:
                return cls(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None

    def save(self):
        """Saves the current state of the user to the database."""
        try:
            supabase_client = get_supabase_client()
            update_data = self.to_dict()
            # Remove telegram_id from update_data as it's the primary key and shouldn't be updated
            del update_data["telegram_id"]
            response = supabase_client.from_("users").update(update_data).eq("telegram_id", self.telegram_id).execute()
            if response.data:
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {e}")
            return False

    def tap(self, taps=1):
        """Handles user tap, increasing coins and decreasing energy."""
        self.update_energy() # Ensure energy is up-to-date
        
        if self.energy >= taps:
            self.coins += (taps * self.power)
            self.energy -= taps
            self.last_tap_time = datetime.now()
            if self.save():
                return True, "Tap successful"
            return False, "Failed to save tap data"
        return False, "Not enough energy"

    def update_energy(self):
        """Recalculates user energy based on time elapsed."""
        now = datetime.now()
        time_diff = now - self.last_energy_update
        minutes_passed = int(time_diff.total_seconds() / 60)
        
        if minutes_passed > 0:
            energy_gained = minutes_passed * self.energy_recharge_rate
            self.energy = min(self.max_energy, self.energy + energy_gained)
            self.last_energy_update = now
            self.save() # Save updated energy to DB

    # Admin functionalities (example)
    def get_all_users(self):
        """Retrieves all users (admin only)."""
        if not self.is_admin:
            return None, "Unauthorized"
        try:
            supabase_client = get_supabase_client()
            response = supabase_client.from_("users").select("*").execute()
            return response.data, None
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return None, str(e)

    def update_user_coins(self, target_telegram_id, amount):
        """Updates a target user's coins (admin only)."""
        if not self.is_admin:
            return False, "Unauthorized"
        try:
            supabase_client = get_supabase_client()
            target_user = User.get_by_telegram_id(target_telegram_id)
            if not target_user:
                return False, "Target user not found"
            target_user.coins += amount
            if target_user.save():
                return True, "Coins updated successfully"
            return False, "Failed to update target user coins"
        except Exception as e:
            logger.error(f"Error updating coins for {target_telegram_id}: {e}")
            return False, str(e)

    # Add more functionalities as needed, e.g., upgrades, referrals, etc.



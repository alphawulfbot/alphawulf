import time
import random
import string
from datetime import datetime

from src.config.database import supabase

class User:
    def __init__(self, telegram_id, username=None, first_name=None, last_name=None, **kwargs):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.coins = kwargs.get("coins", 2500)
        self.energy = kwargs.get("energy", 100)
        self.max_energy = kwargs.get("max_energy", 100)
        self.tap_power = kwargs.get("tap_power", 1)
        self.energy_regen_rate = kwargs.get("energy_regen_rate", 1)
        self.total_taps = kwargs.get("total_taps", 0)
        self.referral_code = kwargs.get("referral_code", self.generate_referral_code())
        self.referred_by = kwargs.get("referred_by", None)
        self.referral_count = kwargs.get("referral_count", 0)
        self.referral_earnings = kwargs.get("referral_earnings", 0)
        self.last_energy_update = kwargs.get("last_energy_update", datetime.utcnow().isoformat())
        self.last_activity = kwargs.get("last_activity", datetime.utcnow().isoformat())
        self.upi_id = kwargs.get("upi_id", None)
        self.total_earned = kwargs.get("total_earned", 2500)
        self.total_withdrawn = kwargs.get("total_withdrawn", 0.0)
        self.referral_level = kwargs.get("referral_level", 1)
        self.id = kwargs.get("id", None) # Supabase row ID

    def generate_referral_code(self):
        """Generate a unique referral code"""
        return f"REF{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by Telegram ID from Supabase"""
        try:
            response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            if response.data:
                user_data = response.data[0]
                return cls(**user_data)
            return None
        except Exception as e:
            print(f"Error getting user by Telegram ID: {e}")
            return None

    def save(self):
        """Save user to Supabase"""
        try:
            user_data = self.to_dict()
            # Remove 'id' if it's None for insert, Supabase will generate it
            if user_data.get("id") is None:
                user_data.pop("id")

            existing_user = self.get_by_telegram_id(self.telegram_id)

            if existing_user:
                # Update existing user
                response = supabase.table("users").update(user_data).eq("telegram_id", self.telegram_id).execute()
            else:
                # Create new user
                response = supabase.table("users").insert(user_data).execute()
                if response.data:
                    self.id = response.data[0]["id"]
            return True
        except Exception as e:
            print(f"Error saving user: {e}")
            return False

    def to_dict(self):
        """Convert User object to dictionary for Supabase"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "coins": self.coins,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "tap_power": self.tap_power,
            "energy_regen_rate": self.energy_regen_rate,
            "total_taps": self.total_taps,
            "referral_code": self.referral_code,
            "referred_by": self.referred_by,
            "referral_count": self.referral_count,
            "referral_earnings": self.referral_earnings,
            "last_energy_update": self.last_energy_update,
            "last_activity": self.last_activity,
            "upi_id": self.upi_id,
            "total_earned": self.total_earned,
            "total_withdrawn": self.total_withdrawn,
            "referral_level": self.referral_level
        }

    def add_coins(self, amount):
        self.coins += amount
        self.total_earned += amount
        return self.save()

    def spend_coins(self, amount):
        if self.coins >= amount:
            self.coins -= amount
            return self.save()
        return False

    def tap(self, taps=1):
        if self.energy >= taps:
            self.energy -= taps
            coins_earned = taps * self.tap_power
            self.coins += coins_earned
            self.total_earned += coins_earned
            self.total_taps += taps
            self.last_activity = datetime.utcnow().isoformat()
            self.update_energy()
            return self.save()
        return False

    def update_energy(self):
        now = datetime.utcnow()
        # Convert ISO format string to datetime object if necessary
        if isinstance(self.last_energy_update, str):
            try:
                self.last_energy_update = datetime.fromisoformat(self.last_energy_update.replace("Z", "+00:00"))
            except:
                self.last_energy_update = now

        time_diff = (now - self.last_energy_update).total_seconds() / 60
        energy_to_add = int(time_diff * self.energy_regen_rate)

        if energy_to_add > 0:
            self.energy = min(self.energy + energy_to_add, self.max_energy)
            self.last_energy_update = now.isoformat()
            self.last_activity = now.isoformat()

    @classmethod
    def get_all_users(cls):
        try:
            response = supabase.table("users").select("*").order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []

    @classmethod
    def get_user_stats(cls):
        try:
            # Total users
            total_users_response = supabase.table("users").select("id", count="exact").execute()
            total_users = total_users_response.count

            # Total coins in circulation
            all_users_coins = supabase.table("users").select("coins").execute()
            total_coins = sum(user["coins"] for user in all_users_coins.data) if all_users_coins.data else 0

            # Total taps
            all_users_taps = supabase.table("users").select("total_taps").execute()
            total_taps = sum(user["total_taps"] for user in all_users_taps.data) if all_users_taps.data else 0

            return {
                "total_users": total_users,
                "total_coins": total_coins,
                "total_taps": total_taps
            }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {"total_users": 0, "total_coins": 0, "total_taps": 0}

# Transaction model for Supabase
class Transaction:
    def __init__(self, user_id, transaction_type, amount, description="", **kwargs):
        self.user_id = user_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.description = description
        self.created_at = kwargs.get("created_at", datetime.utcnow().isoformat())
        self.id = kwargs.get("id", None)

    def save(self):
        """Save transaction to Supabase"""
        try:
            transaction_data = {
                "user_id": self.user_id,
                "transaction_type": self.transaction_type,
                "amount": self.amount,
                "description": self.description,
                "created_at": self.created_at
            }
            response = supabase.table("transactions").insert(transaction_data).execute()
            if response.data:
                self.id = response.data[0]["id"]
            return True
        except Exception as e:
            print(f"Error saving transaction: {e}")
            return False

    @classmethod
    def get_by_user_id(cls, user_id, limit=50):
        """Get transactions by user ID"""
        try:
            response = supabase.table("transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            return [cls(**transaction) for transaction in response.data]
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []

# Upgrade model for Supabase
class Upgrade:
    def __init__(self, name, upgrade_type, base_cost, cost_multiplier, max_level, **kwargs):
        self.name = name
        self.upgrade_type = upgrade_type
        self.base_cost = base_cost
        self.cost_multiplier = cost_multiplier
        self.max_level = max_level
        self.id = kwargs.get("id", None)

    @classmethod
    def get_all_upgrades(cls):
        """Get all available upgrades"""
        # For now, return hardcoded upgrades
        return [
            cls("Tap Power", "tap_power", 100, 1.5, 50),
            cls("Energy Capacity", "energy_capacity", 200, 1.6, 30),
            cls("Energy Regeneration", "energy_regen", 150, 1.4, 40)
        ]

# UserUpgrade model for Supabase
class UserUpgrade:
    def __init__(self, user_id, upgrade_type, level, **kwargs):
        self.user_id = user_id
        self.upgrade_type = upgrade_type
        self.level = level
        self.id = kwargs.get("id", None)

    def save(self):
        """Save user upgrade to Supabase"""
        try:
            upgrade_data = {
                "user_id": self.user_id,
                "upgrade_type": self.upgrade_type,
                "level": self.level
            }
            
            # Check if upgrade exists
            existing = supabase.table("user_upgrades").select("*").eq("user_id", self.user_id).eq("upgrade_type", self.upgrade_type).execute()
            
            if existing.data:
                # Update existing
                response = supabase.table("user_upgrades").update(upgrade_data).eq("user_id", self.user_id).eq("upgrade_type", self.upgrade_type).execute()
            else:
                # Create new
                response = supabase.table("user_upgrades").insert(upgrade_data).execute()
                if response.data:
                    self.id = response.data[0]["id"]
            return True
        except Exception as e:
            print(f"Error saving user upgrade: {e}")
            return False

    @classmethod
    def get_by_user_id(cls, user_id):
        """Get user upgrades by user ID"""
        try:
            response = supabase.table("user_upgrades").select("*").eq("user_id", user_id).execute()
            return [cls(**upgrade) for upgrade in response.data]
        except Exception as e:
            print(f"Error getting user upgrades: {e}")
            return []


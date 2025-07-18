from src.config.database import supabase
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User:
    def __init__(self, telegram_id, username=None, first_name=None, coins=2500, energy=100, 
                 max_energy=100, tap_power=1, energy_regen_rate=1, last_energy_update=None,
                 referred_by=None, referral_count=0, referral_earnings=0, upi_id=None):
        
        # Safe type conversion for all attributes
        self.telegram_id = str(telegram_id).strip()
        self.username = username or f"user_{self.telegram_id}"
        self.first_name = first_name or "User"
        
        # Numeric fields with safe conversion
        self.coins = self._safe_int_convert(coins, 2500)
        self.energy = self._safe_float_convert(energy, 100.0)
        self.max_energy = self._safe_int_convert(max_energy, 100)
        self.tap_power = self._safe_int_convert(tap_power, 1)
        self.energy_regen_rate = self._safe_int_convert(energy_regen_rate, 1)
        self.referral_count = self._safe_int_convert(referral_count, 0)
        self.referral_earnings = self._safe_int_convert(referral_earnings, 0)
        
        # Time fields
        self.last_energy_update = self._safe_int_convert(last_energy_update, int(time.time()))
        
        # Optional fields
        self.referred_by = referred_by
        self.upi_id = upi_id
        
        # Validate data integrity
        self._validate_data()
    
    def _safe_int_convert(self, value, default=0):
        """Safely convert value to integer with fallback"""
        try:
            if value is None:
                return default
            if isinstance(value, str):
                if value.strip() == '' or value.lower() in ['null', 'undefined', 'none']:
                    return default
                # Handle string floats like "100.0"
                return int(float(value))
            if isinstance(value, float):
                return int(value)
            return int(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert {value} to int, using default {default}: {str(e)}")
            return default
    
    def _safe_float_convert(self, value, default=0.0):
        """Safely convert value to float with fallback"""
        try:
            if value is None:
                return default
            if isinstance(value, str):
                if value.strip() == '' or value.lower() in ['null', 'undefined', 'none']:
                    return default
                return float(value)
            return float(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert {value} to float, using default {default}: {str(e)}")
            return default
    
    def _validate_data(self):
        """Validate and fix data integrity"""
        # Ensure minimum values
        if self.coins < 0:
            self.coins = 0
        
        if self.energy < 0:
            self.energy = 0.0
        elif self.energy > self.max_energy:
            self.energy = float(self.max_energy)
        
        if self.max_energy < 100:
            self.max_energy = 100
        
        if self.tap_power < 1:
            self.tap_power = 1
        
        if self.energy_regen_rate < 1:
            self.energy_regen_rate = 1
        
        if self.referral_count < 0:
            self.referral_count = 0
        
        if self.referral_earnings < 0:
            self.referral_earnings = 0
        
        # Validate telegram_id
        if not self.telegram_id or self.telegram_id in ['null', 'undefined', 'none', '']:
            raise ValueError("Invalid telegram_id")
    
    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by telegram ID with enhanced error handling"""
        try:
            telegram_id = str(telegram_id).strip()
            
            if not telegram_id or telegram_id in ['null', 'undefined', 'none', '']:
                logger.error(f"Invalid telegram_id provided: {telegram_id}")
                return None
            
            logger.debug(f"Fetching user with telegram_id: {telegram_id}")
            
            response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.debug(f"User found: {telegram_id}")
                
                # Create User object with safe data conversion
                user = cls(
                    telegram_id=user_data.get("telegram_id"),
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    coins=user_data.get("coins", 2500),
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
                
                return user
            else:
                logger.debug(f"User not found: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {str(e)}")
            return None
    
    def save(self):
        """Save user to database with enhanced error handling"""
        try:
            # Validate data before saving
            self._validate_data()
            
            # Prepare data for database with explicit type conversion
            user_data = {
                "telegram_id": str(self.telegram_id),
                "username": str(self.username),
                "first_name": str(self.first_name),
                "coins": int(self.coins),
                "energy": float(self.energy),
                "max_energy": int(self.max_energy),
                "tap_power": int(self.tap_power),
                "energy_regen_rate": int(self.energy_regen_rate),
                "last_energy_update": int(self.last_energy_update),
                "referral_count": int(self.referral_count),
                "referral_earnings": int(self.referral_earnings)
            }
            
            # Add optional fields if they exist
            if self.referred_by:
                user_data["referred_by"] = str(self.referred_by)
            
            if self.upi_id:
                user_data["upi_id"] = str(self.upi_id)
            
            logger.debug(f"Saving user data for {self.telegram_id}: {user_data}")
            
            # Try to update first, then insert if not exists
            response = supabase.table("users").upsert(user_data).execute()
            
            if response.data:
                logger.debug(f"User saved successfully: {self.telegram_id}")
                return True
            else:
                logger.error(f"Failed to save user: {self.telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {str(e)}")
            return False
    
    def update_energy(self):
        """Update energy based on time passed with enhanced calculation"""
        try:
            current_time = int(time.time())
            time_passed = current_time - self.last_energy_update
            
            if time_passed > 0:
                # Energy regenerates at 1 per 30 seconds (configurable via energy_regen_rate)
                energy_to_add = (time_passed / 30) * self.energy_regen_rate
                
                # Add energy but don't exceed max
                self.energy = min(float(self.max_energy), self.energy + energy_to_add)
                self.last_energy_update = current_time
                
                logger.debug(f"Energy updated for {self.telegram_id}: +{energy_to_add:.2f}, current: {self.energy}")
                
        except Exception as e:
            logger.error(f"Error updating energy for {self.telegram_id}: {str(e)}")
    
    def can_tap(self):
        """Check if user can tap (has enough energy)"""
        return self.energy >= 1.0
    
    def tap(self):
        """Perform tap action with enhanced validation"""
        try:
            if not self.can_tap():
                logger.debug(f"User {self.telegram_id} cannot tap: insufficient energy ({self.energy})")
                return False
            
            # Deduct energy and add coins
            self.energy = max(0.0, self.energy - 1.0)
            self.coins += self.tap_power
            
            logger.debug(f"Tap successful for {self.telegram_id}: +{self.tap_power} coins, -{1} energy")
            return True
            
        except Exception as e:
            logger.error(f"Error during tap for {self.telegram_id}: {str(e)}")
            return False
    
    def add_referral(self):
        """Add a referral to this user with enhanced handling"""
        try:
            self.referral_count += 1
            
            # Give referral bonus (500 coins per referral)
            referral_bonus = 500
            self.referral_earnings += referral_bonus
            self.coins += referral_bonus
            
            logger.info(f"Referral added for {self.telegram_id}: +{referral_bonus} coins, total referrals: {self.referral_count}")
            
        except Exception as e:
            logger.error(f"Error adding referral for {self.telegram_id}: {str(e)}")
    
    def can_upgrade(self, upgrade_type, cost):
        """Check if user can afford an upgrade"""
        return self.coins >= cost
    
    def apply_upgrade(self, upgrade_type):
        """Apply upgrade to user with enhanced validation"""
        try:
            upgrade_costs = {
                "tap_power": lambda level: 100 * (2 ** level),
                "max_energy": lambda level: 50 * (2 ** level),
                "energy_regen": lambda level: 75 * (2 ** level)
            }
            
            if upgrade_type == "tap_power":
                cost = upgrade_costs["tap_power"](self.tap_power - 1)
                if self.can_upgrade(upgrade_type, cost):
                    self.coins -= cost
                    self.tap_power += 1
                    logger.info(f"Tap power upgraded for {self.telegram_id}: level {self.tap_power}, cost {cost}")
                    return True
                    
            elif upgrade_type == "max_energy":
                current_level = (self.max_energy - 100) // 20
                cost = upgrade_costs["max_energy"](current_level)
                if self.can_upgrade(upgrade_type, cost):
                    self.coins -= cost
                    self.max_energy += 20
                    logger.info(f"Max energy upgraded for {self.telegram_id}: {self.max_energy}, cost {cost}")
                    return True
                    
            elif upgrade_type == "energy_regen":
                cost = upgrade_costs["energy_regen"](self.energy_regen_rate - 1)
                if self.can_upgrade(upgrade_type, cost):
                    self.coins -= cost
                    self.energy_regen_rate += 1
                    logger.info(f"Energy regen upgraded for {self.telegram_id}: level {self.energy_regen_rate}, cost {cost}")
                    return True
            
            logger.warning(f"Upgrade failed for {self.telegram_id}: {upgrade_type}, insufficient coins")
            return False
            
        except Exception as e:
            logger.error(f"Error applying upgrade {upgrade_type} for {self.telegram_id}: {str(e)}")
            return False
    
    def to_dict(self):
        """Convert user to dictionary with safe type conversion"""
        try:
            return {
                "telegram_id": str(self.telegram_id),
                "username": str(self.username),
                "first_name": str(self.first_name),
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
        except Exception as e:
            logger.error(f"Error converting user {self.telegram_id} to dict: {str(e)}")
            # Return minimal safe data
            return {
                "telegram_id": str(self.telegram_id),
                "username": str(self.username),
                "first_name": str(self.first_name),
                "coins": 2500,
                "energy": 100.0,
                "max_energy": 100,
                "tap_power": 1,
                "energy_regen_rate": 1,
                "last_energy_update": int(time.time()),
                "referred_by": None,
                "referral_count": 0,
                "referral_earnings": 0,
                "upi_id": None
            }
    
    def __str__(self):
        return f"User(telegram_id={self.telegram_id}, username={self.username}, coins={self.coins})"


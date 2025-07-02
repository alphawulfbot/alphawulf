from src.config.database import db_config
import time
import random
import string

class User:
    def __init__(self, telegram_id, username=None, first_name=None, last_name=None):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.coins = 2500
        self.energy = 100
        self.max_energy = 100
        self.tap_power = 1
        self.energy_regen_rate = 1
        self.total_taps = 0
        self.referral_code = self.generate_referral_code()
        self.referred_by = None
        self.referral_count = 0
        self.referral_earnings = 0
    
    def generate_referral_code(self):
        """Generate a unique referral code"""
        return f"REF{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        """Get user by Telegram ID"""
        try:
            result = db_config.supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            if result.data:
                user_data = result.data[0]
                user = cls(
                    telegram_id=user_data['telegram_id'],
                    username=user_data['username'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )
                user.coins = user_data['coins']
                user.energy = user_data['energy']
                user.max_energy = user_data['max_energy']
                user.tap_power = user_data['tap_power']
                user.energy_regen_rate = user_data['energy_regen_rate']
                user.total_taps = user_data['total_taps']
                user.referral_code = user_data['referral_code']
                user.referred_by = user_data['referred_by']
                user.referral_count = user_data['referral_count']
                user.referral_earnings = user_data['referral_earnings']
                user.id = user_data['id']
                return user
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def save(self):
        """Save user to database"""
        try:
            # Check if user exists
            existing = self.get_by_telegram_id(self.telegram_id)
            
            user_data = {
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
                'last_energy_update': 'now()'
            }
            
            if existing:
                # Update existing user
                result = db_config.supabase.table('users').update(user_data).eq('telegram_id', self.telegram_id).execute()
            else:
                # Create new user
                result = db_config.supabase.table('users').insert(user_data).execute()
                if result.data:
                    self.id = result.data[0]['id']
            
            return True
        except Exception as e:
            print(f"Error saving user: {e}")
            return False
    
    def add_coins(self, amount):
        """Add coins to user"""
        self.coins += amount
        return self.save()
    
    def spend_coins(self, amount):
        """Spend coins if user has enough"""
        if self.coins >= amount:
            self.coins -= amount
            return self.save()
        return False
    
    def tap(self, taps=1):
        """Process tap action"""
        if self.energy >= taps:
            self.energy -= taps
            coins_earned = taps * self.tap_power
            self.coins += coins_earned
            self.total_taps += taps
            
            # Update energy regeneration
            self.update_energy()
            
            return self.save()
        return False
    
    def update_energy(self):
        """Update energy based on time passed"""
        # This would typically be called periodically or on user action
        # For simplicity, we'll regenerate 1 energy per minute
        pass
    
    @classmethod
    def get_all_users(cls):
        """Get all users for admin panel"""
        try:
            result = db_config.supabase.table('users').select('*').order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    @classmethod
    def get_user_stats(cls):
        """Get user statistics for admin panel"""
        try:
            # Total users
            total_users = db_config.supabase.table('users').select('id', count='exact').execute()
            
            # Total coins in circulation
            coins_result = db_config.execute_query("SELECT SUM(coins) as total_coins FROM users")
            total_coins = coins_result[0]['total_coins'] if coins_result else 0
            
            # Total taps
            taps_result = db_config.execute_query("SELECT SUM(total_taps) as total_taps FROM users")
            total_taps = taps_result[0]['total_taps'] if taps_result else 0
            
            return {
                'total_users': total_users.count,
                'total_coins': total_coins,
                'total_taps': total_taps
            }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {'total_users': 0, 'total_coins': 0, 'total_taps': 0}
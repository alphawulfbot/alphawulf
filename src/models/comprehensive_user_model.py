import os
import time
from datetime import datetime
from supabase import create_client, Client
from typing import Optional, Dict, Any, List

class User:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print(f"Supabase client initialized successfully")

    def safe_to_int(self, value, default=0):
        """Safely convert value to integer"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                # Handle datetime strings by converting to Unix timestamp
                if 'T' in value or '-' in value:
                    try:
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        return int(dt.timestamp())
                    except:
                        pass
                return int(float(value))
            except (ValueError, TypeError):
                return default
        return default

    def safe_to_str(self, value, default=""):
        """Safely convert value to string"""
        if value is None:
            return default
        return str(value)

    def get_current_timestamp(self):
        """Get current Unix timestamp"""
        return int(time.time())

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with 1000 coins joining bonus"""
        try:
            current_time = self.get_current_timestamp()
            
            # Prepare user data with proper type conversion
            prepared_data = {
                'telegram_id': self.safe_to_int(user_data.get('telegram_id')),
                'username': self.safe_to_str(user_data.get('username', '')),
                'first_name': self.safe_to_str(user_data.get('first_name', '')),
                'last_name': self.safe_to_str(user_data.get('last_name', '')),
                'coins': 1000,  # 1000 coins joining bonus
                'energy': self.safe_to_int(user_data.get('energy', 100)),
                'max_energy': self.safe_to_int(user_data.get('max_energy', 100)),
                'tap_power': self.safe_to_int(user_data.get('tap_power', 1)),
                'energy_regen_rate': self.safe_to_int(user_data.get('energy_regen_rate', 1)),
                'last_energy_update': current_time,
                'last_tap_time': current_time,
                'created_at': current_time,
                'updated_at': current_time,
                'is_admin': False,
                'power': self.safe_to_int(user_data.get('power', 1)),
                'referrals': '[]',
                'referred_by': self.safe_to_int(user_data.get('referred_by')),
                'referral_code': self.safe_to_str(user_data.get('referral_code', '')),
                'referral_count': 0,
                'referral_earnings': 0,
                'upi_id': self.safe_to_str(user_data.get('upi_id', ''))
            }

            print(f"Creating user with data: {prepared_data}")

            # Insert user
            result = self.supabase.table('users').insert(prepared_data).execute()
            
            if result.data:
                user = result.data[0]
                print(f"User created successfully: {user.get('telegram_id')}")
                
                # Create joining bonus transaction
                self.create_transaction(
                    user_id=user.get('telegram_id'),
                    transaction_type='bonus',
                    description='Joining Bonus',
                    amount=1000,
                    balance_after=1000
                )
                
                return self.format_user_data(user)
            else:
                raise Exception("Failed to create user - no data returned")

        except Exception as e:
            print(f"Error creating user: {str(e)}")
            raise e

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram_id"""
        try:
            result = self.supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            
            if result.data:
                user = result.data[0]
                print(f"User found: {telegram_id}")
                return self.format_user_data(user)
            else:
                print(f"User not found: {telegram_id}")
                return None

        except Exception as e:
            print(f"Error getting user {telegram_id}: {str(e)}")
            return None

    def update_user(self, telegram_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user data"""
        try:
            current_time = self.get_current_timestamp()
            
            # Prepare update data with proper type conversion
            prepared_data = {}
            for key, value in update_data.items():
                if key in ['coins', 'energy', 'max_energy', 'tap_power', 'energy_regen_rate', 
                          'last_energy_update', 'last_tap_time', 'power', 'referred_by', 
                          'referral_count', 'referral_earnings']:
                    prepared_data[key] = self.safe_to_int(value)
                elif key in ['username', 'first_name', 'last_name', 'referral_code', 'upi_id', 'referrals']:
                    prepared_data[key] = self.safe_to_str(value)
                elif key == 'is_admin':
                    prepared_data[key] = bool(value)
            
            # Always update the timestamp
            prepared_data['updated_at'] = current_time

            print(f"Updating user {telegram_id} with data: {prepared_data}")

            result = self.supabase.table('users').update(prepared_data).eq('telegram_id', telegram_id).execute()
            
            if result.data:
                user = result.data[0]
                print(f"User updated successfully: {telegram_id}")
                return self.format_user_data(user)
            else:
                raise Exception("Failed to update user - no data returned")

        except Exception as e:
            print(f"Error updating user {telegram_id}: {str(e)}")
            raise e

    def format_user_data(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Format user data with proper type conversion"""
        return {
            'telegram_id': self.safe_to_int(user.get('telegram_id')),
            'username': self.safe_to_str(user.get('username', '')),
            'first_name': self.safe_to_str(user.get('first_name', '')),
            'last_name': self.safe_to_str(user.get('last_name', '')),
            'coins': self.safe_to_int(user.get('coins', 0)),
            'energy': self.safe_to_int(user.get('energy', 100)),
            'max_energy': self.safe_to_int(user.get('max_energy', 100)),
            'tap_power': self.safe_to_int(user.get('tap_power', 1)),
            'energy_regen_rate': self.safe_to_int(user.get('energy_regen_rate', 1)),
            'last_energy_update': self.safe_to_int(user.get('last_energy_update', 0)),
            'last_tap_time': self.safe_to_int(user.get('last_tap_time', 0)),
            'created_at': self.safe_to_int(user.get('created_at', 0)),
            'updated_at': self.safe_to_int(user.get('updated_at', 0)),
            'is_admin': bool(user.get('is_admin', False)),
            'power': self.safe_to_int(user.get('power', 1)),
            'referrals': self.safe_to_str(user.get('referrals', '[]')),
            'referred_by': self.safe_to_int(user.get('referred_by')),
            'referral_code': self.safe_to_str(user.get('referral_code', '')),
            'referral_count': self.safe_to_int(user.get('referral_count', 0)),
            'referral_earnings': self.safe_to_int(user.get('referral_earnings', 0)),
            'upi_id': self.safe_to_str(user.get('upi_id', ''))
        }

    def create_transaction(self, user_id: int, transaction_type: str, description: str, 
                          amount: int, balance_after: int = None) -> Dict[str, Any]:
        """Create a new transaction record"""
        try:
            current_time = self.get_current_timestamp()
            
            # Get current balance if not provided
            if balance_after is None:
                user = self.get_user(user_id)
                balance_after = user.get('coins', 0) if user else 0
            
            transaction_data = {
                'user_id': user_id,
                'transaction_type': transaction_type,
                'description': description,
                'amount': amount,
                'balance_before': balance_after - amount,
                'balance_after': balance_after,
                'created_at': current_time,
                'status': 'completed'
            }

            print(f"Creating transaction: {transaction_data}")

            result = self.supabase.table('transactions').insert(transaction_data).execute()
            
            if result.data:
                transaction = result.data[0]
                print(f"Transaction created successfully: {transaction.get('id')}")
                return self.format_transaction_data(transaction)
            else:
                raise Exception("Failed to create transaction - no data returned")

        except Exception as e:
            print(f"Error creating transaction: {str(e)}")
            # Don't raise exception for transaction logging failures
            return {}

    def get_user_transactions(self, user_id: int, limit: int = 50, 
                             transaction_type: str = None) -> List[Dict[str, Any]]:
        """Get user transaction history"""
        try:
            query = self.supabase.table('transactions').select('*').eq('user_id', user_id)
            
            if transaction_type:
                query = query.eq('transaction_type', transaction_type)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                transactions = [self.format_transaction_data(t) for t in result.data]
                print(f"Retrieved {len(transactions)} transactions for user {user_id}")
                return transactions
            else:
                print(f"No transactions found for user {user_id}")
                return []

        except Exception as e:
            print(f"Error getting transactions for user {user_id}: {str(e)}")
            return []

    def format_transaction_data(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Format transaction data with proper type conversion"""
        return {
            'id': self.safe_to_int(transaction.get('id')),
            'user_id': self.safe_to_int(transaction.get('user_id')),
            'transaction_type': self.safe_to_str(transaction.get('transaction_type', '')),
            'description': self.safe_to_str(transaction.get('description', '')),
            'amount': self.safe_to_int(transaction.get('amount', 0)),
            'balance_before': self.safe_to_int(transaction.get('balance_before', 0)),
            'balance_after': self.safe_to_int(transaction.get('balance_after', 0)),
            'created_at': self.safe_to_int(transaction.get('created_at', 0)),
            'status': self.safe_to_str(transaction.get('status', 'completed'))
        }

    def update_energy(self, telegram_id: int) -> Dict[str, Any]:
        """Update user energy based on time elapsed"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                raise Exception("User not found")

            current_time = self.get_current_timestamp()
            last_update = user.get('last_energy_update', current_time)
            time_diff = current_time - last_update
            
            # Calculate energy to add (1 energy per 30 seconds)
            energy_to_add = (time_diff // 30) * user.get('energy_regen_rate', 1)
            
            if energy_to_add > 0:
                new_energy = min(user.get('max_energy', 100), 
                               user.get('energy', 0) + energy_to_add)
                
                update_data = {
                    'energy': new_energy,
                    'last_energy_update': current_time
                }
                
                updated_user = self.update_user(telegram_id, update_data)
                print(f"Energy updated for user {telegram_id}: +{energy_to_add} energy")
                return updated_user
            
            return user

        except Exception as e:
            print(f"Error updating energy for user {telegram_id}: {str(e)}")
            raise e

    def process_tap(self, telegram_id: int, taps: int = 1) -> Dict[str, Any]:
        """Process tap action and update user data"""
        try:
            # Update energy first
            user = self.update_energy(telegram_id)
            
            if user.get('energy', 0) < taps:
                raise Exception("Insufficient energy")

            current_time = self.get_current_timestamp()
            tap_power = user.get('tap_power', 1)
            coins_earned = taps * tap_power
            
            update_data = {
                'coins': user.get('coins', 0) + coins_earned,
                'energy': user.get('energy', 0) - taps,
                'last_tap_time': current_time
            }
            
            updated_user = self.update_user(telegram_id, update_data)
            
            # Create transaction record
            self.create_transaction(
                user_id=telegram_id,
                transaction_type='tap',
                description=f'Tap Earning ({taps} taps)',
                amount=coins_earned,
                balance_after=updated_user.get('coins', 0)
            )
            
            print(f"Tap processed for user {telegram_id}: {taps} taps, {coins_earned} coins earned")
            return updated_user

        except Exception as e:
            print(f"Error processing tap for user {telegram_id}: {str(e)}")
            raise e

    def process_game_reward(self, telegram_id: int, game_type: str, reward: int) -> Dict[str, Any]:
        """Process game reward and update user data"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                raise Exception("User not found")

            update_data = {
                'coins': user.get('coins', 0) + reward
            }
            
            updated_user = self.update_user(telegram_id, update_data)
            
            # Create transaction record
            self.create_transaction(
                user_id=telegram_id,
                transaction_type='game',
                description=f'{game_type} Game Reward',
                amount=reward,
                balance_after=updated_user.get('coins', 0)
            )
            
            print(f"Game reward processed for user {telegram_id}: {game_type}, {reward} coins")
            return updated_user

        except Exception as e:
            print(f"Error processing game reward for user {telegram_id}: {str(e)}")
            raise e

    def process_upgrade(self, telegram_id: int, upgrade_type: str, cost: int, 
                       upgrade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process upgrade purchase and update user data"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                raise Exception("User not found")

            if user.get('coins', 0) < cost:
                raise Exception("Insufficient coins")

            # Deduct cost and apply upgrade
            update_data = {
                'coins': user.get('coins', 0) - cost,
                **upgrade_data
            }
            
            updated_user = self.update_user(telegram_id, update_data)
            
            # Create transaction record
            self.create_transaction(
                user_id=telegram_id,
                transaction_type='upgrade',
                description=f'{upgrade_type} Upgrade',
                amount=-cost,
                balance_after=updated_user.get('coins', 0)
            )
            
            print(f"Upgrade processed for user {telegram_id}: {upgrade_type}, cost {cost}")
            return updated_user

        except Exception as e:
            print(f"Error processing upgrade for user {telegram_id}: {str(e)}")
            raise e

    def process_withdrawal(self, telegram_id: int, amount: int, upi_id: str) -> Dict[str, Any]:
        """Process withdrawal request"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                raise Exception("User not found")

            if user.get('coins', 0) < amount:
                raise Exception("Insufficient coins")

            if amount < 1000:
                raise Exception("Minimum withdrawal is 1000 coins")

            # Deduct coins
            update_data = {
                'coins': user.get('coins', 0) - amount,
                'upi_id': upi_id
            }
            
            updated_user = self.update_user(telegram_id, update_data)
            
            # Create transaction record
            self.create_transaction(
                user_id=telegram_id,
                transaction_type='withdrawal',
                description=f'UPI Withdrawal to {upi_id}',
                amount=-amount,
                balance_after=updated_user.get('coins', 0)
            )
            
            print(f"Withdrawal processed for user {telegram_id}: {amount} coins to {upi_id}")
            return updated_user

        except Exception as e:
            print(f"Error processing withdrawal for user {telegram_id}: {str(e)}")
            raise e


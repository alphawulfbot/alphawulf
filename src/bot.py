import os
import requests
import json
from datetime import datetime
from src.models.user import db, User, Transaction, Upgrade, UserUpgrade

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        
    def send_message(self, chat_id, text, reply_markup=None):
        """Send a message to a Telegram chat"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        response = requests.post(url, data=data)
        return response.json()
    
    def send_photo(self, chat_id, photo_path, caption=None, reply_markup=None):
        """Send a photo to a Telegram chat"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'caption': caption or '',
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            response = requests.post(url, data=data, files=files)
        return response.json()
    
    def get_user_profile_photos(self, user_id):
        """Get user profile photos"""
        url = f"{self.base_url}/getUserProfilePhotos"
        data = {'user_id': user_id, 'limit': 1}
        response = requests.post(url, data=data)
        return response.json()
    
    def create_inline_keyboard(self, buttons):
        """Create inline keyboard markup"""
        return {
            'inline_keyboard': buttons
        }
    
    def handle_start_command(self, message):
        """Handle /start command"""
        user_data = message['from']
        telegram_id = user_data['id']
        
        # Check for referral parameter
        referrer_id = None
        if 'text' in message and message['text'].startswith('/start ref_'):
            try:
                referrer_id = int(message['text'].split('ref_')[1])
            except (IndexError, ValueError):
                pass
        
        # Check if user exists
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                coins=2500,  # Welcome bonus
                energy=100
            )
            db.session.add(user)
            db.session.commit()
            
            # Process referral if exists
            if referrer_id and referrer_id != telegram_id:
                try:
                    import requests
                    webhook_url = os.getenv("WEBHOOK_URL", "https://p9hwiqc5v1nk.manus.space")
                    referral_url = f"{webhook_url}/api/process_referral"
                    requests.post(referral_url, json={
                                    "referrer_telegram_id": referrer_id,
                                    "referred_telegram_id": telegram_id
                                })
                except Exception as e:
                    print(f"Failed to process referral: {e}")
            
            welcome_text = f"""🐺 <b>Welcome to Alpha Wulf!</b> 🐺

Hello {user.first_name or 'Alpha'}! 

🎁 You've received <b>2,500 Wolf Coins</b> as a welcome bonus!

🎮 <b>How to Play:</b>
• Tap the wolf to earn coins
• Use energy wisely (it regenerates over time)
• Play mini-games for bonus coins
• Upgrade your abilities
• Withdraw real money via UPI

Ready to become the Alpha? Let's start tapping! 🚀"""
        else:
            user.update_energy()  # Update energy based on time passed
            welcome_text = f"""🐺 <b>Welcome back, Alpha {user.first_name or 'Wolf'}!</b> 🐺

💰 Coins: <b>{user.coins:,}</b>
⚡ Energy: <b>{user.energy}/{user.max_energy}</b>
💪 Tap Power: <b>{user.tap_power}</b>

Ready to continue your hunt? 🎯"""
                # Create main menu keyboard
        base_url = os.getenv('BASE_URL', 'https://xlhyimcjx1g7.manus.space')
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎮 Play Alpha Wulf", "web_app": {"url": base_url}}],
                [{"text": "⬆️ Upgrades", "web_app": {"url": f"{base_url}/upgrades.html"}}],
                [{"text": "🎯 Mini Games", "web_app": {"url": f"{base_url}/minigames.html"}}],
                [{"text": "💳 Withdraw", "web_app": {"url": f"{base_url}/withdraw.html"}}],
                [{"text": "👥 Referrals", "web_app": {"url": f"{base_url}/referrals.html"}}]
            ]
        }
        
        self.send_message(message['chat']['id'], welcome_text, keyboard)
    
    def handle_balance_command(self, message):
        """Handle balance inquiry"""
        user_data = message['from']
        telegram_id = user_data['id']
        
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            self.send_message(message['chat']['id'], "Please start the bot first with /start")
            return
        
        user.update_energy()
        
        balance_text = f"""🐺 <b>Alpha {user.first_name or 'Wolf'} Stats</b> 🐺

💰 <b>Wolf Coins:</b> {user.coins:,}
⚡ <b>Energy:</b> {user.energy}/{user.max_energy}
💪 <b>Tap Power:</b> {user.tap_power} coins per tap
🔋 <b>Energy Regen:</b> {user.energy_regen_rate}/min

📊 <b>Lifetime Stats:</b>
• Total Earned: {user.total_earned:,} coins
• Total Withdrawn: ₹{user.total_withdrawn:,}

🎯 Keep tapping to earn more coins!"""
        
        keyboard = self.create_inline_keyboard([
            [{'text': '🎯 Start Tapping', 'callback_data': 'tap_game'}],
            [{'text': '🏠 Main Menu', 'callback_data': 'main_menu'}]
        ])
        
        self.send_message(message['chat']['id'], balance_text, keyboard)
    
    def handle_help_command(self, message):
        """Handle help command"""
        help_text = """🐺 <b>Alpha Wulf - Help Guide</b> 🐺

🎯 <b>Tapping Game:</b>
• Tap the wolf to earn coins
• Each tap consumes 1 energy
• Energy regenerates over time

🎮 <b>Mini Games:</b>
• Wolf Hunt: Find hidden wolves
• Pack Leader: Memory game
• Howl Challenge: Timing game

⬆️ <b>Upgrades:</b>
• Increase tap power
• Boost energy regeneration
• Expand max energy

💳 <b>Withdrawal:</b>
• Minimum: 1,000 coins = ₹10
• Use UPI for instant transfers
• Processing time: 24-48 hours

🔄 <b>Energy System:</b>
• Regenerates 1 energy per minute
• Max energy increases with upgrades
• Plan your tapping sessions!

Need more help? Contact @AlphaWulfSupport"""
        
        keyboard = self.create_inline_keyboard([
            [{'text': '🏠 Main Menu', 'callback_data': 'main_menu'}]
        ])
        
        self.send_message(message['chat']['id'], help_text, keyboard)
    
    def handle_callback_query(self, callback_query):
        """Handle inline keyboard button presses"""
        data = callback_query['data']
        message = callback_query['message']
        user_data = callback_query['from']
        
        if data == 'main_menu':
            # Simulate a start command to show main menu
            fake_message = {
                'from': user_data,
                'chat': message['chat']
            }
            self.handle_start_command(fake_message)
        elif data == 'balance':
            fake_message = {
                'from': user_data,
                'chat': message['chat']
            }
            self.handle_balance_command(fake_message)
        elif data == 'help':
            fake_message = {
                'from': user_data,
                'chat': message['chat']
            }
            self.handle_help_command(fake_message)
        # Add more callback handlers as needed
        
        # Answer the callback query to remove loading state
        answer_url = f"{self.base_url}/answerCallbackQuery"
        requests.post(answer_url, data={'callback_query_id': callback_query['id']})


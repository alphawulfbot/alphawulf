from flask import Blueprint, request, jsonify
from src.bot import TelegramBot
from src.models.user import db
import os
import requests

bot_bp = Blueprint('bot', __name__)

# Initialize bot with token from environment variable
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
bot = TelegramBot(BOT_TOKEN)

@bot_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates"""
    try:
        update = request.get_json()
        
        if 'message' in update:
            message = update['message']
            
            # Handle text messages
            if 'text' in message:
                text = message['text']
                
                if text.startswith('/start'):
                    bot.handle_start_command(message)
                elif text.startswith('/balance'):
                    bot.handle_balance_command(message)
                elif text.startswith('/help'):
                    bot.handle_help_command(message)
                else:
                    # Handle unknown commands
                    bot.send_message(
                        message['chat']['id'],
                        "🐺 Unknown command! Use /help to see available commands."
                    )
        
        elif 'callback_query' in update:
            # Handle inline keyboard button presses
            bot.handle_callback_query(update['callback_query'])
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        print(f"Error processing update: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Set the webhook URL for the bot"""
    data = request.get_json()
    webhook_url = data.get('url')
    
    if not webhook_url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Set webhook
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, data={'url': webhook_url})
    
    return jsonify(response.json())

@bot_bp.route('/bot_info', methods=['GET'])
def bot_info():
    """Get bot information"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    response = requests.get(url)
    return jsonify(response.json())


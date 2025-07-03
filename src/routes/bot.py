from flask import Blueprint, request, jsonify
import os
import requests

bot_bp = Blueprint('bot', __name__)

# Initialize bot with token from environment variable
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

@bot_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates"""
    try:
        update = request.get_json()
        
        # For now, just acknowledge the webhook
        # Bot functionality can be implemented later
        print(f"Received webhook update: {update}")
        
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
    response = requests.post(url, data={'url': webhook_url} )
    
    return jsonify(response.json())

@bot_bp.route('/bot_info', methods=['GET'])
def bot_info():
    """Get bot information"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    response = requests.get(url )
    return jsonify(response.json())

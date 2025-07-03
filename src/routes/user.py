from flask import Blueprint, request, jsonify
from src.models.user import User
import hashlib
import hmac
import json
from urllib.parse import unquote
from datetime import datetime

user_bp = Blueprint('user', __name__)

def verify_telegram_auth(auth_data, bot_token):
    """Verify Telegram Web App authentication data"""
    try:
        # Parse the auth data
        auth_dict = {}
        for item in auth_data.split('&'):
            key, value = item.split('=', 1)
            auth_dict[key] = unquote(value)
        
        # Extract hash and create data string
        received_hash = auth_dict.pop('hash', '')
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_dict.items())])
        
        # Create secret key
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        
        # Calculate expected hash
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(received_hash, expected_hash)
    except Exception as e:
        print(f"Auth verification error: {e}")
        return False

@user_bp.route('/auth', methods=['POST'])
def authenticate_user():
    """Authenticate user via Telegram Web App data"""
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        username = data.get('username', '')
        
        if not telegram_id:
            return jsonify({'error': 'Telegram ID is required'}), 400
        
        # Find or create user using Supabase
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                coins=2500,  # Welcome bonus
                total_earned=2500
            )
            user.save()
        else:
            # Update user info
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.username = username or user.username
            user.last_activity = datetime.utcnow().isoformat()
            user.update_energy()
            user.save()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
    
    except Exception as e:
        print(f"Authentication error: {e}")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/profile/<int:telegram_id>', methods=['GET'])
def get_user_profile(telegram_id):
    """Get user profile by Telegram ID"""
    user = User.get_by_telegram_id(telegram_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.update_energy()
    return jsonify(user.to_dict())

@user_bp.route('/tap', methods=['POST'])
def handle_tap():
    """Handle tap action"""
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        taps = data.get('taps', 1)
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.update_energy()
        
        # Check if user has enough energy
        if user.energy < taps:
            return jsonify({'error': 'Not enough energy'}), 400
        
        # Calculate coins earned
        coins_earned = taps * user.tap_power
        
        # Update user stats
        user.coins += coins_earned
        user.energy -= taps
        user.total_earned += coins_earned
        user.total_taps += taps
        user.last_activity = datetime.utcnow().isoformat()
        
        user.save()
        
        return jsonify({
            'success': True,
            'coins_earned': coins_earned,
            'user': user.to_dict()
        })
    
    except Exception as e:
        print(f"Tap error: {e}")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/update_upi', methods=['POST'])
def update_upi():
    """Update user UPI ID"""
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        upi_id = data.get('upi_id')
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.upi_id = upi_id
        user.save()
        
        return jsonify({
            'success': True,
            'message': 'UPI ID updated successfully'
        })
    
    except Exception as e:
        print(f"UPI update error: {e}")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/transactions/<int:telegram_id>', methods=['GET'])
def get_user_transactions(telegram_id):
    """Get user transaction history"""
    user = User.get_by_telegram_id(telegram_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # For now, return empty transactions since we haven't implemented transaction tracking in Supabase yet
    # This can be enhanced later with a separate transactions table
    return jsonify([])

@user_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top users leaderboard"""
    try:
        # Get all users and sort by total_earned
        all_users = User.get_all_users()
        top_users = sorted(all_users, key=lambda x: x.get('total_earned', 0), reverse=True)[:10]
        
        return jsonify([{
            'rank': idx + 1,
            'name': user.get('first_name') or user.get('username') or f'User{user.get("telegram_id")}',
            'total_earned': user.get('total_earned', 0)
        } for idx, user in enumerate(top_users)])
    
    except Exception as e:
        print(f"Leaderboard error: {e}")
        return jsonify([])

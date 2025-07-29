from flask import Blueprint, request, jsonify
import logging
from src.models.user import User

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/tap', methods=['POST', 'OPTIONS'])
def tap():
    """Handle tap action with real-time updates"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'error': 'telegram_id is required'}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Perform tap with real-time updates
        if user.tap():
            # Return real-time data
            user_data = user.get_real_time_data()
            
            return jsonify({
                'success': True,
                'coins': user.coins,
                'energy': user.energy,
                'tap_power': user.tap_power,
                'total_taps': user.total_taps,
                'user': user_data  # Full user data for sync
            })
        else:
            # Get current data even if tap failed
            user_data = user.get_real_time_data()
            
            return jsonify({
                'success': False,
                'error': 'Tap failed - insufficient energy or save error',
                'coins': user.coins,
                'energy': user.energy,
                'user': user_data
            }), 400
            
    except Exception as e:
        logger.error(f"Error in tap: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/users/telegram/<int:telegram_id>', methods=['GET'])
def get_user_by_telegram_id(telegram_id):
    """Get user by telegram ID with real-time data"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if user:
            # Return real-time data
            user_data = user.get_real_time_data()
            return jsonify(user_data)
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting user {telegram_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/user/energy/<int:telegram_id>', methods=['GET'])
def get_user_energy(telegram_id):
    """Get user energy with real-time regeneration"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if user:
            # Energy is already updated by get_by_telegram_id
            return jsonify({
                'energy': user.energy,
                'max_energy': user.max_energy,
                'last_update': user.last_energy_update,
                'regen_rate': user.energy_regen_rate
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting user energy {telegram_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/user/coins/<int:telegram_id>', methods=['GET'])
def get_user_coins(telegram_id):
    """Get user coins with real-time data"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if user:
            return jsonify({
                'coins': user.coins,
                'tap_power': user.tap_power,
                'total_taps': user.total_taps
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting user coins {telegram_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/user/stats/<int:telegram_id>', methods=['GET'])
def get_user_stats(telegram_id):
    """Get comprehensive user stats with real-time data"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if user:
            user_data = user.get_real_time_data()
            
            # Add calculated stats
            stats = {
                'basic': {
                    'coins': user.coins,
                    'energy': user.energy,
                    'max_energy': user.max_energy,
                    'tap_power': user.tap_power
                },
                'progress': {
                    'total_taps': user.total_taps,
                    'referral_count': user.referral_count,
                    'referral_earnings': user.referral_earnings
                },
                'rates': {
                    'energy_regen_rate': user.energy_regen_rate,
                    'coins_per_tap': user.tap_power
                },
                'user': user_data
            }
            
            return jsonify(stats)
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting user stats {telegram_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


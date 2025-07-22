from flask import Blueprint, request, jsonify
import logging
from src.models.user import User

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/tap', methods=['POST', 'OPTIONS'])
def tap():
    """Handle tap action"""
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
        
        # Update energy before tap
        user.update_energy()
        
        if not user.can_tap():
            return jsonify({'error': 'Not enough energy'}), 400
        
        if user.tap():
            return jsonify({
                'success': True,
                'coins': user.coins,
                'energy': user.energy,
                'tap_power': user.tap_power
            })
        else:
            return jsonify({'error': 'Tap failed'}), 500
            
    except Exception as e:
        logger.error(f"Error in tap: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/users/telegram/<int:telegram_id>', methods=['GET'])
def get_user_by_telegram_id(telegram_id):
    """Get user by telegram ID"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if user:
            # Update energy before returning
            user.update_energy()
            user.save()  # Save updated energy
            return jsonify(user.to_dict())
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting user {telegram_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/user/energy/<int:telegram_id>', methods=['GET'])
def get_user_energy(telegram_id):
    """Get user energy (with regeneration)"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if user:
            user.update_energy()
            user.save()  # Save updated energy
            return jsonify({
                'energy': user.energy,
                'max_energy': user.max_energy,
                'last_update': user.last_energy_update
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting user energy {telegram_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


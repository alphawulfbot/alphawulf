from flask import Blueprint, request, jsonify
from src.models.user import User
from datetime import datetime

upgrades_bp = Blueprint('upgrades', __name__)

@upgrades_bp.route('/upgrade', methods=['POST'])
def upgrade_item():
    """Handle user upgrades"""
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        upgrade_type = data.get('upgrade_type')
        
        if not telegram_id or not upgrade_type:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Calculate upgrade cost based on current level
        base_costs = {
            'tap_power': 1000,
            'max_energy': 2000,
            'energy_regen_rate': 1500
        }
        
        # Map frontend upgrade_type to backend field name
        field_mapping = {
            'tap_power': 'tap_power',
            'max_energy': 'max_energy',
            'energy_regen': 'energy_regen_rate'
        }
        
        backend_field = field_mapping.get(upgrade_type)
        if not backend_field:
            return jsonify({'error': 'Invalid upgrade type'}), 400
        
        current_level = getattr(user, backend_field, 1)
        upgrade_cost = int(base_costs.get(backend_field, 1000) * (1.5 ** (current_level - 1)))
        
        # Check if user has enough coins
        if user.coins < upgrade_cost:
            return jsonify({'error': 'Not enough coins'}), 400
        
        # Apply upgrade
        user.coins -= upgrade_cost
        setattr(user, backend_field, current_level + 1)
        user.last_activity = datetime.utcnow().isoformat()
        user.save()
        
        return jsonify({
            'success': True,
            'message': f'{upgrade_type} upgraded successfully',
            'user': user.to_dict()
        })
    
    except Exception as e:
        print(f"Upgrade error: {e}")
        return jsonify({'error': str(e)}), 500


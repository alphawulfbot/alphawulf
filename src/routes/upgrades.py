from flask import Blueprint, request, jsonify
import logging
from src.models.user import User

logger = logging.getLogger(__name__)

upgrades_bp = Blueprint('upgrades', __name__)

# Upgrade configurations
UPGRADE_CONFIGS = {
    'tap_power': {
        'name': 'Tap Power',
        'description': 'Increase coins per tap',
        'base_cost': 100,
        'cost_multiplier': 1.5,
        'max_level': 50
    },
    'energy_capacity': {
        'name': 'Energy Capacity',
        'description': 'Increase maximum energy',
        'base_cost': 200,
        'cost_multiplier': 1.3,
        'max_level': 30
    },
    'energy_regen': {
        'name': 'Energy Regeneration',
        'description': 'Faster energy regeneration',
        'base_cost': 500,
        'cost_multiplier': 2.0,
        'max_level': 20
    }
}

def calculate_upgrade_cost(upgrade_type, current_level):
    """Calculate cost for next upgrade level"""
    if upgrade_type not in UPGRADE_CONFIGS:
        return None
    
    config = UPGRADE_CONFIGS[upgrade_type]
    if current_level >= config['max_level']:
        return None
    
    cost = int(config['base_cost'] * (config['cost_multiplier'] ** current_level))
    return cost

@upgrades_bp.route('/api/upgrades/info/<int:telegram_id>', methods=['GET'])
def get_upgrades_info(telegram_id):
    """Get upgrade information for user with real-time data"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get real-time user data
        user_data = user.get_real_time_data()
        
        # Calculate current levels (based on user stats)
        tap_power_level = user.tap_power - 1  # Level 0 = 1 tap power
        energy_capacity_level = (user.max_energy - 100) // 10  # Level 0 = 100 energy, +10 per level
        energy_regen_level = user.energy_regen_rate - 1  # Level 0 = 1 regen rate
        
        upgrades_info = {
            'user': user_data,
            'available_coins': user.coins,
            'upgrades': {
                'tap_power': {
                    'current_level': tap_power_level,
                    'current_value': user.tap_power,
                    'next_value': user.tap_power + 1,
                    'cost': calculate_upgrade_cost('tap_power', tap_power_level),
                    'can_upgrade': user.coins >= calculate_upgrade_cost('tap_power', tap_power_level) if calculate_upgrade_cost('tap_power', tap_power_level) else False,
                    'max_level': UPGRADE_CONFIGS['tap_power']['max_level'],
                    'is_max': tap_power_level >= UPGRADE_CONFIGS['tap_power']['max_level'],
                    **UPGRADE_CONFIGS['tap_power']
                },
                'energy_capacity': {
                    'current_level': energy_capacity_level,
                    'current_value': user.max_energy,
                    'next_value': user.max_energy + 10,
                    'cost': calculate_upgrade_cost('energy_capacity', energy_capacity_level),
                    'can_upgrade': user.coins >= calculate_upgrade_cost('energy_capacity', energy_capacity_level) if calculate_upgrade_cost('energy_capacity', energy_capacity_level) else False,
                    'max_level': UPGRADE_CONFIGS['energy_capacity']['max_level'],
                    'is_max': energy_capacity_level >= UPGRADE_CONFIGS['energy_capacity']['max_level'],
                    **UPGRADE_CONFIGS['energy_capacity']
                },
                'energy_regen': {
                    'current_level': energy_regen_level,
                    'current_value': user.energy_regen_rate,
                    'next_value': user.energy_regen_rate + 1,
                    'cost': calculate_upgrade_cost('energy_regen', energy_regen_level),
                    'can_upgrade': user.coins >= calculate_upgrade_cost('energy_regen', energy_regen_level) if calculate_upgrade_cost('energy_regen', energy_regen_level) else False,
                    'max_level': UPGRADE_CONFIGS['energy_regen']['max_level'],
                    'is_max': energy_regen_level >= UPGRADE_CONFIGS['energy_regen']['max_level'],
                    **UPGRADE_CONFIGS['energy_regen']
                }
            }
        }
        
        return jsonify(upgrades_info)
        
    except Exception as e:
        logger.error(f"Error getting upgrades info for {telegram_id}: {str(e)}")
        return jsonify({'error': 'Failed to get upgrades info'}), 500

@upgrades_bp.route('/api/upgrades/purchase', methods=['POST'])
def purchase_upgrade():
    """Purchase upgrade with real-time validation and sync"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        upgrade_type = data.get('upgrade_type')
        
        if not telegram_id or not upgrade_type:
            return jsonify({'error': 'telegram_id and upgrade_type are required'}), 400
        
        if upgrade_type not in UPGRADE_CONFIGS:
            return jsonify({'error': 'Invalid upgrade type'}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Calculate current level and cost
        if upgrade_type == 'tap_power':
            current_level = user.tap_power - 1
            cost = calculate_upgrade_cost('tap_power', current_level)
            
            if not cost:
                return jsonify({'error': 'Upgrade at maximum level'}), 400
            
            if user.coins < cost:
                return jsonify({'error': 'Insufficient coins'}), 400
            
            # Perform upgrade
            old_coins = user.coins
            old_tap_power = user.tap_power
            
            if user.upgrade_tap_power(cost):
                logger.info(f"User {telegram_id} upgraded tap power: {old_tap_power} -> {user.tap_power}, cost: {cost}")
                
                return jsonify({
                    'success': True,
                    'upgrade_type': upgrade_type,
                    'old_level': current_level,
                    'new_level': current_level + 1,
                    'old_value': old_tap_power,
                    'new_value': user.tap_power,
                    'cost': cost,
                    'remaining_coins': user.coins,
                    'user': user.get_real_time_data()
                })
            else:
                return jsonify({'error': 'Failed to purchase upgrade'}), 500
                
        elif upgrade_type == 'energy_capacity':
            current_level = (user.max_energy - 100) // 10
            cost = calculate_upgrade_cost('energy_capacity', current_level)
            
            if not cost:
                return jsonify({'error': 'Upgrade at maximum level'}), 400
            
            if user.coins < cost:
                return jsonify({'error': 'Insufficient coins'}), 400
            
            # Perform upgrade
            old_coins = user.coins
            old_max_energy = user.max_energy
            
            if user.subtract_coins(cost):
                user.max_energy += 10
                user.energy = min(user.energy + 10, user.max_energy)  # Also increase current energy
                
                if user.save():
                    logger.info(f"User {telegram_id} upgraded energy capacity: {old_max_energy} -> {user.max_energy}, cost: {cost}")
                    
                    return jsonify({
                        'success': True,
                        'upgrade_type': upgrade_type,
                        'old_level': current_level,
                        'new_level': current_level + 1,
                        'old_value': old_max_energy,
                        'new_value': user.max_energy,
                        'cost': cost,
                        'remaining_coins': user.coins,
                        'user': user.get_real_time_data()
                    })
                else:
                    # Rollback
                    user.add_coins(cost)
                    user.max_energy = old_max_energy
                    return jsonify({'error': 'Failed to save upgrade'}), 500
            else:
                return jsonify({'error': 'Failed to deduct coins'}), 500
                
        elif upgrade_type == 'energy_regen':
            current_level = user.energy_regen_rate - 1
            cost = calculate_upgrade_cost('energy_regen', current_level)
            
            if not cost:
                return jsonify({'error': 'Upgrade at maximum level'}), 400
            
            if user.coins < cost:
                return jsonify({'error': 'Insufficient coins'}), 400
            
            # Perform upgrade
            old_coins = user.coins
            old_regen_rate = user.energy_regen_rate
            
            if user.subtract_coins(cost):
                user.energy_regen_rate += 1
                
                if user.save():
                    logger.info(f"User {telegram_id} upgraded energy regen: {old_regen_rate} -> {user.energy_regen_rate}, cost: {cost}")
                    
                    return jsonify({
                        'success': True,
                        'upgrade_type': upgrade_type,
                        'old_level': current_level,
                        'new_level': current_level + 1,
                        'old_value': old_regen_rate,
                        'new_value': user.energy_regen_rate,
                        'cost': cost,
                        'remaining_coins': user.coins,
                        'user': user.get_real_time_data()
                    })
                else:
                    # Rollback
                    user.add_coins(cost)
                    user.energy_regen_rate = old_regen_rate
                    return jsonify({'error': 'Failed to save upgrade'}), 500
            else:
                return jsonify({'error': 'Failed to deduct coins'}), 500
        
        return jsonify({'error': 'Unknown upgrade type'}), 400
        
    except Exception as e:
        logger.error(f"Error purchasing upgrade: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@upgrades_bp.route('/api/upgrades/preview/<upgrade_type>/<int:telegram_id>', methods=['GET'])
def preview_upgrade(upgrade_type, telegram_id):
    """Preview upgrade cost and benefits"""
    try:
        if upgrade_type not in UPGRADE_CONFIGS:
            return jsonify({'error': 'Invalid upgrade type'}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Calculate current level and preview
        if upgrade_type == 'tap_power':
            current_level = user.tap_power - 1
            current_value = user.tap_power
            next_value = user.tap_power + 1
        elif upgrade_type == 'energy_capacity':
            current_level = (user.max_energy - 100) // 10
            current_value = user.max_energy
            next_value = user.max_energy + 10
        elif upgrade_type == 'energy_regen':
            current_level = user.energy_regen_rate - 1
            current_value = user.energy_regen_rate
            next_value = user.energy_regen_rate + 1
        
        cost = calculate_upgrade_cost(upgrade_type, current_level)
        
        preview = {
            'upgrade_type': upgrade_type,
            'current_level': current_level,
            'current_value': current_value,
            'next_level': current_level + 1 if cost else current_level,
            'next_value': next_value if cost else current_value,
            'cost': cost,
            'can_afford': user.coins >= cost if cost else False,
            'is_max_level': cost is None,
            'user_coins': user.coins,
            'config': UPGRADE_CONFIGS[upgrade_type]
        }
        
        return jsonify(preview)
        
    except Exception as e:
        logger.error(f"Error previewing upgrade {upgrade_type} for {telegram_id}: {str(e)}")
        return jsonify({'error': 'Failed to preview upgrade'}), 500


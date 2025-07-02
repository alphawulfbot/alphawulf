from flask import Blueprint, request, jsonify
from src.models.user import db, User, Transaction
from datetime import datetime

upgrades_bp = Blueprint('upgrades', __name__)

@upgrades_bp.route('/user_upgrades/<int:telegram_id>', methods=['GET'])
def get_user_upgrades(telegram_id):
    """Get user's current upgrade levels"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    upgrades = {
        'tap_power': user.tap_power - 1,  # Base is 1, so level 0 means no upgrades
        'energy_capacity': max(0, (user.max_energy - 100) // 10),  # Base is 100, +10 per level
        'energy_regen': user.energy_regen_rate - 1  # Base is 1, so level 0 means no upgrades
    }
    
    return jsonify({
        'user_id': telegram_id,
        'upgrades': upgrades,
        'current_stats': {
            'tap_power': user.tap_power,
            'max_energy': user.max_energy,
            'energy_regen_rate': user.energy_regen_rate
        }
    })

@upgrades_bp.route('/purchase_upgrade', methods=['POST'])
def purchase_upgrade():
    """Purchase an upgrade for the user"""
    data = request.json
    telegram_id = data.get('telegram_id')
    upgrade_type = data.get('upgrade_type')
    
    if not telegram_id or not upgrade_type:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate upgrade type
    valid_upgrades = ['tap_power', 'energy_capacity', 'energy_regen']
    if upgrade_type not in valid_upgrades:
        return jsonify({'error': 'Invalid upgrade type'}), 400
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Calculate current level and cost
    if upgrade_type == 'tap_power':
        current_level = user.tap_power - 1
        base_cost = 100
        multiplier = 1.5
        max_level = 20
    elif upgrade_type == 'energy_capacity':
        current_level = max(0, (user.max_energy - 100) // 10)
        base_cost = 200
        multiplier = 1.6
        max_level = 20
    elif upgrade_type == 'energy_regen':
        current_level = user.energy_regen_rate - 1
        base_cost = 300
        multiplier = 1.7
        max_level = 20
    
    # Check if already at max level
    if current_level >= max_level:
        return jsonify({'error': 'Upgrade already at maximum level'}), 400
    
    # Calculate upgrade cost
    upgrade_cost = int(base_cost * (multiplier ** current_level))
    
    # Check if user has enough coins
    if user.coins < upgrade_cost:
        return jsonify({'error': 'Insufficient coins'}), 400
    
    try:
        # Deduct coins
        user.coins -= upgrade_cost
        
        # Apply upgrade
        new_level = current_level + 1
        if upgrade_type == 'tap_power':
            user.tap_power += 1
            upgrade_name = 'Wolf Claws'
        elif upgrade_type == 'energy_capacity':
            user.max_energy += 10
            upgrade_name = 'Wolf Stamina'
        elif upgrade_type == 'energy_regen':
            user.energy_regen_rate += 1
            upgrade_name = 'Wolf Recovery'
        
        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            transaction_type='upgrade',
            amount=-upgrade_cost,
            description=f'Purchased {upgrade_name} upgrade (Level {new_level})'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'upgrade_type': upgrade_type,
            'upgrade_name': upgrade_name,
            'new_level': new_level,
            'cost': upgrade_cost,
            'new_balance': user.coins,
            'new_stats': {
                'tap_power': user.tap_power,
                'max_energy': user.max_energy,
                'energy_regen_rate': user.energy_regen_rate
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to purchase upgrade'}), 500

@upgrades_bp.route('/upgrade_costs/<int:telegram_id>', methods=['GET'])
def get_upgrade_costs(telegram_id):
    """Get the costs for all available upgrades"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    upgrades_info = []
    
    # Tap Power upgrade
    tap_level = user.tap_power - 1
    tap_cost = int(100 * (1.5 ** tap_level)) if tap_level < 20 else None
    upgrades_info.append({
        'type': 'tap_power',
        'name': 'Wolf Claws',
        'current_level': tap_level,
        'next_cost': tap_cost,
        'max_level': tap_level >= 20
    })
    
    # Energy Capacity upgrade
    energy_level = max(0, (user.max_energy - 100) // 10)
    energy_cost = int(200 * (1.6 ** energy_level)) if energy_level < 20 else None
    upgrades_info.append({
        'type': 'energy_capacity',
        'name': 'Wolf Stamina',
        'current_level': energy_level,
        'next_cost': energy_cost,
        'max_level': energy_level >= 20
    })
    
    # Energy Regen upgrade
    regen_level = user.energy_regen_rate - 1
    regen_cost = int(300 * (1.7 ** regen_level)) if regen_level < 20 else None
    upgrades_info.append({
        'type': 'energy_regen',
        'name': 'Wolf Recovery',
        'current_level': regen_level,
        'next_cost': regen_cost,
        'max_level': regen_level >= 20
    })
    
    return jsonify({
        'user_id': telegram_id,
        'upgrades': upgrades_info,
        'user_coins': user.coins
    })


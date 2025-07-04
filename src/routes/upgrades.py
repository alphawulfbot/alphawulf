from flask import Blueprint, request, jsonify
from src.models.user import User
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upgrades_bp = Blueprint('upgrades', __name__)

@upgrades_bp.route('/api/upgrade', methods=['POST'])
def upgrade():
    """
    Endpoint to handle user upgrades
    """
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        upgrade_type = data.get('upgrade_type')
        
        logger.info(f"Upgrade request: telegram_id={telegram_id}, upgrade_type={upgrade_type}")
        
        if not telegram_id or not upgrade_type:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            # Create user if not exists
            user = User(
                telegram_id=telegram_id,
                username="user_" + str(telegram_id),
                first_name="User",
                coins=0,
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=None
            )
            user.save()
            logger.info(f"Created new user for telegram_id={telegram_id}")
            return jsonify({'error': 'User created. Please try again.'}), 400
        
        # Calculate upgrade cost based on current level
        current_level = 0
        if upgrade_type == 'tap_power':
            current_level = user.tap_power
            base_cost = 100
            multiplier = 1.5
        elif upgrade_type == 'energy_capacity':
            current_level = (user.max_energy - 100) // 10
            base_cost = 200
            multiplier = 1.6
        elif upgrade_type == 'energy_regen':
            current_level = user.energy_regen_rate
            base_cost = 300
            multiplier = 1.7
        else:
            return jsonify({'error': 'Invalid upgrade type'}), 400
        
        # Calculate cost
        cost = int(base_cost * (multiplier ** current_level))
        
        logger.info(f"Upgrade cost: {cost} coins for {upgrade_type} (current level: {current_level})")
        
        # Check if user has enough coins
        if user.coins < cost:
            return jsonify({'error': 'Not enough coins'}), 400
        
        # Apply upgrade
        user.coins -= cost
        
        if upgrade_type == 'tap_power':
            user.tap_power += 1
            logger.info(f"Upgraded tap_power to {user.tap_power}")
        elif upgrade_type == 'energy_capacity':
            user.max_energy += 10
            # Also increase current energy by the same amount
            user.energy = min(user.energy + 10, user.max_energy)
            logger.info(f"Upgraded max_energy to {user.max_energy}")
        elif upgrade_type == 'energy_regen':
            user.energy_regen_rate += 1
            logger.info(f"Upgraded energy_regen_rate to {user.energy_regen_rate}")
        
        # Save user
        user.save()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error in upgrade: {str(e)}")
        return jsonify({'error': str(e)}), 500


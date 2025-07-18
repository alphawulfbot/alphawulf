from flask import Blueprint, request, jsonify
from src.models.user import User
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upgrades_bp = Blueprint('upgrades', __name__)

@upgrades_bp.route('/api/upgrade', methods=['POST'])
def upgrade():
    try:
        # Get upgrade data from request
        data = request.json
        telegram_id = data.get('telegram_id')
        upgrade_type = data.get('upgrade_type')
        
        if not telegram_id or not upgrade_type:
            return jsonify({"error": "Telegram ID and upgrade type are required"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Calculate upgrade cost and effect
        current_level = 0
        cost = 0
        
        if upgrade_type == 'tap_power':
            current_level = user.tap_power
            cost = 100 * (current_level + 1)
        elif upgrade_type == 'max_energy':
            current_level = user.max_energy // 100
            cost = 200 * (current_level + 1)
        elif upgrade_type == 'energy_regen_rate':
            current_level = user.energy_regen_rate
            cost = 300 * (current_level + 1)
        else:
            return jsonify({"error": "Invalid upgrade type"}), 400
        
        # Check if user has enough coins
        if user.coins < cost:
            return jsonify({
                "success": False,
                "message": "Not enough coins",
                "coins": user.coins,
                "cost": cost
            })
        
        # Apply upgrade
        user.coins -= cost
        
        if upgrade_type == 'tap_power':
            user.tap_power += 1
        elif upgrade_type == 'max_energy':
            user.max_energy += 100
        elif upgrade_type == 'energy_regen_rate':
            user.energy_regen_rate += 1
        
        # Save updated user
        user.save()
        
        # Return updated user data
        return jsonify({
            "success": True,
            "message": "Upgrade successful",
            "coins": user.coins,
            "energy": user.energy,
            "max_energy": user.max_energy,
            "tap_power": user.tap_power,
            "energy_regen_rate": user.energy_regen_rate
        })
    except Exception as e:
        logger.error(f"Error in upgrade: {str(e)}")
        return jsonify({"error": str(e)}), 500


from flask import Blueprint, request, jsonify
from src.models.user import User
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upgrades_bp = Blueprint("upgrades", __name__)

@upgrades_bp.route("/api/upgrade", methods=["POST"])
def upgrade():
    try:
        # Get upgrade data from request
        data = request.json
        telegram_id = str(data.get("telegram_id", "")).strip()
        upgrade_type = data.get("upgrade_type")
        
        logger.info(f"Upgrade request for user {telegram_id}: type={upgrade_type}")
        
        if not telegram_id or not upgrade_type:
            return jsonify({"error": "Telegram ID and upgrade type are required"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Apply upgrade using the User model's method
        if user.apply_upgrade(upgrade_type):
            user.save()
            logger.info(f"Upgrade successful for user {telegram_id}, type: {upgrade_type}")
            return jsonify({
                "success": True,
                "message": "Upgrade successful",
                "coins": user.coins,
                "energy": user.energy,
                "max_energy": user.max_energy,
                "tap_power": user.tap_power,
                "energy_regen_rate": user.energy_regen_rate
            })
        else:
            logger.warning(f"Upgrade failed for user {telegram_id}, type: {upgrade_type}")
            return jsonify({"success": False, "message": "Upgrade failed or insufficient coins"}), 400
            
    except Exception as e:
        logger.error(f"Error in upgrade for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500



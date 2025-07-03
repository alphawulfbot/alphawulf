from flask import Blueprint, request, jsonify
from src.models.user import User, Upgrade, Transaction
from datetime import datetime

upgrades_bp = Blueprint("upgrades", __name__)

# Hardcoded upgrade definitions (should ideally come from a config or DB)
UPGRADES = {
    "tap_power": {"name": "Tap Power", "base_cost": 100, "cost_multiplier": 1.5, "max_level": 50},
    "energy_capacity": {"name": "Energy Capacity", "base_cost": 200, "cost_multiplier": 1.6, "max_level": 30},
    "energy_regen": {"name": "Energy Regeneration", "base_cost": 150, "cost_multiplier": 1.4, "max_level": 40}
}

def calculate_upgrade_cost(upgrade_type, current_level):
    """Calculate the cost of the next upgrade level"""
    upgrade_info = UPGRADES.get(upgrade_type)
    if not upgrade_info:
        return None
    
    if current_level >= upgrade_info["max_level"]:
        return None # Max level reached
    
    cost = upgrade_info["base_cost"] * (upgrade_info["cost_multiplier"] ** current_level)
    return int(cost)

@upgrades_bp.route("/upgrades", methods=["GET"])
def get_upgrades():
    """Get all available upgrades"""
    try:
        upgrades_list = []
        for key, info in UPGRADES.items():
            upgrades_list.append({
                "type": key,
                "name": info["name"],
                "base_cost": info["base_cost"],
                "cost_multiplier": info["cost_multiplier"],
                "max_level": info["max_level"]
            })
        return jsonify(upgrades_list)
    except Exception as e:
        print(f"Error getting upgrades: {e}")
        return jsonify({"error": str(e)}), 500

@upgrades_bp.route("/upgrades/purchase", methods=["POST"])
def purchase_upgrade():
    """Purchase an upgrade"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        upgrade_type = data.get("upgrade_type")
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get current level
        if upgrade_type == "tap_power":
            current_level = user.tap_power - 1
        elif upgrade_type == "energy_capacity":
            current_level = (user.max_energy - 100) // 10
        elif upgrade_type == "energy_regen":
            current_level = user.energy_regen_rate - 1
        else:
            return jsonify({"error": "Invalid upgrade type"}), 400
        
        # Calculate cost
        cost = calculate_upgrade_cost(upgrade_type, current_level)
        if cost is None:
            return jsonify({"error": "Upgrade not available or max level reached"}), 400
        
        # Check if user has enough coins
        if user.coins < cost:
            return jsonify({"error": "Insufficient coins"}), 400
        
        # Apply upgrade
        user.coins -= cost
        
        if upgrade_type == "tap_power":
            user.tap_power += 1
        elif upgrade_type == "energy_capacity":
            user.max_energy += 10
        elif upgrade_type == "energy_regen":
            user.energy_regen_rate += 1
        
        user.save()
        
        # Log transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type="upgrade_purchase",
            amount=-cost, # Negative amount for purchase
            description=f"Purchased {UPGRADES[upgrade_type]["name"]} upgrade"
        )
        transaction.save()
        
        return jsonify({
            "success": True,
            "message": f"{UPGRADES[upgrade_type]["name"]} upgraded successfully",
            "cost": cost,
            "user": user.to_dict()
        })
    
    except Exception as e:
        print(f"Purchase upgrade error: {e}")
        return jsonify({"error": str(e)}), 500

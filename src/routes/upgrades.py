from flask import Blueprint, request, jsonify
import logging
from src.models.user import User

logger = logging.getLogger(__name__)

upgrades_bp = Blueprint('upgrades', __name__)

class UpgradeSystem:
    """Upgrade system for the game"""
    
    @staticmethod
    def get_upgrade_costs():
        """Get upgrade costs and information"""
        return {
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
                'base_cost': 300,
                'cost_multiplier': 1.4,
                'max_level': 20
            }
        }
    
    @staticmethod
    def calculate_upgrade_cost(upgrade_type, current_level):
        """Calculate cost for next upgrade level"""
        costs = UpgradeSystem.get_upgrade_costs()
        
        if upgrade_type not in costs:
            return None
        
        upgrade_info = costs[upgrade_type]
        base_cost = upgrade_info['base_cost']
        multiplier = upgrade_info['cost_multiplier']
        
        # Cost increases exponentially
        cost = int(base_cost * (multiplier ** current_level))
        return cost
    
    @staticmethod
    def can_upgrade(upgrade_type, current_level):
        """Check if upgrade is possible"""
        costs = UpgradeSystem.get_upgrade_costs()
        
        if upgrade_type not in costs:
            return False
        
        max_level = costs[upgrade_type]['max_level']
        return current_level < max_level

@upgrades_bp.route('/api/upgrades/info', methods=['GET'])
def get_upgrades_info():
    """Get upgrade information and costs"""
    try:
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id:
            return jsonify({
                "error": "telegram_id is required",
                "success": False
            }), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                "error": "User not found",
                "success": False
            }), 404
        
        # Get current levels (for now, we'll use tap_power as the main upgrade)
        current_tap_level = user.tap_power - 1  # Level 0 = tap_power 1
        
        # Calculate upgrade costs and info
        upgrades_info = {}
        upgrade_costs = UpgradeSystem.get_upgrade_costs()
        
        for upgrade_type, info in upgrade_costs.items():
            if upgrade_type == 'tap_power':
                current_level = current_tap_level
            else:
                current_level = 0  # Other upgrades not implemented yet
            
            can_upgrade = UpgradeSystem.can_upgrade(upgrade_type, current_level)
            next_cost = UpgradeSystem.calculate_upgrade_cost(upgrade_type, current_level) if can_upgrade else None
            
            upgrades_info[upgrade_type] = {
                'name': info['name'],
                'description': info['description'],
                'current_level': current_level,
                'max_level': info['max_level'],
                'can_upgrade': can_upgrade,
                'next_cost': next_cost,
                'affordable': user.coins >= next_cost if next_cost else False
            }
        
        response = jsonify({
            "success": True,
            "user": user.to_dict(),
            "upgrades": upgrades_info
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Get upgrades info error: {str(e)}")
        return jsonify({
            "error": "Failed to get upgrades info",
            "message": str(e),
            "success": False
        }), 500

@upgrades_bp.route('/api/upgrades/purchase', methods=['POST'])
def purchase_upgrade():
    """Purchase an upgrade"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        upgrade_type = data.get('upgrade_type')
        
        if not telegram_id or not upgrade_type:
            return jsonify({
                "error": "telegram_id and upgrade_type are required",
                "success": False
            }), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                "error": "User not found",
                "success": False
            }), 404
        
        # Get current level
        if upgrade_type == 'tap_power':
            current_level = user.tap_power - 1
        else:
            return jsonify({
                "error": "Upgrade type not implemented yet",
                "success": False
            }), 400
        
        # Check if upgrade is possible
        if not UpgradeSystem.can_upgrade(upgrade_type, current_level):
            return jsonify({
                "error": "Maximum level reached",
                "success": False
            }), 400
        
        # Calculate cost
        cost = UpgradeSystem.calculate_upgrade_cost(upgrade_type, current_level)
        
        if user.coins < cost:
            return jsonify({
                "error": "Insufficient coins",
                "success": False
            }), 400
        
        # Perform upgrade
        if upgrade_type == 'tap_power':
            if user.upgrade_tap_power(cost):
                response = jsonify({
                    "success": True,
                    "user": user.to_dict(),
                    "message": f"Tap power upgraded to level {user.tap_power}",
                    "cost": cost
                })
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 200
            else:
                return jsonify({
                    "error": "Failed to upgrade",
                    "success": False
                }), 500
        
        return jsonify({
            "error": "Upgrade type not implemented",
            "success": False
        }), 400
        
    except Exception as e:
        logger.error(f"Purchase upgrade error: {str(e)}")
        return jsonify({
            "error": "Failed to purchase upgrade",
            "message": str(e),
            "success": False
        }), 500

@upgrades_bp.route('/api/upgrades/list', methods=['GET'])
def list_available_upgrades():
    """List all available upgrades"""
    try:
        upgrade_costs = UpgradeSystem.get_upgrade_costs()
        
        upgrades_list = []
        for upgrade_type, info in upgrade_costs.items():
            upgrades_list.append({
                'type': upgrade_type,
                'name': info['name'],
                'description': info['description'],
                'base_cost': info['base_cost'],
                'cost_multiplier': info['cost_multiplier'],
                'max_level': info['max_level']
            })
        
        response = jsonify({
            "success": True,
            "upgrades": upgrades_list
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"List upgrades error: {str(e)}")
        return jsonify({
            "error": "Failed to list upgrades",
            "message": str(e),
            "success": False
        }), 500


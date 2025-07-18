from flask import Blueprint, request, jsonify
from src.models.user import User
import logging
import time
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/user/<telegram_id>', methods=['GET'])
def get_user(telegram_id):
    try:
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        # If user doesn't exist, create a new one
        if not user:
            # Extract user data from request
            data = request.args
            username = data.get('username')
            first_name = data.get('first_name')
            referred_by = data.get('referred_by')
            
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                coins=0,
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=int(time.time()),
                referred_by=referred_by,
                referral_count=0,
                referral_earnings=0
            )
            
            # Save user to database
            user.save()
            
            # If user was referred, update referrer's stats
            if referred_by and referred_by != telegram_id:
                referrer = User.get_by_telegram_id(referred_by)
                if referrer:
                    referrer.referral_count += 1
                    referrer.referral_earnings += 100  # Bonus for referring a user
                    referrer.coins += 100
                    referrer.save()
        else:
            # Update energy based on regeneration rate
            current_time = int(time.time())
            if user.last_energy_update:
                time_diff = current_time - user.last_energy_update
                energy_regen = (time_diff / 60) * user.energy_regen_rate  # Energy regenerates per minute
                
                user.energy = min(user.max_energy, user.energy + energy_regen)
                user.last_energy_update = current_time
                
                # Save updated energy
                user.save()
        
        # Return user data
        return jsonify({
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "coins": user.coins,
            "energy": user.energy,
            "max_energy": user.max_energy,
            "tap_power": user.tap_power,
            "energy_regen_rate": user.energy_regen_rate,
            "referral_count": user.referral_count,
            "referral_earnings": user.referral_earnings,
            "upi_id": user.upi_id
        })
    except Exception as e:
        logger.error(f"Error in get_user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route('/api/tap', methods=['POST'])
def tap():
    try:
        # Get user data from request
        data = request.json
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({"error": "Telegram ID is required"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update energy based on regeneration rate
        current_time = int(time.time())
        if user.last_energy_update:
            time_diff = current_time - user.last_energy_update
            energy_regen = (time_diff / 60) * user.energy_regen_rate  # Energy regenerates per minute
            
            user.energy = min(user.max_energy, user.energy + energy_regen)
        
        # Check if user has enough energy
        if user.energy < 1:
            return jsonify({
                "success": False,
                "message": "Not enough energy",
                "coins": user.coins,
                "energy": user.energy,
                "max_energy": user.max_energy,
                "tap_power": user.tap_power,
                "energy_regen_rate": user.energy_regen_rate
            })
        
        # Deduct energy and add coins
        user.energy -= 1
        user.coins += user.tap_power
        user.last_energy_update = current_time
        
        # Save updated user
        user.save()
        
        # Return updated user data
        return jsonify({
            "success": True,
            "message": "Tap successful",
            "coins": user.coins,
            "energy": user.energy,
            "max_energy": user.max_energy,
            "tap_power": user.tap_power,
            "energy_regen_rate": user.energy_regen_rate
        })
    except Exception as e:
        logger.error(f"Error in tap: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route('/api/update_upi', methods=['POST'])
def update_upi():
    try:
        # Get user data from request
        data = request.json
        telegram_id = data.get('telegram_id')
        upi_id = data.get('upi_id')
        
        if not telegram_id or not upi_id:
            return jsonify({"error": "Telegram ID and UPI ID are required"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update UPI ID
        user.upi_id = upi_id
        
        # Save updated user
        user.save()
        
        # Return success message
        return jsonify({
            "success": True,
            "message": "UPI ID updated successfully"
        })
    except Exception as e:
        logger.error(f"Error in update_upi: {str(e)}")
        return jsonify({"error": str(e)}), 500


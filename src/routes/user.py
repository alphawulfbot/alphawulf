from flask import Blueprint, request, jsonify
from src.models.user import User
from src.config.database import supabase
import logging
import time
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__)

@user_bp.route("/api/user/<telegram_id>", methods=["GET"])
def get_user(telegram_id):
    try:
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        # If user doesn't exist, create a new one with 2500 coins bonus
        if not user:
            # Extract user data from request
            data = request.args
            username = data.get("username")
            first_name = data.get("first_name")
            referred_by = data.get("referred_by")
            
            logger.info(f"Creating new user {telegram_id} with 2500 coins bonus")
            
            # Create new user with 2500 coins bonus
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                coins=2500,  # New user bonus
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
            
            # If user was referred, update referrer's stats and record referred user
            if referred_by and referred_by != telegram_id:
                referrer = User.get_by_telegram_id(referred_by)
                if referrer:
                    referrer.referral_count += 1
                    referrer.referral_earnings += 100  # Bonus for referring a user
                    referrer.coins += 100
                    referrer.save()
                    
                    # Record the referred user
                    try:
                        supabase.table("referred_users").insert({
                            "referrer_id": referred_by,
                            "user_id": telegram_id,
                            "username": username,
                            "name": first_name,
                            "joined_date": int(time.time()),
                            "earnings_from_referral": 0 # Initial earnings from this referral
                        }).execute()
                    except Exception as e:
                        logger.error(f"Error recording referred user: {str(e)}")
        else:
            # Update energy based on regeneration rate for existing users
            current_time = int(time.time())
            if user.last_energy_update:
                time_diff = current_time - user.last_energy_update
                # Energy regenerates 1 per 30 seconds
                energy_regen = (time_diff / 30) * user.energy_regen_rate  
                
                user.energy = min(user.max_energy, user.energy + energy_regen)
                user.last_energy_update = current_time
                
                # Save updated energy without affecting coins
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

@user_bp.route("/api/tap", methods=["POST"])
def tap():
    try:
        # Get user data from request
        data = request.json
        telegram_id = data.get("telegram_id")
        
        if not telegram_id:
            return jsonify({"error": "Telegram ID is required"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update energy based on regeneration rate before tap
        current_time = int(time.time())
        if user.last_energy_update:
            time_diff = current_time - user.last_energy_update
            energy_regen = (time_diff / 30) * user.energy_regen_rate  
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
        
        # Save updated user data immediately
        try:
            user.save()
            logger.debug(f"User {telegram_id} tapped: coins={user.coins}, energy={user.energy}")
        except Exception as save_error:
            logger.error(f"Error saving user data after tap: {str(save_error)}")
            return jsonify({
                "success": False,
                "message": "Failed to save progress",
                "error": str(save_error)
            }), 500
        
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

@user_bp.route("/api/save_progress", methods=["POST"])
def save_progress():
    """Endpoint to manually save user progress"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        coins = data.get("coins")
        energy = data.get("energy")
        
        if not telegram_id:
            return jsonify({"error": "Telegram ID is required"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update user data if provided
        if coins is not None:
            user.coins = int(coins)
        if energy is not None:
            user.energy = float(energy)
        
        user.last_energy_update = int(time.time())
        
        # Save updated user
        try:
            user.save()
            logger.info(f"Progress saved for user {telegram_id}: coins={user.coins}, energy={user.energy}")
        except Exception as save_error:
            logger.error(f"Error saving progress: {str(save_error)}")
            return jsonify({
                "success": False,
                "message": "Failed to save progress",
                "error": str(save_error)
            }), 500
        
        return jsonify({
            "success": True,
            "message": "Progress saved successfully",
            "coins": user.coins,
            "energy": user.energy
        })
        
    except Exception as e:
        logger.error(f"Error in save_progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/update_upi", methods=["POST"])
def update_upi():
    try:
        # Get user data from request
        data = request.json
        telegram_id = data.get("telegram_id")
        upi_id = data.get("upi_id")
        
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




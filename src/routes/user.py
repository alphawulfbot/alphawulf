from flask import Blueprint, request, jsonify
from src.models.user import User
from src.config.database import supabase
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__)

@user_bp.route("/api/user/<telegram_id>", methods=["GET"])
def get_user(telegram_id):
    """Get user data by telegram ID"""
    try:
        telegram_id = str(telegram_id).strip()
        logger.info(f"Getting user data for telegram_id: {telegram_id}")
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            logger.error("Invalid telegram_id provided")
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if user:
            # Update energy before returning data
            user.update_energy()
            user.save()
            
            logger.info(f"User found: {telegram_id}")
            return jsonify(user.to_dict())
        else:
            logger.info(f"User not found: {telegram_id}")
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        logger.error(f"Error getting user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/create", methods=["POST"])
def create_user():
    """Create a new user"""
    try:
        data = request.json
        telegram_id = str(data.get("telegram_id", "")).strip()
        
        logger.info(f"Creating new user with telegram_id: {telegram_id}")
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            logger.error("Invalid telegram_id provided for user creation")
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Check if user already exists
        existing_user = User.get_by_telegram_id(telegram_id)
        if existing_user:
            logger.info(f"User already exists: {telegram_id}")
            return jsonify(existing_user.to_dict())
        
        # Create new user with 2500 coins bonus
        user = User(
            telegram_id=telegram_id,
            username=data.get("username"),
            first_name=data.get("first_name", "User"),
            coins=2500,  # New user bonus
            energy=100,
            max_energy=100,
            tap_power=1,
            energy_regen_rate=1,
            last_energy_update=int(time.time()),
            referred_by=data.get("referred_by"),
            referral_count=0,
            referral_earnings=0
        )
        
        # Save user to database
        if user.save():
            logger.info(f"New user created successfully: {telegram_id}")
            
            # Handle referral if present
            referred_by = data.get("referred_by")
            if referred_by and referred_by != telegram_id:
                try:
                    logger.info(f"Processing referral: {telegram_id} referred by {referred_by}")
                    
                    # Get referrer
                    referrer = User.get_by_telegram_id(referred_by)
                    if referrer:
                        # Add referral to referrer
                        referrer.add_referral()
                        referrer.save()
                        
                        # Record the referral relationship
                        referral_data = {
                            "referrer_id": referred_by,
                            "referred_id": telegram_id,
                            "created_at": int(time.time())
                        }
                        
                        supabase.table("referrals").insert(referral_data).execute()
                        
                        logger.info(f"Referral processed successfully: {referred_by} -> {telegram_id}")
                    else:
                        logger.warning(f"Referrer not found: {referred_by}")
                        
                except Exception as e:
                    logger.error(f"Error processing referral: {str(e)}")
                    # Don't fail user creation if referral processing fails
            
            return jsonify(user.to_dict()), 201
        else:
            logger.error(f"Failed to save new user: {telegram_id}")
            return jsonify({"error": "Failed to create user"}), 500
            
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/save", methods=["POST"])
def save_progress():
    """Save user progress"""
    try:
        data = request.json
        telegram_id = str(data.get("telegram_id", "")).strip()
        
        logger.debug(f"Saving progress for user: {telegram_id}")
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            logger.error("Invalid telegram_id provided for save progress")
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            logger.error(f"User not found for save progress: {telegram_id}")
            return jsonify({"error": "User not found"}), 404
        
        # Update user data with safe type conversion
        user.coins = user._safe_int_convert(data.get("coins", user.coins), user.coins)
        user.energy = user._safe_float_convert(data.get("energy", user.energy), user.energy)
        user.max_energy = user._safe_int_convert(data.get("max_energy", user.max_energy), user.max_energy)
        user.tap_power = user._safe_int_convert(data.get("tap_power", user.tap_power), user.tap_power)
        user.energy_regen_rate = user._safe_int_convert(data.get("energy_regen_rate", user.energy_regen_rate), user.energy_regen_rate)
        user.last_energy_update = user._safe_int_convert(data.get("last_energy_update", int(time.time())), int(time.time()))
        user.referral_count = user._safe_int_convert(data.get("referral_count", user.referral_count), user.referral_count)
        user.referral_earnings = user._safe_int_convert(data.get("referral_earnings", user.referral_earnings), user.referral_earnings)
        
        # Update UPI ID if provided
        if data.get("upi_id"):
            user.upi_id = data.get("upi_id")
        
        # Save to database
        if user.save():
            logger.debug(f"Progress saved successfully for user: {telegram_id}")
            return jsonify({"success": True, "message": "Progress saved successfully"})
        else:
            logger.error(f"Failed to save progress for user: {telegram_id}")
            return jsonify({"error": "Failed to save progress"}), 500
            
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/<telegram_id>/tap", methods=["POST"])
def tap_coin(telegram_id):
    """Handle coin tap action"""
    try:
        telegram_id = str(telegram_id).strip()
        logger.debug(f"Processing tap for user: {telegram_id}")
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update energy first
        user.update_energy()
        
        # Check if user can tap
        if not user.can_tap():
            return jsonify({
                "success": False,
                "message": "Not enough energy",
                "energy": user.energy
            })
        
        # Perform tap
        if user.tap():
            user.save()
            logger.debug(f"Tap successful for user: {telegram_id}")
            return jsonify({
                "success": True,
                "coins": user.coins,
                "energy": user.energy,
                "coins_earned": user.tap_power
            })
        else:
            return jsonify({
                "success": False,
                "message": "Tap failed"
            })
            
    except Exception as e:
        logger.error(f"Error processing tap for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/referrals/<telegram_id>", methods=["GET"])
def get_referrals(telegram_id):
    """Get referrals for a user"""
    try:
        telegram_id = str(telegram_id).strip()
        logger.info(f"Getting referrals for user: {telegram_id}")
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get referrals from database
        response = supabase.table("referrals").select("*").eq("referrer_id", telegram_id).execute()
        
        if response.data:
            referrals = []
            for referral in response.data:
                # Get referred user details
                referred_user = User.get_by_telegram_id(referral["referred_id"])
                if referred_user:
                    referrals.append({
                        "telegram_id": referred_user.telegram_id,
                        "username": referred_user.username,
                        "first_name": referred_user.first_name,
                        "created_at": referral["created_at"]
                    })
            
            logger.info(f"Found {len(referrals)} referrals for user: {telegram_id}")
            return jsonify(referrals)
        else:
            logger.info(f"No referrals found for user: {telegram_id}")
            return jsonify([])
            
    except Exception as e:
        logger.error(f"Error getting referrals for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/<telegram_id>/energy", methods=["GET"])
def get_energy(telegram_id):
    """Get current energy for a user"""
    try:
        telegram_id = str(telegram_id).strip()
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update energy
        user.update_energy()
        user.save()
        
        return jsonify({
            "energy": user.energy,
            "max_energy": user.max_energy,
            "energy_regen_rate": user.energy_regen_rate,
            "last_energy_update": user.last_energy_update
        })
        
    except Exception as e:
        logger.error(f"Error getting energy for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/<telegram_id>/stats", methods=["GET"])
def get_user_stats(telegram_id):
    """Get user statistics"""
    try:
        telegram_id = str(telegram_id).strip()
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Calculate level based on coins
        level = max(1, user.coins // 1000)
        
        # Get withdrawal count
        withdrawal_response = supabase.table("withdrawals").select("id", count="exact").eq("telegram_id", telegram_id).execute()
        withdrawal_count = withdrawal_response.count if withdrawal_response.count else 0
        
        # Calculate total upgrades purchased
        base_tap_power = 1
        base_max_energy = 100
        base_energy_regen = 1
        
        upgrades_purchased = (user.tap_power - base_tap_power) + \
                           ((user.max_energy - base_max_energy) // 20) + \
                           (user.energy_regen_rate - base_energy_regen)
        
        stats = {
            "level": level,
            "total_coins_earned": user.coins + user.referral_earnings,
            "upgrades_purchased": max(0, upgrades_purchased),
            "withdrawals_made": withdrawal_count,
            "referrals_made": user.referral_count,
            "referral_earnings": user.referral_earnings
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/api/user/validate", methods=["POST"])
def validate_user():
    """Validate user data and fix any inconsistencies"""
    try:
        data = request.json
        telegram_id = str(data.get("telegram_id", "")).strip()
        
        if not telegram_id or telegram_id == 'null' or telegram_id == 'undefined':
            return jsonify({"error": "Invalid telegram ID"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Validate and fix data
        fixed = False
        
        # Ensure minimum values
        if user.coins < 0:
            user.coins = 0
            fixed = True
        
        if user.energy < 0:
            user.energy = 0
            fixed = True
        elif user.energy > user.max_energy:
            user.energy = user.max_energy
            fixed = True
        
        if user.max_energy < 100:
            user.max_energy = 100
            fixed = True
        
        if user.tap_power < 1:
            user.tap_power = 1
            fixed = True
        
        if user.energy_regen_rate < 1:
            user.energy_regen_rate = 1
            fixed = True
        
        if user.referral_count < 0:
            user.referral_count = 0
            fixed = True
        
        if user.referral_earnings < 0:
            user.referral_earnings = 0
            fixed = True
        
        # Save if any fixes were made
        if fixed:
            user.save()
            logger.info(f"User data fixed for: {telegram_id}")
        
        return jsonify({
            "success": True,
            "fixed": fixed,
            "user_data": user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error validating user: {str(e)}")
        return jsonify({"error": str(e)}), 500


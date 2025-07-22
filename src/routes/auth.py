from flask import Blueprint, request, jsonify
from src.models.user import User
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        logger.info("Health check requested")
        return jsonify({
            "status": "healthy",
            "timestamp": int(time.time()),
            "service": "Alpha Wulf Backend"
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }), 500

@auth_bp.route("/api/auth", methods=["POST", "OPTIONS"])
def authenticate_user():
    """Enhanced authentication endpoint with better error handling"""
    
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        logger.info("CORS preflight request received")
        response = jsonify({"message": "CORS preflight"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Accept")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200
    
    try:
        # Log the incoming request
        logger.info("Authentication request received")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request origin: {request.headers.get('Origin', 'No origin')}")
        
        # Get request data with validation
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({
                "success": False,
                "error": "Request must be JSON",
                "details": f"Content-Type: {request.content_type}"
            }), 400
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400
        
        logger.info(f"Auth request data: {data}")
        
        # Validate required fields
        telegram_id = data.get("telegram_id")
        if not telegram_id:
            logger.error("Missing telegram_id in request")
            return jsonify({
                "success": False,
                "error": "telegram_id is required",
                "received_data": data
            }), 400
        
        # Convert telegram_id to string for consistency
        telegram_id = str(telegram_id).strip()
        
        if not telegram_id or telegram_id in ['null', 'undefined', '']:
            logger.error(f"Invalid telegram_id: {telegram_id}")
            return jsonify({
                "success": False,
                "error": "Invalid telegram_id",
                "received_id": telegram_id
            }), 400
        
        # Extract user data with defaults
        username = data.get("username")
        first_name = data.get("first_name", "User")
        last_name = data.get("last_name")  # This might be None
        referred_by = data.get("referred_by")
        
        logger.info(f"Processing auth for telegram_id: {telegram_id}, username: {username}, first_name: {first_name}")
        
        # Try to get existing user
        user = User.get_by_telegram_id(telegram_id)
        
        if user:
            logger.info(f"Existing user found: {telegram_id}")
            
            # Update user info if provided - FIXED: Check if attributes exist before setting
            updated = False
            if username and hasattr(user, 'username') and user.username != username:
                user.username = username
                updated = True
            if first_name and hasattr(user, 'first_name') and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            # FIXED: Only update last_name if the User model has this attribute
            if last_name and hasattr(user, 'last_name') and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            
            # Update energy before returning
            user.update_energy()
            
            if updated:
                user.save()
                logger.info(f"User info updated for: {telegram_id}")
            
        else:
            logger.info(f"Creating new user: {telegram_id}")
            
            # Create new user with bonus coins
            # FIXED: Only pass last_name if the User model supports it
            user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "coins": 2500,  # New user bonus
                "energy": 100,
                "max_energy": 100,
                "tap_power": 1,
                "energy_regen_rate": 1,
                "last_energy_update": int(time.time()),
                "referred_by": referred_by,
                "referral_count": 0,
                "referral_earnings": 0
            }
            
            # Only add last_name if it's provided and the User model supports it
            if last_name:
                # Check if User model has last_name attribute by creating a test instance
                try:
                    test_user = User(**user_data, last_name=last_name)
                    user_data["last_name"] = last_name
                except TypeError:
                    # User model doesn't support last_name, skip it
                    logger.info("User model doesn't support last_name attribute, skipping")
            
            user = User(**user_data)
            
            # Save new user
            if not user.save():
                logger.error(f"Failed to save new user: {telegram_id}")
                return jsonify({
                    "success": False,
                    "error": "Failed to create user account"
                }), 500
            
            logger.info(f"New user created successfully: {telegram_id}")
            
            # Handle referral if present
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
                        from src.config.database import supabase
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
                    # Don't fail authentication if referral processing fails
        
        # Return user data
        user_data = user.to_dict()
        logger.info(f"Authentication successful for: {telegram_id}")
        
        response = jsonify({
            "success": True,
            "message": "Authentication successful",
            "user": user_data
        })
        
        # Add CORS headers
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Accept")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
        
        response = jsonify({
            "success": False,
            "error": "Authentication failed",
            "details": str(e),
            "error_type": type(e).__name__
        })
        
        # Add CORS headers even for errors
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Accept")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        
        return response, 500

@auth_bp.route("/api/tap", methods=["POST", "OPTIONS"])
def handle_tap():
    """Enhanced tap endpoint with better error handling"""
    
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Accept")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"}), 400
        
        telegram_id = str(data.get("telegram_id", "")).strip()
        taps = int(data.get("taps", 1))
        
        if not telegram_id or telegram_id in ['null', 'undefined', '']:
            return jsonify({"success": False, "error": "Invalid telegram_id"}), 400
        
        # Get user
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        # Update energy
        user.update_energy()
        
        # Process taps
        coins_earned = 0
        for _ in range(taps):
            if user.can_tap():
                if user.tap():
                    coins_earned += user.tap_power
                else:
                    break
            else:
                break
        
        # Save user data
        user.save()
        
        response = jsonify({
            "success": True,
            "coins_earned": coins_earned,
            "total_coins": user.coins,
            "energy": user.energy
        })
        
        # Add CORS headers
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Accept")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Tap error: {str(e)}")
        
        response = jsonify({
            "success": False,
            "error": "Tap processing failed",
            "details": str(e)
        })
        
        # Add CORS headers even for errors
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Accept")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        
        return response, 500


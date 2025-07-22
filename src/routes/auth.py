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
    """Enhanced authentication endpoint compatible with existing User model"""
    
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
            
            # Update user info if provided - Check if attributes exist before setting
            updated = False
            if username and hasattr(user, 'username') and getattr(user, 'username', None) != username:
                user.username = username
                updated = True
            if first_name and hasattr(user, 'first_name') and getattr(user, 'first_name', None) != first_name:
                user.first_name = first_name
                updated = True
            # Only update last_name if the User model has this attribute
            if last_name and hasattr(user, 'last_name') and getattr(user, 'last_name', None) != last_name:
                user.last_name = last_name
                updated = True
            
            # FIXED: Check if update_energy method exists before calling it
            if hasattr(user, 'update_energy') and callable(getattr(user, 'update_energy')):
                try:
                    user.update_energy()
                    logger.info(f"Energy updated for user: {telegram_id}")
                except Exception as e:
                    logger.warning(f"Failed to update energy for user {telegram_id}: {str(e)}")
            else:
                logger.info(f"User model doesn't have update_energy method, skipping energy update")
            
            # FIXED: Check if save method exists and is callable before calling it
            if updated:
                if hasattr(user, 'save') and callable(getattr(user, 'save')):
                    try:
                        save_result = user.save()
                        if save_result is False:
                            logger.error(f"Failed to save user updates for: {telegram_id}")
                        else:
                            logger.info(f"User info updated for: {telegram_id}")
                    except Exception as e:
                        logger.error(f"Error saving user updates for {telegram_id}: {str(e)}")
                else:
                    logger.warning(f"User model doesn't have save method, cannot persist updates")
            
        else:
            logger.info(f"Creating new user: {telegram_id}")
            
            # Create new user with bonus coins
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
            if last_name and hasattr(User, '__init__'):
                # Try to create a test instance to see if last_name is supported
                try:
                    import inspect
                    sig = inspect.signature(User.__init__)
                    if 'last_name' in sig.parameters:
                        user_data["last_name"] = last_name
                        logger.info("Added last_name to user data")
                    else:
                        logger.info("User model doesn't support last_name parameter, skipping")
                except Exception as e:
                    logger.warning(f"Could not determine User model parameters: {str(e)}")
            
            try:
                user = User(**user_data)
                logger.info(f"User object created for: {telegram_id}")
            except Exception as e:
                logger.error(f"Failed to create User object: {str(e)}")
                # Try with minimal data
                try:
                    minimal_data = {
                        "telegram_id": telegram_id,
                        "username": username,
                        "first_name": first_name,
                        "coins": 2500,
                        "energy": 100
                    }
                    user = User(**minimal_data)
                    logger.info(f"User object created with minimal data for: {telegram_id}")
                except Exception as e2:
                    logger.error(f"Failed to create User object even with minimal data: {str(e2)}")
                    return jsonify({
                        "success": False,
                        "error": "Failed to create user object",
                        "details": str(e2)
                    }), 500
            
            # Save new user
            if hasattr(user, 'save') and callable(getattr(user, 'save')):
                try:
                    save_result = user.save()
                    if save_result is False:
                        logger.error(f"Failed to save new user: {telegram_id}")
                        return jsonify({
                            "success": False,
                            "error": "Failed to create user account"
                        }), 500
                    else:
                        logger.info(f"New user created successfully: {telegram_id}")
                except Exception as e:
                    logger.error(f"Error saving new user {telegram_id}: {str(e)}")
                    return jsonify({
                        "success": False,
                        "error": "Failed to save user account",
                        "details": str(e)
                    }), 500
            else:
                logger.warning(f"User model doesn't have save method, cannot persist new user")
                return jsonify({
                    "success": False,
                    "error": "User model doesn't support saving"
                }), 500
            
            # Handle referral if present
            if referred_by and referred_by != telegram_id:
                try:
                    logger.info(f"Processing referral: {telegram_id} referred by {referred_by}")
                    
                    # Get referrer
                    referrer = User.get_by_telegram_id(referred_by)
                    if referrer:
                        # Add referral to referrer if method exists
                        if hasattr(referrer, 'add_referral') and callable(getattr(referrer, 'add_referral')):
                            try:
                                referrer.add_referral()
                                if hasattr(referrer, 'save') and callable(getattr(referrer, 'save')):
                                    referrer.save()
                                logger.info(f"Referral reward added to: {referred_by}")
                            except Exception as e:
                                logger.error(f"Failed to add referral reward: {str(e)}")
                        
                        # Record the referral relationship
                        try:
                            from src.config.database import supabase
                            referral_data = {
                                "referrer_id": referred_by,
                                "referred_id": telegram_id,
                                "created_at": int(time.time())
                            }
                            
                            supabase.table("referrals").insert(referral_data).execute()
                            logger.info(f"Referral relationship recorded: {referred_by} -> {telegram_id}")
                        except Exception as e:
                            logger.error(f"Failed to record referral relationship: {str(e)}")
                        
                    else:
                        logger.warning(f"Referrer not found: {referred_by}")
                        
                except Exception as e:
                    logger.error(f"Error processing referral: {str(e)}")
                    # Don't fail authentication if referral processing fails
        
        # Return user data - FIXED: Use to_dict if available, otherwise create dict manually
        try:
            if hasattr(user, 'to_dict') and callable(getattr(user, 'to_dict')):
                user_data = user.to_dict()
            else:
                # Create dict manually from user attributes
                user_data = {}
                for attr in ['telegram_id', 'username', 'first_name', 'last_name', 'coins', 'energy', 'max_energy', 'tap_power', 'referral_count', 'referral_earnings', 'last_energy_update']:
                    if hasattr(user, attr):
                        user_data[attr] = getattr(user, attr)
                
                # Ensure required fields have defaults
                user_data.setdefault('coins', 0)
                user_data.setdefault('energy', 100)
                user_data.setdefault('max_energy', 100)
                user_data.setdefault('tap_power', 1)
                user_data.setdefault('referral_count', 0)
                user_data.setdefault('referral_earnings', 0)
                
            logger.info(f"Authentication successful for: {telegram_id}")
            
        except Exception as e:
            logger.error(f"Failed to serialize user data: {str(e)}")
            # Return minimal user data
            user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "coins": getattr(user, 'coins', 0),
                "energy": getattr(user, 'energy', 100),
                "max_energy": getattr(user, 'max_energy', 100),
                "tap_power": getattr(user, 'tap_power', 1)
            }
        
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
    """Enhanced tap endpoint compatible with existing User model"""
    
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
        
        # Update energy if method exists
        if hasattr(user, 'update_energy') and callable(getattr(user, 'update_energy')):
            try:
                user.update_energy()
            except Exception as e:
                logger.warning(f"Failed to update energy: {str(e)}")
        
        # Process taps - check if methods exist
        coins_earned = 0
        current_energy = getattr(user, 'energy', 100)
        tap_power = getattr(user, 'tap_power', 1)
        
        for _ in range(taps):
            if current_energy > 0:
                # Check if can_tap method exists
                if hasattr(user, 'can_tap') and callable(getattr(user, 'can_tap')):
                    if user.can_tap():
                        if hasattr(user, 'tap') and callable(getattr(user, 'tap')):
                            if user.tap():
                                coins_earned += tap_power
                            else:
                                break
                        else:
                            # Manual tap processing
                            user.coins = getattr(user, 'coins', 0) + tap_power
                            user.energy = max(0, getattr(user, 'energy', 100) - 1)
                            coins_earned += tap_power
                            current_energy = user.energy
                    else:
                        break
                else:
                    # Manual tap processing without can_tap method
                    if current_energy > 0:
                        user.coins = getattr(user, 'coins', 0) + tap_power
                        user.energy = max(0, current_energy - 1)
                        coins_earned += tap_power
                        current_energy = user.energy
                    else:
                        break
            else:
                break
        
        # Save user data if method exists
        if hasattr(user, 'save') and callable(getattr(user, 'save')):
            try:
                user.save()
            except Exception as e:
                logger.error(f"Failed to save tap data: {str(e)}")
        
        response = jsonify({
            "success": True,
            "coins_earned": coins_earned,
            "total_coins": getattr(user, 'coins', 0),
            "energy": getattr(user, 'energy', 100)
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


from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    try:
        logger.info("Health check requested")
        return jsonify({
            "status": "healthy",
            "timestamp": int(datetime.now().timestamp()),
            "service": "Alpha Wulf Backend"
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({"error": "Health check failed"}), 500

@auth_bp.route('/api/auth', methods=['POST', 'OPTIONS'])
@cross_origin()
def authenticate():
    """Authentication endpoint with robust error handling"""
    try:
        logger.info("Authentication request received")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request origin: {request.headers.get('Origin', 'Unknown')}")
        
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            return '', 200
        
        # Handle different Content-Type scenarios
        data = None
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            # Standard JSON request
            data = request.get_json()
        elif 'text/plain' in content_type:
            # Handle text/plain requests (convert to JSON)
            try:
                raw_data = request.get_data(as_text=True)
                data = json.loads(raw_data)
                logger.info(f"Converted text/plain to JSON: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse text/plain as JSON: {str(e)}")
                return jsonify({"error": "Invalid JSON in text/plain request"}), 400
        else:
            # Try to get JSON anyway (fallback)
            try:
                data = request.get_json(force=True)
            except Exception as e:
                logger.error(f"Failed to parse request data: {str(e)}")
                return jsonify({"error": "Invalid request format"}), 400
        
        if not data:
            logger.error("No data provided in request")
            return jsonify({"error": "No data provided"}), 400
        
        logger.info(f"Auth request data: {data}")
        
        # Extract user data
        telegram_id = data.get('telegram_id')
        username = data.get('username', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        if not telegram_id:
            logger.error("No telegram_id provided")
            return jsonify({"error": "telegram_id is required"}), 400
        
        logger.info(f"Processing auth for telegram_id: {telegram_id}, username: {username}, first_name: {first_name}")
        
        # Import User model
        from src.models.user import User
        
        # Get or create user
        user = User.get_by_telegram_id(telegram_id)
        
        if user:
            logger.info(f"Existing user found: {telegram_id}")
            # Update user info
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            
            # Update energy based on time passed
            user.update_energy()
            
            # Save user
            user.save()
        else:
            logger.info(f"Creating new user: {telegram_id}")
            # Create new user
            user = User.create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
        
        # Get real-time user data
        user_data = user.get_real_time_data()
        
        # Fix datetime serialization issues
        response_data = {
            "success": True,
            "user": {
                "telegram_id": user_data.get("telegram_id"),
                "username": user_data.get("username", ""),
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "coins": int(user_data.get("coins", 0)),
                "energy": int(user_data.get("energy", 100)),
                "max_energy": int(user_data.get("max_energy", 100)),
                "tap_power": int(user_data.get("tap_power", 1)),
                "energy_regen_rate": int(user_data.get("energy_regen_rate", 1)),
                "total_taps": int(user_data.get("total_taps", 0)),
                "referral_count": int(user_data.get("referral_count", 0)),
                "referral_earnings": int(user_data.get("referral_earnings", 0)),
                "last_energy_update": int(user_data.get("last_energy_update", 0))
            },
            "timestamp": int(datetime.now().timestamp())
        }
        
        logger.info(f"Authentication successful for user: {telegram_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            "error": "Authentication failed",
            "message": str(e),
            "timestamp": int(datetime.now().timestamp())
        }), 500

@auth_bp.route('/api/debug', methods=['GET'])
@cross_origin()
def debug_info():
    """Debug endpoint for troubleshooting"""
    try:
        return jsonify({
            "status": "debug_active",
            "timestamp": int(datetime.now().timestamp()),
            "endpoints": [
                "/api/health",
                "/api/auth",
                "/api/debug"
            ],
            "message": "Debug endpoint is working"
        }), 200
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return jsonify({"error": "Debug failed"}), 500


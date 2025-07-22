from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging
import json

# Import the User model
from src.models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return jsonify({
        "status": "healthy",
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "service": "Alpha Wulf Backend"
    }), 200

@auth_bp.route('/api/auth', methods=['OPTIONS'])
def auth_options():
    """Handle CORS preflight requests"""
    logger.info("CORS preflight request received")
    response = jsonify({"message": "CORS preflight"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response, 200

@auth_bp.route('/api/auth', methods=['POST'])
def authenticate():
    """Authenticate user and return user data"""
    try:
        logger.info("Authentication request received")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request origin: {request.headers.get('Origin', 'No origin')}")
        
        # Check if request is JSON
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Request must be JSON", "success": False}), 400
        
        data = request.get_json()
        logger.info(f"Auth request data: {data}")
        
        if not data:
            logger.error("No data received")
            return jsonify({"error": "No data received", "success": False}), 400
        
        # Extract user data
        telegram_id = data.get('telegram_id')
        username = data.get('username', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        if not telegram_id:
            logger.error("No telegram_id provided")
            return jsonify({"error": "telegram_id is required", "success": False}), 400
        
        logger.info(f"Processing auth for telegram_id: {telegram_id}, username: {username}, first_name: {first_name}")
        
        # Try to get existing user
        user = User.get_by_telegram_id(telegram_id)
        
        if user:
            logger.info(f"Existing user found: {telegram_id}")
            
            # Update user information
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            if last_name:  # Only update if provided
                user.last_name = last_name
            
            # Update energy based on time passed
            user.update_energy()
            
            # Save updated user data
            if user.save():
                logger.info(f"User data updated successfully for {telegram_id}")
            else:
                logger.warning(f"Failed to save user data for {telegram_id}")
        else:
            logger.info(f"Creating new user: {telegram_id}")
            
            # Create new user
            user = User.create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            
            if not user:
                logger.error(f"Failed to create user {telegram_id}")
                return jsonify({
                    "error": "Failed to create user",
                    "success": False
                }), 500
        
        # Return user data
        user_data = user.to_dict()
        logger.info(f"Authentication successful for user {telegram_id}")
        
        response_data = {
            "success": True,
            "user": user_data,
            "message": "Authentication successful"
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else {}}")
        
        return jsonify({
            "error": "Authentication failed",
            "message": str(e),
            "success": False
        }), 500

@auth_bp.route('/api/user/tap', methods=['POST'])
def tap():
    """Handle tap action"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({"error": "telegram_id is required", "success": False}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found", "success": False}), 404
        
        if user.tap():
            return jsonify({
                "success": True,
                "user": user.to_dict(),
                "message": "Tap successful"
            }), 200
        else:
            return jsonify({
                "error": "Cannot tap - no energy",
                "success": False
            }), 400
            
    except Exception as e:
        logger.error(f"Tap error: {str(e)}")
        return jsonify({
            "error": "Tap failed",
            "message": str(e),
            "success": False
        }), 500

@auth_bp.route('/api/user/data', methods=['GET'])
def get_user_data():
    """Get user data"""
    try:
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id:
            return jsonify({"error": "telegram_id is required", "success": False}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found", "success": False}), 404
        
        # Update energy before returning data
        user.update_energy()
        user.save()
        
        response = jsonify({
            "success": True,
            "user": user.to_dict()
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Get user data error: {str(e)}")
        return jsonify({
            "error": "Failed to get user data",
            "message": str(e),
            "success": False
        }), 500

@auth_bp.route('/api/user/upgrade', methods=['POST'])
def upgrade():
    """Handle upgrade action"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        upgrade_type = data.get('upgrade_type')
        cost = data.get('cost', 0)
        
        if not telegram_id:
            return jsonify({"error": "telegram_id is required", "success": False}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found", "success": False}), 404
        
        if upgrade_type == 'tap_power':
            if user.upgrade_tap_power(cost):
                return jsonify({
                    "success": True,
                    "user": user.to_dict(),
                    "message": "Upgrade successful"
                }), 200
            else:
                return jsonify({
                    "error": "Cannot afford upgrade",
                    "success": False
                }), 400
        else:
            return jsonify({
                "error": "Invalid upgrade type",
                "success": False
            }), 400
            
    except Exception as e:
        logger.error(f"Upgrade error: {str(e)}")
        return jsonify({
            "error": "Upgrade failed",
            "message": str(e),
            "success": False
        }), 500


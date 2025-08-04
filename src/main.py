"""
Alpha Wulf Flask Backend Application

This is the main Flask application for the Alpha Wulf Telegram bot backend.
It handles user authentication, game mechanics, and API endpoints.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Import the User model
from src.models.comprehensive_user_model import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Configure CORS - Allow all origins for development
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

@app.route('/')
def home():
    """Basic health check endpoint."""
    return jsonify({"status": "Alpha Wulf Backend is running", "timestamp": datetime.now().isoformat()})

@app.route('/api/auth', methods=['POST', 'OPTIONS'])
def authenticate():
    """Authenticate user with Telegram data."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        logger.info(f"Auth request received - Method: {request.method}, Content-Type: {request.content_type}")
        
        # Get JSON data from request
        auth_data = request.get_json()
        if not auth_data:
            logger.error("No JSON data received in auth request")
            return jsonify({"error": "No data provided"}), 400
        
        logger.info(f"Auth data received: {auth_data}")
        
        # Extract Telegram user data
        telegram_id = auth_data.get('telegram_id')
        username = auth_data.get('username', '')
        first_name = auth_data.get('first_name', '')
        last_name = auth_data.get('last_name', '')
        
        if not telegram_id:
            logger.error("No telegram_id provided in auth data")
            return jsonify({"error": "telegram_id is required"}), 400
        
        logger.info(f"Authenticating user: {telegram_id}")
        
        # Try to get existing user
        user = User.get_by_telegram_id(telegram_id)
        
        if user:
            logger.info(f"Existing user found: {telegram_id}")
            # Update user energy before returning data
            user.update_energy()
        else:
            logger.info(f"Creating new user: {telegram_id}")
            # Create new user
            user = User.create_user(telegram_id, username, first_name, last_name)
            if not user:
                logger.error(f"Failed to create user: {telegram_id}")
                return jsonify({"error": "Failed to create user"}), 500
        
        # Return user data
        user_data = user.to_dict()
        logger.info(f"Authentication successful for user: {telegram_id}")
        return jsonify({
            "success": True,
            "user": user_data
        })
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/api/tap', methods=['POST'])
def tap():
    """Handle user tap action."""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        taps = data.get('taps', 1)
        
        if not telegram_id:
            return jsonify({"error": "telegram_id is required"}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        success, message = user.tap(taps)
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "user": user.to_dict()
            })
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        logger.error(f"Tap error: {e}")
        return jsonify({"error": "Tap failed"}), 500

@app.route('/api/user/<int:telegram_id>', methods=['GET'])
def get_user(telegram_id):
    """Get user data by Telegram ID."""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update energy before returning data
        user.update_energy()
        
        return jsonify({
            "success": True,
            "user": user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({"error": "Failed to get user"}), 500

@app.route('/api/admin/users', methods=['GET'])
def admin_get_all_users():
    """Admin endpoint to get all users."""
    try:
        # For now, we'll skip admin authentication and return all users
        # In production, you should implement proper admin authentication
        
        from src.models.comprehensive_user_model import get_supabase_client
        supabase_client = get_supabase_client()
        response = supabase_client.from_("users").select("*").execute()
        
        return jsonify({
            "success": True,
            "users": response.data
        })
        
    except Exception as e:
        logger.error(f"Admin get users error: {e}")
        return jsonify({"error": "Failed to get users"}), 500

@app.route('/api/admin/user/<int:telegram_id>/coins', methods=['POST'])
def admin_update_user_coins(telegram_id):
    """Admin endpoint to update user coins."""
    try:
        data = request.get_json()
        amount = data.get('amount', 0)
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.coins += amount
        if user.save():
            return jsonify({
                "success": True,
                "message": "Coins updated successfully",
                "user": user.to_dict()
            })
        else:
            return jsonify({"error": "Failed to update coins"}), 500
            
    except Exception as e:
        logger.error(f"Admin update coins error: {e}")
        return jsonify({"error": "Failed to update coins"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


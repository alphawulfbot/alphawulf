"""
Complete Alpha Wulf Flask Application - Final Fix for Render Deployment

This version addresses the ModuleNotFoundError by ensuring correct absolute imports
for Render's typical 'src' directory structure, specifically for models within 'src/models'.

Integrates all previous fixes for CORS, real-time data synchronization,
and preserves original UI/UX while fixing backend connection issues.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import User model assuming main.py is in src/ and User model is in src/models/
from src.models.comprehensive_user_model import User

def create_app():
    """Create and configure Flask application with corrected CORS"""
    
    app = Flask(__name__)
    
    # CORRECTED CORS Configuration - Single setup to prevent duplicate headers
    CORS(app, 
         origins=["*"],  # Allow all origins
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
         supports_credentials=False,
         max_age=86400)  # Cache preflight for 24 hours
    
    # Helper function to parse request data
    def get_request_data():
        """Parse request data from different content types"""
        try:
            if request.content_type and "application/json" in request.content_type:
                return request.get_json()
            else:
                # Handle text/plain or other content types
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    return json.loads(raw_data)
                else:
                    return request.form.to_dict()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON decode error: {e}")
            return None
    
    # Health check endpoint
    @app.route("/api/health", methods=["GET", "OPTIONS"])
    def health_check():
        """Health check endpoint with proper CORS handling"""
        if request.method == "OPTIONS":
            # Handle preflight request
            return "", 200
            
        try:
            return jsonify({
                "status": "healthy",
                "timestamp": int(time.time()),
                "service": "Alpha Wulf Backend"
            }), 200
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    # Authentication endpoint
    @app.route("/api/auth", methods=["POST", "OPTIONS"])
    def authenticate_user():
        """Authenticate user with comprehensive error handling"""
        try:
            # Handle CORS preflight
            if request.method == "OPTIONS":
                return "", 200
            
            logger.info(f"Auth request received - Method: {request.method}, Content-Type: {request.content_type}")
            
            # Parse request data
            data = get_request_data()
            if not data:
                logger.error("No data received in auth request")
                return jsonify({
                    "success": False,
                    "error": "Invalid JSON data"
                }), 400
            
            logger.info(f"Auth data received: {data}")
            
            # Validate required fields
            telegram_id = data.get("telegram_id")
            if not telegram_id:
                return jsonify({
                    "success": False,
                    "error": "Missing telegram_id"
                }), 400
            
            username = data.get("username", "")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            
            logger.info(f"Authenticating user: {telegram_id}")
            
            # Get or create user
            user = User.get_by_telegram_id(telegram_id)
            
            if user:
                logger.info(f"Existing user found: {telegram_id}")
                # Update user info
                user.username = username
                user.first_name = first_name
                if last_name:  # Only update if provided
                    user.last_name = last_name
                
                # Update energy based on time elapsed
                user.update_energy()
                
                # Save updated user data
                if not user.save():
                    logger.error(f"Failed to save existing user: {telegram_id}")
                    return jsonify({
                        "success": False,
                        "error": "Failed to update user data"
                    }), 500
            else:
                logger.info(f"Creating new user: {telegram_id}")
                user = User.create_user(telegram_id, username, first_name, last_name)
                
                if not user:
                    logger.error(f"Failed to create user: {telegram_id}")
                    return jsonify({
                        "success": False,
                        "error": "Failed to create user"
                    }), 500
            
            # Return user data
            user_data = user.to_dict()
            logger.info(f"Authentication successful for user: {telegram_id}")
            
            return jsonify({
                "success": True,
                "user": user_data,
                "message": "Authentication successful"
            }), 200
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }), 500
    
    # Tap endpoint
    @app.route("/api/tap", methods=["POST", "OPTIONS"])
    def handle_tap():
        """Handle tap requests with proper error handling"""
        try:
            # Handle CORS preflight
            if request.method == "OPTIONS":
                return "", 200
            
            # Parse request data
            data = get_request_data()
            if not data:
                return jsonify({
                    "success": False,
                    "error": "Invalid JSON data"
                }), 400
            
            telegram_id = data.get("telegram_id")
            taps = data.get("taps", 1)
            
            if not telegram_id:
                return jsonify({
                    "success": False,
                    "error": "Missing telegram_id"
                }), 400
            
            logger.info(f"Tap request: user {telegram_id}, taps {taps}")
            
            # Get user
            user = User.get_by_telegram_id(telegram_id)
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 404
            
            # Process tap
            success, message = user.tap(taps)
            
            if success:
                return jsonify({
                    "success": True,
                    "user": user.to_dict(),
                    "message": message
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": message
                }), 400
                
        except Exception as e:
            logger.error(f"Tap error: {e}")
            return jsonify({
                "success": False,
                "error": f"Tap failed: {str(e)}"
            }), 500
    
    # User data endpoint
    @app.route("/api/user/<int:telegram_id>", methods=["GET", "OPTIONS"])
    def get_user_data(telegram_id):
        """Get user data endpoint"""
        try:
            # Handle CORS preflight
            if request.method == "OPTIONS":
                return "", 200
            
            logger.info(f"Getting user data for: {telegram_id}")
            
            # Get user
            user = User.get_by_telegram_id(telegram_id)
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 404
            
            # Update energy
            user.update_energy()
            user.save()
            
            return jsonify({
                "success": True,
                "user": user.to_dict()
            }), 200
            
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to get user: {str(e)}"
            }), 500
    
    return app

# Create the Flask application
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)



"""
Complete Alpha Wulf Flask Application
Integrates all fixes and ensures real-time data synchronization
Preserves original UI/UX while fixing backend connection issues
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

def create_app():
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    
    # Configure CORS to handle all content types and origins
    CORS(app, 
         origins=['*'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With'],
         supports_credentials=False)
    
    # Helper function to parse request data
    def get_request_data():
        """Parse request data from different content types"""
        try:
            if request.content_type and 'application/json' in request.content_type:
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
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'Alpha Wulf Backend'
            }), 200
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Authentication endpoint
    @app.route('/api/auth', methods=['POST', 'OPTIONS'])
    def authenticate_user():
        """Authenticate user with comprehensive error handling"""
        try:
            # Handle CORS preflight
            if request.method == 'OPTIONS':
                return '', 200
            
            # Parse request data
            data = get_request_data()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
            
            # Validate required fields
            telegram_id = data.get('telegram_id')
            if not telegram_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing telegram_id'
                }), 400
            
            username = data.get('username', '')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            
            logger.info(f"Authenticating user: {telegram_id}")
            
            # Import User model
            try:
                from comprehensive_user_model import User
            except ImportError:
                logger.error("Failed to import User model")
                return jsonify({
                    'success': False,
                    'error': 'Server configuration error'
                }), 500
            
            # Get or create user
            try:
                user = User.get_by_telegram_id(telegram_id)
                if not user:
                    # Create new user
                    user = User.create_user(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name
                    )
                    if not user:
                        return jsonify({
                            'success': False,
                            'error': 'Failed to create user'
                        }), 500
                    logger.info(f"Created new user: {telegram_id}")
                else:
                    # Update existing user info
                    user.username = username
                    user.first_name = first_name
                    if last_name:
                        user.last_name = last_name
                    
                    # Update energy
                    user.update_energy()
                    
                    # Save user data
                    if not user.save():
                        logger.warning(f"Failed to save user updates: {telegram_id}")
                    
                    logger.info(f"Updated existing user: {telegram_id}")
                
                # Return user data
                user_data = user.to_dict()
                
                return jsonify({
                    'success': True,
                    'user': user_data,
                    'message': 'Authentication successful'
                }), 200
                
            except Exception as db_error:
                logger.error(f"Database error during authentication: {db_error}")
                return jsonify({
                    'success': False,
                    'error': 'Database error occurred'
                }), 500
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    # Tap endpoint
    @app.route('/api/tap', methods=['POST', 'OPTIONS'])
    def handle_tap():
        """Handle tap requests"""
        try:
            # Handle CORS preflight
            if request.method == 'OPTIONS':
                return '', 200
            
            # Parse request data
            data = get_request_data()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
            
            telegram_id = data.get('telegram_id')
            taps = int(float(data.get('taps', 1)))
            
            if not telegram_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing telegram_id'
                }), 400
            
            # Import User model
            try:
                from comprehensive_user_model import User
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'Server configuration error'
                }), 500
            
            # Get user and process tap
            user = User.get_by_telegram_id(telegram_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Process tap
            if user.tap(taps):
                return jsonify({
                    'success': True,
                    'coins': user.coins,
                    'energy': user.energy,
                    'message': f'Tapped {taps} times'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Insufficient energy or tap failed'
                }), 400
            
        except Exception as e:
            logger.error(f"Tap error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    # User data endpoint
    @app.route('/api/user/<int:telegram_id>', methods=['GET'])
    def get_user_data(telegram_id):
        """Get user data by telegram_id"""
        try:
            from comprehensive_user_model import User
            
            user = User.get_by_telegram_id(telegram_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Update energy before returning data
            user.update_energy()
            user.save()
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            logger.error(f"Get user data error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    # Upgrade endpoint
    @app.route('/api/upgrade', methods=['POST', 'OPTIONS'])
    def handle_upgrade():
        """Handle upgrade requests"""
        try:
            # Handle CORS preflight
            if request.method == 'OPTIONS':
                return '', 200
            
            # Parse request data
            data = get_request_data()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
            
            telegram_id = data.get('telegram_id')
            if not telegram_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing telegram_id'
                }), 400
            
            from comprehensive_user_model import User
            
            user = User.get_by_telegram_id(telegram_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Process upgrade
            if user.upgrade_tap_power():
                return jsonify({
                    'success': True,
                    'user': user.to_dict(),
                    'message': 'Upgrade successful'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Insufficient coins for upgrade'
                }), 400
            
        except Exception as e:
            logger.error(f"Upgrade error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    # Admin endpoints
    @app.route('/api/admin/users', methods=['GET'])
    def get_all_users():
        """Get all users for admin panel"""
        try:
            from comprehensive_user_model import User
            
            # Get pagination parameters
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            users = User.get_all_users(limit=limit, offset=offset)
            total_count = User.get_user_count()
            
            return jsonify({
                'success': True,
                'users': [user.to_dict() for user in users],
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            }), 200
            
        except Exception as e:
            logger.error(f"Get all users error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/api/admin/user/<int:telegram_id>/coins', methods=['POST'])
    def adjust_user_coins(telegram_id):
        """Adjust user coins (admin only)"""
        try:
            data = get_request_data()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
            
            coins_adjustment = int(float(data.get('coins', 0)))
            
            from comprehensive_user_model import User
            
            user = User.get_by_telegram_id(telegram_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            user.coins = max(0, user.coins + coins_adjustment)
            
            if user.save():
                return jsonify({
                    'success': True,
                    'user': user.to_dict(),
                    'message': f'Adjusted coins by {coins_adjustment}'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save changes'
                }), 500
            
        except Exception as e:
            logger.error(f"Adjust coins error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    # CORS handlers
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
    
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


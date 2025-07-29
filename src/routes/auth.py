from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging
from src.models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        logger.info("Health check requested")
        return jsonify({
            'status': 'healthy',
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'service': 'Alpha Wulf Backend',
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@auth_bp.route('/api/auth', methods=['POST', 'OPTIONS'])
def authenticate():
    """Authenticate user and return real-time data"""
    if request.method == 'OPTIONS':
        logger.info("CORS preflight request received")
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    try:
        logger.info("Authentication request received")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request origin: {request.headers.get('Origin', 'No origin')}")
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
        
        logger.info(f"Auth request data: {data}")
        
        telegram_id = data.get('telegram_id')
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        if not telegram_id:
            logger.error("No telegram_id provided")
            return jsonify({'error': 'telegram_id is required'}), 400
        
        logger.info(f"Processing auth for telegram_id: {telegram_id}, username: {username}, first_name: {first_name}")
        
        # Try to get existing user
        user = User.get_by_telegram_id(telegram_id)
        
        if user:
            logger.info(f"Existing user found: {telegram_id}")
            
            # Update user info if provided
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            
            # Save updates if any
            if updated:
                if user.save():
                    logger.info(f"Updated user info for {telegram_id}")
                else:
                    logger.warning(f"Failed to save user updates for {telegram_id}")
        else:
            logger.info(f"Creating new user: {telegram_id}")
            user = User.create_user(telegram_id, username, first_name, last_name)
            
            if not user:
                logger.error(f"Failed to create user: {telegram_id}")
                return jsonify({'error': 'Failed to create user'}), 500
        
        # Get real-time user data
        user_data = user.get_real_time_data()
        
        logger.info(f"Authentication successful for user {telegram_id}")
        
        response = jsonify({
            'success': True,
            'user': user_data
        })
        
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        return response
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'error': 'Authentication failed',
            'message': str(e)
        }), 500

@auth_bp.route('/api/user/sync/<int:telegram_id>', methods=['GET'])
def sync_user_data(telegram_id):
    """Sync user data - get real-time data"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get real-time data with energy updates
        user_data = user.get_real_time_data()
        
        return jsonify({
            'success': True,
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"Error syncing user data for {telegram_id}: {str(e)}")
        return jsonify({'error': 'Sync failed'}), 500

@auth_bp.route('/api/user/refresh/<int:telegram_id>', methods=['POST'])
def refresh_user_data(telegram_id):
    """Refresh user data - force real-time update"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Force energy update and save
        user.update_energy()
        user.save()
        
        # Get fresh data
        user_data = user.get_real_time_data()
        
        return jsonify({
            'success': True,
            'user': user_data,
            'refreshed_at': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error refreshing user data for {telegram_id}: {str(e)}")
        return jsonify({'error': 'Refresh failed'}), 500


from flask import Blueprint, request, jsonify
import logging
from src.models.user import User
from src.config.database import supabase

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get admin statistics with real-time data"""
    try:
        users = User.get_all_users()
        
        total_users = len(users)
        active_users = len([u for u in users if u.total_taps > 0])
        total_coins = sum(u.coins for u in users)
        
        # Get withdrawal stats
        try:
            withdrawals_response = supabase.table('withdrawals').select('*').execute()
            total_withdrawals = len(withdrawals_response.data) if withdrawals_response.data else 0
        except:
            total_withdrawals = 0
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_coins': total_coins,
            'total_withdrawals': total_withdrawals,
            'average_coins': total_coins // total_users if total_users > 0 else 0
        }
        
        logger.info(f"Stats: {total_users} users, {active_users} active, {total_coins} coins, {total_withdrawals} withdrawals")
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        return jsonify({'error': 'Failed to get stats'}), 500

@admin_bp.route('/api/admin/users', methods=['GET'])
def get_all_users():
    """Get all users with real-time data"""
    try:
        users = User.get_all_users()
        
        users_data = []
        for user in users:
            user_data = user.get_real_time_data()
            users_data.append(user_data)
        
        return jsonify({
            'users': users_data,
            'count': len(users_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        return jsonify({'error': 'Failed to get users'}), 500

@admin_bp.route('/api/admin/user/coins', methods=['POST'])
def adjust_user_coins():
    """Adjust user coins with real-time sync"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not user_id or amount is None:
            return jsonify({'error': 'user_id and amount are required'}), 400
        
        user = User.get_by_telegram_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        old_coins = user.coins
        
        if amount > 0:
            success = user.add_coins(amount)
        else:
            success = user.subtract_coins(abs(amount))
        
        if success:
            logger.info(f"Admin adjusted coins for user {user_id}: {old_coins} -> {user.coins} ({amount:+d})")
            return jsonify({
                'success': True,
                'old_coins': old_coins,
                'new_coins': user.coins,
                'adjustment': amount
            })
        else:
            return jsonify({'error': 'Failed to adjust coins'}), 500
            
    except Exception as e:
        logger.error(f"Error adjusting user coins: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/api/admin/user/reset', methods=['POST'])
def reset_user():
    """Reset user data with real-time sync"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.get_by_telegram_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.reset_user_data():
            logger.info(f"Admin reset user {user_id}")
            return jsonify({
                'success': True,
                'user': user.get_real_time_data()
            })
        else:
            return jsonify({'error': 'Failed to reset user'}), 500
            
    except Exception as e:
        logger.error(f"Error resetting user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/api/admin/user/delete', methods=['POST'])
def delete_user():
    """Delete user with real-time sync"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.get_by_telegram_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.delete():
            logger.info(f"Admin deleted user {user_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete user'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/api/admin/withdrawals', methods=['GET'])
def get_withdrawals():
    """Get all withdrawals with real-time data"""
    try:
        response = supabase.table('withdrawals').select('*').execute()
        
        withdrawals = response.data if response.data else []
        
        return jsonify({
            'withdrawals': withdrawals,
            'count': len(withdrawals)
        })
        
    except Exception as e:
        logger.error(f"Error getting withdrawals: {str(e)}")
        return jsonify({'error': 'Failed to get withdrawals'}), 500

@admin_bp.route('/api/admin/withdrawal/update', methods=['POST'])
def update_withdrawal_status():
    """Update withdrawal status with real-time sync"""
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        status = data.get('status')
        
        if not withdrawal_id or not status:
            return jsonify({'error': 'withdrawal_id and status are required'}), 400
        
        if status not in ['pending', 'completed', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        response = supabase.table('withdrawals').update({
            'status': status,
            'updated_at': 'now()'
        }).eq('id', withdrawal_id).execute()
        
        if response.data:
            logger.info(f"Admin updated withdrawal {withdrawal_id} status to {status}")
            return jsonify({
                'success': True,
                'withdrawal': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to update withdrawal'}), 500
            
    except Exception as e:
        logger.error(f"Error updating withdrawal: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/api/admin/system/health', methods=['GET'])
def system_health():
    """Get system health with real-time data"""
    try:
        # Test database connection
        db_healthy = True
        try:
            supabase.table('users').select('id').limit(1).execute()
        except:
            db_healthy = False
        
        # Get user count
        users = User.get_all_users()
        user_count = len(users)
        
        # Calculate system stats
        active_users = len([u for u in users if u.total_taps > 0])
        total_coins = sum(u.coins for u in users)
        
        health_data = {
            'status': 'healthy' if db_healthy else 'unhealthy',
            'database': 'connected' if db_healthy else 'disconnected',
            'users': {
                'total': user_count,
                'active': active_users
            },
            'economy': {
                'total_coins': total_coins,
                'average_coins': total_coins // user_count if user_count > 0 else 0
            },
            'timestamp': int(datetime.now(timezone.utc).timestamp())
        }
        
        return jsonify(health_data)
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


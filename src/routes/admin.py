from flask import Blueprint, request, jsonify, render_template
from src.models.user import User
import time

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/users', methods=['GET'])
def get_users():
    """
    Get all users for admin panel
    """
    try:
        # Get all users from database
        from src.config.database import supabase
        response = supabase.table('users').select('*').execute()
        users = response.data
        
        return jsonify({
            'success': True,
            'users': users
        })
        
    except Exception as e:
        print(f"Error in get_users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/withdrawals', methods=['GET'])
def get_withdrawals():
    """
    Get all withdrawals for admin panel
    """
    try:
        # Get all withdrawals from database
        from src.config.database import supabase
        response = supabase.table('withdrawals').select('*').order('created_at', desc=True).execute()
        withdrawals = response.data
        
        return jsonify({
            'success': True,
            'withdrawals': withdrawals
        })
        
    except Exception as e:
        print(f"Error in get_withdrawals: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/withdrawal/<withdrawal_id>', methods=['PUT'])
def update_withdrawal(withdrawal_id):
    """
    Update withdrawal status
    """
    try:
        data = request.json
        status = data.get('status')
        
        if not status:
            return jsonify({'error': 'Missing status parameter'}), 400
        
        # Update withdrawal status
        from src.config.database import supabase
        response = supabase.table('withdrawals').update({'status': status}).eq('id', withdrawal_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Withdrawal not found'}), 404
        
        return jsonify({
            'success': True,
            'withdrawal': response.data[0]
        })
        
    except Exception as e:
        print(f"Error in update_withdrawal: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/stats', methods=['GET'])
def get_stats():
    """
    Get admin dashboard stats
    """
    try:
        # Get all users
        from src.config.database import supabase
        users_response = supabase.table('users').select('*').execute()
        users = users_response.data
        
        # Get all withdrawals
        withdrawals_response = supabase.table('withdrawals').select('*').execute()
        withdrawals = withdrawals_response.data
        
        # Calculate stats
        total_users = len(users)
        total_coins = sum(user.get('coins', 0) for user in users)
        
        # Active users in last 24 hours
        current_time = int(time.time())
        active_users = sum(1 for user in users if user.get('last_energy_update', 0) > current_time - 86400)
        
        # Withdrawal stats
        total_withdrawals = len(withdrawals)
        pending_withdrawals = sum(1 for w in withdrawals if w.get('status') == 'pending')
        completed_withdrawals = sum(1 for w in withdrawals if w.get('status') == 'completed')
        
        # Total withdrawn amount
        total_withdrawn = sum(w.get('final_amount', 0) for w in withdrawals if w.get('status') == 'completed')
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'total_coins': total_coins,
                'total_withdrawals': total_withdrawals,
                'pending_withdrawals': pending_withdrawals,
                'completed_withdrawals': completed_withdrawals,
                'total_withdrawn': total_withdrawn
            }
        })
        
    except Exception as e:
        print(f"Error in get_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin', methods=['GET'])
def admin_panel():
    """
    Render admin panel
    """
    return render_template('admin.html')


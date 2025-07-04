from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session, flash
from src.models.user import User
from src.config.database import supabase
import logging
import os
import time
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

# Admin credentials - should be stored securely in environment variables
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'alphawulf2025')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@admin_bp.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin.html')

@admin_bp.route('/api/admin/users')
@login_required
def get_users():
    try:
        # Get all users from database
        response = supabase.table("users").select("*").execute()
        
        if response.data:
            users = response.data
            logger.info(f"Retrieved {len(users)} users")
            return jsonify({"users": users})
        else:
            logger.info("Retrieved 0 users")
            return jsonify({"users": []})
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        return jsonify({"users": [], "error": str(e)}), 500

@admin_bp.route('/api/admin/withdrawals')
@login_required
def get_withdrawals():
    try:
        # Get all withdrawals from database, ordered by created_at desc
        response = supabase.table("withdrawals").select("*").order("created_at", desc=True).execute()
        
        if response.data:
            withdrawals = response.data
            logger.info(f"Retrieved {len(withdrawals)} withdrawals")
            return jsonify({"withdrawals": withdrawals})
        else:
            logger.info("Retrieved 0 withdrawals")
            return jsonify({"withdrawals": []})
    except Exception as e:
        logger.error(f"Error retrieving withdrawals: {str(e)}")
        return jsonify({"withdrawals": [], "error": str(e)}), 500

@admin_bp.route('/api/admin/stats')
@login_required
def get_stats():
    try:
        # Get all users
        users_response = supabase.table("users").select("*").execute()
        users = users_response.data if users_response.data else []
        
        # Get all withdrawals
        withdrawals_response = supabase.table("withdrawals").select("*").execute()
        withdrawals = withdrawals_response.data if withdrawals_response.data else []
        
        # Calculate stats
        total_users = len(users)
        
        # Active users in the last 24 hours
        current_time = int(time.time())
        active_users = sum(1 for user in users if user.get('last_energy_update') and current_time - user.get('last_energy_update') < 86400)
        
        # Total coins across all users
        total_coins = sum(user.get('coins', 0) for user in users)
        
        # Total withdrawals
        total_withdrawals = len(withdrawals)
        
        # Pending withdrawals
        pending_withdrawals = sum(1 for withdrawal in withdrawals if withdrawal.get('status') == 'pending')
        
        # Total withdrawn amount
        total_withdrawn = sum(withdrawal.get('amount', 0) for withdrawal in withdrawals if withdrawal.get('status') == 'completed')
        
        logger.info(f"Stats: {total_users} users, {active_users} active, {total_coins} coins, {total_withdrawals} withdrawals")
        
        return jsonify({
            "total_users": total_users,
            "active_users": active_users,
            "total_coins": total_coins,
            "total_withdrawals": total_withdrawals,
            "pending_withdrawals": pending_withdrawals,
            "total_withdrawn": total_withdrawn
        })
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        return jsonify({
            "total_users": 0,
            "active_users": 0,
            "total_coins": 0,
            "total_withdrawals": 0,
            "pending_withdrawals": 0,
            "total_withdrawn": 0,
            "error": str(e)
        }), 500

@admin_bp.route('/api/admin/approve_withdrawal/<int:withdrawal_id>', methods=['POST'])
@login_required
def approve_withdrawal(withdrawal_id):
    try:
        # Update withdrawal status to completed
        response = supabase.table("withdrawals").update({"status": "completed"}).eq("id", withdrawal_id).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({"success": True, "message": "Withdrawal approved"})
        else:
            return jsonify({"success": False, "message": "Withdrawal not found"}), 404
    except Exception as e:
        logger.error(f"Error approving withdrawal: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/api/admin/reject_withdrawal/<int:withdrawal_id>', methods=['POST'])
@login_required
def reject_withdrawal(withdrawal_id):
    try:
        # Get withdrawal details
        withdrawal_response = supabase.table("withdrawals").select("*").eq("id", withdrawal_id).execute()
        
        if not withdrawal_response.data or len(withdrawal_response.data) == 0:
            return jsonify({"success": False, "message": "Withdrawal not found"}), 404
        
        withdrawal = withdrawal_response.data[0]
        user_id = withdrawal.get("user_id")
        amount = withdrawal.get("amount")
        
        # Update withdrawal status to rejected
        update_response = supabase.table("withdrawals").update({"status": "rejected"}).eq("id", withdrawal_id).execute()
        
        if not update_response.data or len(update_response.data) == 0:
            return jsonify({"success": False, "message": "Failed to update withdrawal status"}), 500
        
        # Refund coins to user
        user_response = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
        
        if not user_response.data or len(user_response.data) == 0:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        user = user_response.data[0]
        current_coins = user.get("coins", 0)
        
        # Update user coins
        user_update_response = supabase.table("users").update({"coins": current_coins + amount}).eq("telegram_id", user_id).execute()
        
        if not user_update_response.data or len(user_update_response.data) == 0:
            return jsonify({"success": False, "message": "Failed to refund coins to user"}), 500
        
        return jsonify({"success": True, "message": "Withdrawal rejected and coins refunded"})
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
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

# Admin credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'alphawulf2025')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/admin')
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@admin_bp.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/admin/login')

@admin_bp.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@admin_bp.route('/api/admin/users')
@login_required
def get_users():
    try:
        # Get all users
        users = User.get_all_users()
        logger.info(f"Retrieved {len(users)} users")
        
        # Format users for display
        formatted_users = []
        for user in users:
            formatted_users.append({
                "id": user.telegram_id,
                "username": user.username or "N/A",
                "name": user.first_name or "N/A",
                "coins": user.coins,
                "energy": user.energy,
                "tap_power": user.tap_power,
                "referrals": user.referral_count,
                "last_active": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(user.last_energy_update)) if user.last_energy_update else "N/A"
            })
        
        return jsonify({"users": formatted_users})
    except Exception as e:
        logger.error(f"Error in get_users: {str(e)}")
        return jsonify({"users": []})

@admin_bp.route('/api/admin/withdrawals')
@login_required
def get_withdrawals():
    try:
        # Get all withdrawals
        response = supabase.table("withdrawals").select("*").order("created_at", desc=True).execute()
        
        if response.data:
            withdrawals = response.data
            logger.info(f"Retrieved {len(withdrawals)} withdrawals")
            
            # Format withdrawals for display
            formatted_withdrawals = []
            for withdrawal in withdrawals:
                # Get user info
                user_id = withdrawal.get("user_id")
                user = User.get_by_telegram_id(user_id)
                username = user.username if user else "N/A"
                
                formatted_withdrawals.append({
                    "id": withdrawal.get("id"),
                    "user": username,
                    "amount": withdrawal.get("amount"),
                    "final_amount": withdrawal.get("final_amount", withdrawal.get("amount")),
                    "upi_id": withdrawal.get("upi_id"),
                    "date": withdrawal.get("created_at"),
                    "status": withdrawal.get("status")
                })
            
            return jsonify({"withdrawals": formatted_withdrawals})
        else:
            logger.info("Retrieved 0 withdrawals")
            return jsonify({"withdrawals": []})
    except Exception as e:
        logger.error(f"Error in get_withdrawals: {str(e)}")
        return jsonify({"withdrawals": []})

@admin_bp.route('/api/admin/stats')
@login_required
def get_stats():
    try:
        # Get all users
        users = User.get_all_users()
        
        # Calculate stats
        total_users = len(users)
        total_coins = sum(user.coins for user in users)
        
        # Calculate active users (last 24 hours)
        current_time = int(time.time())
        active_users = sum(1 for user in users if user.last_energy_update and current_time - user.last_energy_update < 86400)
        
        # Get all withdrawals
        try:
            withdrawals_response = supabase.table("withdrawals").select("*").execute()
            withdrawals = withdrawals_response.data if withdrawals_response.data else []
        except Exception as e:
            logger.error(f"Error getting withdrawals: {str(e)}")
            withdrawals = []
        
        total_withdrawals = len(withdrawals)
        pending_withdrawals = sum(1 for w in withdrawals if w.get("status") == "pending")
        total_withdrawn = sum(w.get("amount", 0) for w in withdrawals)
        
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
        logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({
            "total_users": 0,
            "active_users": 0,
            "total_coins": 0,
            "total_withdrawals": 0,
            "pending_withdrawals": 0,
            "total_withdrawn": 0
        })

@admin_bp.route('/api/admin/approve_withdrawal', methods=['POST'])
@login_required
def approve_withdrawal():
    try:
        # Get withdrawal ID from request
        data = request.json
        withdrawal_id = data.get('id')
        
        if not withdrawal_id:
            return jsonify({"error": "Withdrawal ID is required"}), 400
        
        # Update withdrawal status
        response = supabase.table("withdrawals").update({"status": "approved"}).eq("id", withdrawal_id).execute()
        
        if response.data:
            return jsonify({"success": True, "message": "Withdrawal approved successfully"})
        else:
            return jsonify({"error": "Withdrawal not found"}), 404
    except Exception as e:
        logger.error(f"Error in approve_withdrawal: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/admin/reject_withdrawal', methods=['POST'])
@login_required
def reject_withdrawal():
    try:
        # Get withdrawal ID from request
        data = request.json
        withdrawal_id = data.get('id')
        
        if not withdrawal_id:
            return jsonify({"error": "Withdrawal ID is required"}), 400
        
        # Get withdrawal info
        withdrawal_response = supabase.table("withdrawals").select("*").eq("id", withdrawal_id).execute()
        
        if not withdrawal_response.data or len(withdrawal_response.data) == 0:
            return jsonify({"error": "Withdrawal not found"}), 404
        
        withdrawal = withdrawal_response.data[0]
        user_id = withdrawal.get("user_id")
        amount = withdrawal.get("amount")
        
        # Get user
        user = User.get_by_telegram_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Refund coins to user
        user.coins += amount
        user.save()
        
        # Update withdrawal status
        response = supabase.table("withdrawals").update({"status": "rejected"}).eq("id", withdrawal_id).execute()
        
        if response.data:
            return jsonify({
                "success": True,
                "message": "Withdrawal rejected and coins refunded successfully"
            })
        else:
            return jsonify({"error": "Failed to update withdrawal status"}), 500
    except Exception as e:
        logger.error(f"Error in reject_withdrawal: {str(e)}")
        return jsonify({"error": str(e)}), 500


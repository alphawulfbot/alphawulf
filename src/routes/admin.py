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

admin_bp = Blueprint("admin", __name__)

# Admin credentials - should be stored securely in environment variables
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "alphawulf2025")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_logged_in" not in session or not session["admin_logged_in"]:
            return redirect(url_for("admin.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("admin.admin_dashboard"))
        else:
            flash("Invalid username or password")
    
    return render_template("login.html")

@admin_bp.route("/admin/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))

@admin_bp.route("/admin")
@login_required
def admin_dashboard():
    return render_template("admin.html")

@admin_bp.route("/api/admin/users")
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

@admin_bp.route("/api/admin/withdrawals")
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

@admin_bp.route("/api/admin/stats")
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
        active_users = sum(1 for user in users if user.get("last_energy_update") and current_time - user.get("last_energy_update") < 86400)
        
        # Total coins across all users
        total_coins = sum(user.get("coins", 0) for user in users)
        
        # Total withdrawals
        total_withdrawals = len(withdrawals)
        
        # Pending withdrawals
        pending_withdrawals = sum(1 for withdrawal in withdrawals if withdrawal.get("status") == "pending")
        
        # Total withdrawn amount
        total_withdrawn = sum(withdrawal.get("amount", 0) for withdrawal in withdrawals if withdrawal.get("status") == "completed")
        
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

@admin_bp.route("/api/admin/approve_withdrawal/<withdrawal_id>", methods=["POST"])
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

@admin_bp.route("/api/admin/reject_withdrawal/<withdrawal_id>", methods=["POST"])
@login_required
def reject_withdrawal(withdrawal_id):
    try:
        # Get withdrawal details
        withdrawal_response = supabase.table("withdrawals").select("*").eq("id", withdrawal_id).execute()
        
        if not withdrawal_response.data or len(withdrawal_response.data) == 0:
            return jsonify({"success": False, "message": "Withdrawal not found"}), 404
        
        withdrawal = withdrawal_response.data[0]
        telegram_id = withdrawal.get("telegram_id")
        amount = withdrawal.get("amount")
        
        # Update withdrawal status to rejected
        update_response = supabase.table("withdrawals").update({"status": "rejected"}).eq("id", withdrawal_id).execute()
        
        if not update_response.data or len(update_response.data) == 0:
            return jsonify({"success": False, "message": "Failed to update withdrawal status"}), 500
        
        # Refund coins to user
        user_response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        
        if not user_response.data or len(user_response.data) == 0:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        user = user_response.data[0]
        current_coins = user.get("coins", 0)
        
        # Update user coins
        user_update_response = supabase.table("users").update({"coins": current_coins + amount}).eq("telegram_id", telegram_id).execute()
        
        if not user_update_response.data or len(user_update_response.data) == 0:
            return jsonify({"success": False, "message": "Failed to refund coins to user"}), 500
        
        return jsonify({"success": True, "message": "Withdrawal rejected and coins refunded"})
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route("/api/admin/adjust_coins", methods=["POST"])
@login_required
def adjust_coins():
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        amount = data.get("amount")
        
        if not telegram_id or amount is None:
            return jsonify({"success": False, "message": "Telegram ID and amount are required"}), 400
        
        # Get user
        user_response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        
        if not user_response.data or len(user_response.data) == 0:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        user = user_response.data[0]
        current_coins = user.get("coins", 0)
        new_coins = max(0, current_coins + int(amount))  # Ensure coins don't go negative
        
        # Update user coins
        update_response = supabase.table("users").update({"coins": new_coins}).eq("telegram_id", telegram_id).execute()
        
        if update_response.data and len(update_response.data) > 0:
            return jsonify({"success": True, "message": f"Coins adjusted by {amount}. New balance: {new_coins}"})
        else:
            return jsonify({"success": False, "message": "Failed to update coins"}), 500
    except Exception as e:
        logger.error(f"Error adjusting coins: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route("/api/admin/reset_user", methods=["POST"])
@login_required
def reset_user():
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        
        if not telegram_id:
            return jsonify({"success": False, "message": "Telegram ID is required"}), 400
        
        # Reset user data to defaults
        reset_data = {
            "coins": 0,
            "energy": 100,
            "max_energy": 100,
            "tap_power": 1,
            "energy_regen_rate": 1,
            "last_energy_update": int(time.time()),
            "referral_count": 0,
            "referral_earnings": 0,
            "upi_id": None
        }
        
        # Update user
        update_response = supabase.table("users").update(reset_data).eq("telegram_id", telegram_id).execute()
        
        if update_response.data and len(update_response.data) > 0:
            return jsonify({"success": True, "message": "User data reset successfully"})
        else:
            return jsonify({"success": False, "message": "User not found or failed to reset"}), 404
    except Exception as e:
        logger.error(f"Error resetting user: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route("/api/admin/delete_user", methods=["POST"])
@login_required
def delete_user():
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        
        if not telegram_id:
            return jsonify({"success": False, "message": "Telegram ID is required"}), 400
        
        # Delete user from database
        delete_response = supabase.table("users").delete().eq("telegram_id", telegram_id).execute()
        
        if delete_response.data and len(delete_response.data) > 0:
            # Also delete related data
            try:
                supabase.table("withdrawals").delete().eq("telegram_id", telegram_id).execute()
                supabase.table("referred_users").delete().eq("user_id", telegram_id).execute()
                supabase.table("referred_users").delete().eq("referrer_id", telegram_id).execute()
            except Exception as e:
                logger.warning(f"Error deleting related data for user {telegram_id}: {str(e)}")
            
            return jsonify({"success": True, "message": "User deleted successfully"})
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route("/api/admin/referred_users/<telegram_id>")
@login_required
def get_referred_users(telegram_id):
    try:
        # Get referred users for this user
        response = supabase.table("referred_users").select("*").eq("referrer_id", telegram_id).execute()
        
        if response.data:
            referred_users = response.data
            return jsonify({"referred_users": referred_users})
        else:
            return jsonify({"referred_users": []})
    except Exception as e:
        logger.error(f"Error retrieving referred users: {str(e)}")
        return jsonify({"referred_users": [], "error": str(e)}), 500


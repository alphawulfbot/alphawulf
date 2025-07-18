from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from src.config.database import supabase
from src.models.user import User
import logging
import hashlib
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)

# Admin credentials (in production, use environment variables)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"  # "admin123"

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_admin_auth():
    """Check if user is authenticated as admin"""
    return session.get('admin_authenticated', False)

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH:
            session['admin_authenticated'] = True
            logger.info("Admin logged in successfully")
            return redirect(url_for('admin.admin_dashboard'))
        else:
            logger.warning(f"Failed admin login attempt for username: {username}")
            return render_template("login.html", error="Invalid credentials")
    
    return render_template("login.html")

@admin_bp.route("/admin/logout")
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    logger.info("Admin logged out")
    return redirect(url_for('admin.admin_login'))

@admin_bp.route("/admin")
def admin_dashboard():
    """Admin dashboard"""
    if not check_admin_auth():
        return redirect(url_for('admin.admin_login'))
    
    return render_template("admin.html")

@admin_bp.route("/api/admin/users", methods=["GET"])
def get_users():
    """Get all users for admin dashboard with enhanced data fetching"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        logger.info("Fetching all users for admin dashboard")
        
        # Fetch all users from database with comprehensive data
        response = supabase.table("users").select("*").order("created_at", desc=True).execute()
        
        if response.data:
            users = []
            for user_data in response.data:
                try:
                    # Ensure all fields are properly formatted with safe conversion
                    user = {
                        "telegram_id": str(user_data.get("telegram_id", "")),
                        "username": user_data.get("username") or "N/A",
                        "first_name": user_data.get("first_name") or "User",
                        "coins": int(float(str(user_data.get("coins", 0)))),
                        "energy": float(str(user_data.get("energy", 0))),
                        "max_energy": int(float(str(user_data.get("max_energy", 100)))),
                        "tap_power": int(float(str(user_data.get("tap_power", 1)))),
                        "energy_regen_rate": int(float(str(user_data.get("energy_regen_rate", 1)))),
                        "referral_count": int(float(str(user_data.get("referral_count", 0)))),
                        "referral_earnings": int(float(str(user_data.get("referral_earnings", 0)))),
                        "last_active": user_data.get("last_energy_update") or user_data.get("created_at") or "N/A",
                        "upi_id": user_data.get("upi_id") or "N/A",
                        "created_at": user_data.get("created_at") or "N/A",
                        "referred_by": user_data.get("referred_by") or "N/A"
                    }
                    
                    # Format last active time
                    if user["last_active"] != "N/A":
                        try:
                            if isinstance(user["last_active"], (int, float)):
                                last_active_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(user["last_active"]))
                            else:
                                last_active_time = str(user["last_active"])[:19]  # Truncate to datetime format
                            user["last_active"] = last_active_time
                        except:
                            user["last_active"] = "N/A"
                    
                    users.append(user)
                    
                except Exception as e:
                    logger.error(f"Error processing user data for {user_data.get('telegram_id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(users)} users for admin dashboard")
            return jsonify(users)
        else:
            logger.warning("No users found in database")
            return jsonify([])
            
    except Exception as e:
        logger.error(f"Error fetching users for admin dashboard: {str(e)}")
        return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500

@admin_bp.route("/api/admin/withdrawals", methods=["GET"])
def get_withdrawals():
    """Get all withdrawal requests for admin dashboard with enhanced data fetching"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        logger.info("Fetching all withdrawals for admin dashboard")
        
        # Fetch all withdrawals from database
        response = supabase.table("withdrawals").select("*").order("created_at", desc=True).execute()
        
        if response.data:
            withdrawals = []
            for withdrawal_data in response.data:
                try:
                    # Get user details for this withdrawal
                    user_response = supabase.table("users").select("username, first_name").eq("telegram_id", withdrawal_data.get("telegram_id")).execute()
                    user_info = user_response.data[0] if user_response.data else {}
                    
                    # Ensure all fields are properly formatted
                    withdrawal = {
                        "id": withdrawal_data.get("id"),
                        "telegram_id": str(withdrawal_data.get("telegram_id", "")),
                        "username": user_info.get("username") or "N/A",
                        "first_name": user_info.get("first_name") or "User",
                        "amount": int(float(str(withdrawal_data.get("amount", 0)))),
                        "final_amount": float(str(withdrawal_data.get("final_amount", 0))),
                        "rupee_amount": float(str(withdrawal_data.get("rupee_amount", 0))),
                        "upi_id": withdrawal_data.get("upi_id") or "N/A",
                        "status": withdrawal_data.get("status", "pending"),
                        "created_at": withdrawal_data.get("created_at"),
                        "processed_at": withdrawal_data.get("processed_at")
                    }
                    
                    # Format dates
                    if withdrawal["created_at"]:
                        try:
                            if isinstance(withdrawal["created_at"], (int, float)):
                                withdrawal["created_at"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(withdrawal["created_at"]))
                            else:
                                withdrawal["created_at"] = str(withdrawal["created_at"])[:19]
                        except:
                            withdrawal["created_at"] = "N/A"
                    
                    if withdrawal["processed_at"]:
                        try:
                            if isinstance(withdrawal["processed_at"], (int, float)):
                                withdrawal["processed_at"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(withdrawal["processed_at"]))
                            else:
                                withdrawal["processed_at"] = str(withdrawal["processed_at"])[:19]
                        except:
                            withdrawal["processed_at"] = "N/A"
                    
                    withdrawals.append(withdrawal)
                    
                except Exception as e:
                    logger.error(f"Error processing withdrawal data for ID {withdrawal_data.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(withdrawals)} withdrawals for admin dashboard")
            return jsonify(withdrawals)
        else:
            logger.warning("No withdrawals found in database")
            return jsonify([])
            
    except Exception as e:
        logger.error(f"Error fetching withdrawals for admin dashboard: {str(e)}")
        return jsonify({"error": f"Failed to fetch withdrawals: {str(e)}"}), 500

@admin_bp.route("/api/admin/user/<telegram_id>/coins", methods=["POST"])
def adjust_user_coins(telegram_id):
    """Adjust user coins with enhanced validation"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.json
        action = data.get("action")  # "add" or "set"
        amount = int(float(str(data.get("amount", 0))))
        
        logger.info(f"Admin adjusting coins for user {telegram_id}: {action} {amount}")
        
        if action not in ["add", "set"]:
            return jsonify({"error": "Invalid action. Use 'add' or 'set'"}), 400
        
        if amount < 0 and action == "set":
            return jsonify({"error": "Cannot set negative coins"}), 400
        
        # Get user using User model for better data handling
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        old_coins = user.coins
        
        if action == "add":
            user.coins = max(0, user.coins + amount)  # Ensure coins don't go negative
        else:  # set
            user.coins = amount
        
        # Save user data
        if user.save():
            logger.info(f"Admin successfully adjusted coins for user {telegram_id}: {old_coins} -> {user.coins}")
            return jsonify({
                "success": True,
                "message": f"Coins updated successfully",
                "old_coins": old_coins,
                "new_coins": user.coins
            })
        else:
            logger.error(f"Failed to save coin adjustment for user {telegram_id}")
            return jsonify({"error": "Failed to update coins"}), 500
            
    except Exception as e:
        logger.error(f"Error adjusting coins for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/admin/user/<telegram_id>/reset", methods=["POST"])
def reset_user_data(telegram_id):
    """Reset user data to default values with enhanced handling"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        logger.info(f"Admin resetting data for user {telegram_id}")
        
        # Get user using User model
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Reset user to default values
        user.coins = 2500  # Default bonus
        user.energy = 100
        user.max_energy = 100
        user.tap_power = 1
        user.energy_regen_rate = 1
        user.referral_count = 0
        user.referral_earnings = 0
        user.last_energy_update = int(time.time())
        
        if user.save():
            logger.info(f"Admin successfully reset data for user {telegram_id}")
            return jsonify({
                "success": True,
                "message": "User data reset successfully"
            })
        else:
            logger.error(f"Failed to reset data for user {telegram_id}")
            return jsonify({"error": "Failed to reset user data"}), 500
            
    except Exception as e:
        logger.error(f"Error resetting data for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/admin/user/<telegram_id>/delete", methods=["DELETE"])
def delete_user(telegram_id):
    """Delete user from database with enhanced cleanup"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        logger.info(f"Admin deleting user {telegram_id}")
        
        # Delete user from users table
        user_response = supabase.table("users").delete().eq("telegram_id", telegram_id).execute()
        
        # Also delete related data
        try:
            # Delete withdrawals
            supabase.table("withdrawals").delete().eq("telegram_id", telegram_id).execute()
            
            # Delete referrals (both as referrer and referred)
            supabase.table("referrals").delete().eq("referrer_id", telegram_id).execute()
            supabase.table("referrals").delete().eq("referred_id", telegram_id).execute()
            
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup for user {telegram_id}: {str(cleanup_error)}")
        
        if user_response.data:
            logger.info(f"Admin successfully deleted user {telegram_id}")
            return jsonify({
                "success": True,
                "message": "User deleted successfully"
            })
        else:
            logger.warning(f"User {telegram_id} not found for deletion")
            return jsonify({"error": "User not found or already deleted"}), 404
            
    except Exception as e:
        logger.error(f"Error deleting user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/admin/withdrawal/<int:withdrawal_id>/status", methods=["POST"])
def update_withdrawal_status(withdrawal_id):
    """Update withdrawal status with enhanced validation"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.json
        new_status = data.get("status")
        
        logger.info(f"Admin updating withdrawal {withdrawal_id} status to {new_status}")
        
        if new_status not in ["pending", "approved", "rejected", "completed"]:
            return jsonify({"error": "Invalid status"}), 400
        
        # Update withdrawal status
        update_data = {"status": new_status}
        if new_status in ["approved", "rejected", "completed"]:
            update_data["processed_at"] = int(time.time())
        
        response = supabase.table("withdrawals").update(update_data).eq("id", withdrawal_id).execute()
        
        if response.data:
            logger.info(f"Admin successfully updated withdrawal {withdrawal_id} status to {new_status}")
            return jsonify({
                "success": True,
                "message": f"Withdrawal status updated to {new_status}"
            })
        else:
            logger.error(f"Failed to update withdrawal {withdrawal_id} status")
            return jsonify({"error": "Failed to update withdrawal status or withdrawal not found"}), 404
            
    except Exception as e:
        logger.error(f"Error updating withdrawal {withdrawal_id} status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/admin/stats", methods=["GET"])
def get_admin_stats():
    """Get admin dashboard statistics with enhanced data"""
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        logger.info("Fetching admin dashboard statistics")
        
        # Get user count
        users_response = supabase.table("users").select("id", count="exact").execute()
        user_count = users_response.count if users_response.count else 0
        
        # Get total coins in circulation
        coins_response = supabase.table("users").select("coins").execute()
        total_coins = 0
        if coins_response.data:
            for user in coins_response.data:
                try:
                    total_coins += int(float(str(user.get("coins", 0))))
                except:
                    continue
        
        # Get withdrawal statistics
        withdrawals_response = supabase.table("withdrawals").select("id, status, final_amount", count="exact").execute()
        withdrawal_count = withdrawals_response.count if withdrawals_response.count else 0
        
        # Count pending withdrawals and total withdrawal amount
        pending_withdrawals = 0
        total_withdrawn = 0
        if withdrawals_response.data:
            for withdrawal in withdrawals_response.data:
                if withdrawal.get("status") == "pending":
                    pending_withdrawals += 1
                if withdrawal.get("status") == "completed":
                    try:
                        total_withdrawn += float(str(withdrawal.get("final_amount", 0)))
                    except:
                        continue
        
        # Get referral statistics
        referrals_response = supabase.table("referrals").select("id", count="exact").execute()
        total_referrals = referrals_response.count if referrals_response.count else 0
        
        # Get new users today
        today_start = int(time.time()) - (24 * 60 * 60)  # 24 hours ago
        new_users_response = supabase.table("users").select("id", count="exact").gte("created_at", today_start).execute()
        new_users_today = new_users_response.count if new_users_response.count else 0
        
        stats = {
            "total_users": user_count,
            "new_users_today": new_users_today,
            "total_coins": total_coins,
            "total_withdrawals": withdrawal_count,
            "pending_withdrawals": pending_withdrawals,
            "total_withdrawn": round(total_withdrawn, 2),
            "total_referrals": total_referrals
        }
        
        logger.info(f"Admin stats retrieved: {stats}")
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        return jsonify({"error": str(e)}), 500


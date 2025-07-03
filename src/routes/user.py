from flask import Blueprint, request, jsonify
from src.models.user import User
import hashlib
import hmac
import json
from urllib.parse import unquote
from datetime import datetime

user_bp = Blueprint("user", __name__)

def verify_telegram_auth(auth_data, bot_token):
    """Verify Telegram Web App authentication data"""
    try:
        # Parse the auth data
        auth_dict = {}
        for item in auth_data.split("&"):
            key, value = item.split("=", 1)
            auth_dict[key] = unquote(value)
        
        # Extract hash and create data string
        received_hash = auth_dict.pop("hash", "")
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(auth_dict.items())])
        
        # Create secret key
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        
        # Calculate expected hash
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(received_hash, expected_hash)
    except Exception as e:
        print(f"Auth verification error: {e}")
        return False

@user_bp.route("/auth", methods=["POST"])
def authenticate_user():
    """Authenticate user via Telegram Web App data"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        username = data.get("username", "")
        auth_data = data.get("auth_data")
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

        if not verify_telegram_auth(auth_data, bot_token):
            return jsonify({"error": "Authentication failed"}), 401

        user = User.get_by_telegram_id(telegram_id)

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            user.save()

        user.update_energy()
        user.save() # Save any energy updates

        return jsonify({"message": "Authentication successful", "user": user.to_dict()})

    except Exception as e:
        print(f"Authentication error: {e}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/user/<int:telegram_id>", methods=["GET"])
def get_user(telegram_id):
    """Get user data by Telegram ID"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.update_energy()
        user.save()

        return jsonify(user.to_dict())

    except Exception as e:
        print(f"Get user error: {e}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/user/update_coins", methods=["POST"])
def update_user_coins():
    """Update user coins (for testing/admin) - REMOVE IN PRODUCTION"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        amount = data.get("amount")

        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user.coins += amount
        user.save()

        return jsonify({"success": True, "user": user.to_dict()})

    except Exception as e:
        print(f"Update coins error: {e}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/user/update_upi", methods=["POST"])
def update_user_upi():
    """Update user UPI ID"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        upi_id = data.get("upi_id")

        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.upi_id = upi_id
        user.save()
        
        return jsonify({
            "success": True,
            "message": "UPI ID updated successfully"
        })
    
    except Exception as e:
        print(f"UPI update error: {e}")
        return jsonify({"error": str(e)}), 500

@user_bp.route("/transactions/<int:telegram_id>", methods=["GET"])
def get_user_transactions(telegram_id):
    """Get user transaction history"""
    user = User.get_by_telegram_id(telegram_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    transactions = Transaction.get_by_user_id(user.id)
    transactions_data = []
    for tx in transactions:
        transactions_data.append({
            "type": tx.transaction_type,
            "amount": tx.amount,
            "description": tx.description,
            "date": tx.created_at
        })

    return jsonify(transactions_data)

@user_bp.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    """Get top users leaderboard"""
    try:
        # Get all users and sort by total_earned
        all_users = User.get_all_users()
        top_users = sorted(all_users, key=lambda x: x.get("total_earned", 0), reverse=True)[:10]
        
        return jsonify([{
            "rank": idx + 1,
            "name": user.get("first_name") or user.get("username") or f"User{user.get("telegram_id")}",
            "total_earned": user.get("total_earned", 0)
        } for idx, user in enumerate(top_users)])
    
    except Exception as e:
        print(f"Leaderboard error: {e}")
        return jsonify([])

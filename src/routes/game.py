from flask import Blueprint, request, jsonify
from src.models.user import User, Transaction
from datetime import datetime

game_bp = Blueprint("game", __name__)

@game_bp.route("/tap", methods=["POST"])
def handle_tap():
    """Handle tap action"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        taps = data.get("taps", 1)

        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user.update_energy()

        # Check if user has enough energy
        if user.energy < taps:
            return jsonify({"error": "Not enough energy"}), 400

        # Process tap
        success = user.tap(taps)
        if success:
            # Log transaction
            transaction = Transaction(
                user_id=user.id,
                transaction_type="tap",
                amount=taps * user.tap_power,
                description=f"Earned from {taps} taps"
            )
            transaction.save()

            return jsonify({
                "success": True,
                "coins_earned": taps * user.tap_power,
                "user": user.to_dict()
            })
        else:
            return jsonify({"error": "Failed to process tap"}), 500

    except Exception as e:
        print(f"Tap error: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.route("/energy_update", methods=["POST"])
def update_energy():
    """Update user energy"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")

        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user.update_energy()
        user.save() # Save energy update

        return jsonify({
            "success": True,
            "user": user.to_dict()
        })

    except Exception as e:
        print(f"Energy update error: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.route("/leaderboard", methods=["GET"])
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

@game_bp.route("/stats/<int:telegram_id>", methods=["GET"])
def get_user_stats(telegram_id):
    """Get detailed user statistics"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get recent transactions
        recent_transactions = Transaction.get_by_user_id(user.id)

        transactions_data = []
        for tx in recent_transactions:
            transactions_data.append({
                "type": tx.transaction_type,
                "amount": tx.amount,
                "description": tx.description,
                "date": tx.created_at
            })

        return jsonify({
            "user": user.to_dict(),
            "recent_transactions": transactions_data
        })

    except Exception as e:
        print(f"User stats error: {e}")
        return jsonify({"error": str(e)}), 500

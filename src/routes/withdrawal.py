from flask import Blueprint, request, jsonify
from src.models.user import User, Transaction
from datetime import datetime

withdrawal_bp = Blueprint("withdrawal", __name__)

@withdrawal_bp.route("/request", methods=["POST"])
def request_withdrawal():
    """Request withdrawal"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        amount = data.get("amount")
        upi_id = data.get("upi_id")
        
        if not all([telegram_id, amount, upi_id]):
            return jsonify({"error": "Missing required fields"}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check minimum withdrawal amount
        min_withdrawal = 1000
        if amount < min_withdrawal:
            return jsonify({"error": f"Minimum withdrawal amount is {min_withdrawal} coins"}), 400
        
        # Check if user has enough coins
        if user.coins < amount:
            return jsonify({"error": "Insufficient coins"}), 400
        
        # Update user UPI ID
        user.upi_id = upi_id
        user.save()
        
        # Log withdrawal request as a transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type="withdrawal_request",
            amount=-amount, # Negative amount for withdrawal
            description=f"Withdrawal request for {amount} coins to UPI: {upi_id}"
        )
        transaction.save()

        # For now, just return success (withdrawal processing would be handled by admin)
        return jsonify({
            "success": True,
            "message": "Withdrawal request submitted successfully",
            "amount": amount,
            "upi_id": upi_id
        })
    
    except Exception as e:
        print(f"Withdrawal request error: {e}")
        return jsonify({"error": str(e)}), 500

@withdrawal_bp.route("/history/<int:telegram_id>", methods=["GET"])
def get_withdrawal_history(telegram_id):
    """Get user's withdrawal history"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Fetch withdrawal transactions
        withdrawal_transactions = Transaction.get_by_user_id(user.id)
        history = [
            {
                "amount": abs(tx.amount),
                "date": tx.created_at,
                "status": "pending" # Assuming all are pending for now
            }
            for tx in withdrawal_transactions if tx.transaction_type == "withdrawal_request"
        ]
        
        return jsonify(history)
    
    except Exception as e:
        print(f"Get withdrawal history error: {e}")
        return jsonify({"error": str(e)}), 500

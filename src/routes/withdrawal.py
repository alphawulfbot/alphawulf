from flask import Blueprint, request, jsonify
from src.models.user import User
from src.config.database import supabase
import logging
import time
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

withdraw_bp = Blueprint("withdraw", __name__)

@withdraw_bp.route("/api/withdraw", methods=["POST"])
def withdraw():
    try:
        # Get withdrawal data from request
        data = request.json
        telegram_id = data.get("telegram_id")
        amount = data.get("amount")
        upi_id = data.get("upi_id")
        
        if not telegram_id or not amount or not upi_id:
            return jsonify({"error": "Telegram ID, amount, and UPI ID are required"}), 400
        
        # Convert amount to integer
        try:
            amount = int(amount)
        except ValueError:
            return jsonify({"error": "Amount must be a number"}), 400
        
        # Check if amount is valid
        if amount < 1000:
            return jsonify({"error": "Minimum withdrawal amount is 1,000 coins"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user has enough coins
        if user.coins < amount:
            return jsonify({
                "success": False,
                "message": "Not enough coins",
                "coins": user.coins
            })
        
        # Calculate fee (2%)
        fee = int(amount * 0.02)
        final_amount = amount - fee
        
        # Convert coins to INR (1000 coins = ₹10)
        rupee_amount = (final_amount / 1000) * 10
        
        # Update user coins
        user.coins -= amount
        user.save()
        
        # Create withdrawal record
        withdrawal_id = str(uuid.uuid4())
        withdrawal_data = {
            "id": withdrawal_id,
            "telegram_id": telegram_id,
            "amount": amount,
            "rupee_amount": rupee_amount,
            "fee": fee,
            "final_amount": final_amount,
            "upi_id": upi_id,
            "status": "pending",
            "created_at": int(time.time())
        }
        
        try:
            response = supabase.table("withdrawals").insert(withdrawal_data).execute()
            if not response.data:
                logger.error(f"Supabase insert response data empty: {response}")
                raise Exception("Failed to create withdrawal record in Supabase.")
        except Exception as e:
            logger.error(f"Error creating withdrawal record: {str(e)}")
            # If withdrawal record creation fails, log and proceed, but inform user
            return jsonify({
                "success": True,
                "message": "Withdrawal processed, but record not saved. Contact support.",
                "coins": user.coins,
                "amount": amount,
                "fee": fee,
                "final_amount": final_amount,
                "rupee_amount": rupee_amount
            })
        
        # Return success message
        return jsonify({
            "success": True,
            "message": "Withdrawal processed successfully",
            "coins": user.coins,
            "amount": amount,
            "fee": fee,
            "final_amount": final_amount,
            "rupee_amount": rupee_amount
        })
    except Exception as e:
        logger.error(f"Error in withdraw: {str(e)}")
        return jsonify({"error": str(e)}), 500

@withdraw_bp.route("/api/withdrawal_history/<telegram_id>", methods=["GET"])
def withdrawal_history(telegram_id):
    try:
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get withdrawal history from database
        response = supabase.table("withdrawals").select("*").eq("telegram_id", telegram_id).order("created_at", desc=True).execute()
        
        if response.data:
            withdrawals = response.data
            return jsonify({"withdrawals": withdrawals})
        else:
            return jsonify({"withdrawals": []})
    except Exception as e:
        logger.error(f"Error in withdrawal_history: {str(e)}")
        return jsonify({"error": str(e)}), 500



from flask import Blueprint, request, jsonify
from src.config.database import supabase
from src.models.user import User
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

withdraw_bp = Blueprint("withdraw", __name__)

@withdraw_bp.route("/api/withdraw", methods=["POST"])
def request_withdrawal():
    """Handle withdrawal request"""
    try:
        data = request.json
        telegram_id = str(data.get("telegram_id", "")).strip()
        amount = data.get("amount")  # Coins to withdraw
        upi_id = data.get("upi_id")
        
        logger.info(f"Withdrawal request for user {telegram_id}: amount={amount}, upi_id={upi_id}")
        
        if not telegram_id or not amount or not upi_id:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Ensure amount is a valid number and convert to float for calculations
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"error": "Withdrawal amount must be positive"}), 400
        except ValueError:
            return jsonify({"error": "Invalid amount format"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user has enough coins
        if user.coins < amount:
            return jsonify({"error": "Insufficient coins"}), 400
        
        # Calculate processing fee (2%)
        processing_fee = amount * 0.02
        final_amount = amount - processing_fee
        
        # Convert coins to rupees (assuming 1000 coins = 10 rupees)
        rupee_amount = final_amount / 100
        
        # Deduct coins from user balance
        user.coins -= amount
        if not user.save():
            logger.error(f"Failed to deduct coins for withdrawal for user {telegram_id}")
            return jsonify({"error": "Failed to process withdrawal"}), 500
        
        # Record withdrawal in database
        withdrawal_data = {
            "telegram_id": telegram_id,
            "amount": amount,
            "final_amount": final_amount,
            "rupee_amount": rupee_amount,
            "upi_id": upi_id,
            "status": "pending",
            "created_at": int(time.time())
        }
        
        response = supabase.table("withdrawals").insert(withdrawal_data).execute()
        
        if response.data:
            logger.info(f"Withdrawal request successful for user {telegram_id}, ID: {response.data[0].get("id")}")
            return jsonify({
                "success": True,
                "message": "Withdrawal request submitted successfully",
                "withdrawal_id": response.data[0].get("id"),
                "new_balance": user.coins
            })
        else:
            logger.error(f"Failed to record withdrawal in database for user {telegram_id}")
            return jsonify({"error": "Failed to record withdrawal"}), 500
            
    except Exception as e:
        logger.error(f"Error processing withdrawal request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@withdraw_bp.route("/api/withdrawals/<telegram_id>", methods=["GET"])
def get_withdrawals(telegram_id):
    """Get withdrawal history for a user"""
    try:
        telegram_id = str(telegram_id).strip()
        logger.info(f"Fetching withdrawal history for user: {telegram_id}")
        
        if not telegram_id:
            return jsonify({"error": "Missing telegram ID"}), 400
        
        response = supabase.table("withdrawals").select("*").eq("telegram_id", telegram_id).order("created_at", desc=True).execute()
        
        if response.data:
            withdrawals = []
            for withdrawal_data in response.data:
                # Ensure all fields are properly formatted
                withdrawal = {
                    "id": withdrawal_data.get("id"),
                    "telegram_id": str(withdrawal_data.get("telegram_id", "")),
                    "amount": float(str(withdrawal_data.get("amount", 0))),
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
                            withdrawal["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(withdrawal["created_at"]))
                        else:
                            withdrawal["created_at"] = str(withdrawal["created_at"])[:19]
                    except:
                        withdrawal["created_at"] = "N/A"
                
                if withdrawal["processed_at"]:
                    try:
                        if isinstance(withdrawal["processed_at"], (int, float)):
                            withdrawal["processed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(withdrawal["processed_at"]))
                        else:
                            withdrawal["processed_at"] = str(withdrawal["processed_at"])[:19]
                    except:
                        withdrawal["processed_at"] = "N/A"
                
                withdrawals.append(withdrawal)
            
            logger.info(f"Retrieved {len(withdrawals)} withdrawals for user {telegram_id}")
            return jsonify(withdrawals)
        else:
            logger.info(f"No withdrawal history found for user: {telegram_id}")
            return jsonify([])
            
    except Exception as e:
        logger.error(f"Error fetching withdrawal history for user {telegram_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


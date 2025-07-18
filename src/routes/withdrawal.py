from flask import Blueprint, request, jsonify
from src.models.user import User
from src.config.database import supabase
import logging
import time

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
        
        if not telegram_id or amount is None or not upi_id:
            return jsonify({"error": "Telegram ID, amount, and UPI ID are required"}), 400
        
        # Convert amount to float first, then to integer for calculations
        try:
            amount = float(amount)
            # Ensure amount is a whole number for coin deduction, if it's meant to be integer coins
            # If coins can be fractional, adjust this. Assuming coins are integer.
            amount_int = int(amount)
        except ValueError:
            return jsonify({"error": "Amount must be a valid number"}), 400
        
        # Check if amount is valid
        if amount_int < 1000:
            return jsonify({"error": "Minimum withdrawal amount is 1,000 coins"}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user has enough coins
        if user.coins < amount_int:
            return jsonify({
                "success": False,
                "message": "Not enough coins",
                "coins": user.coins
            })
        
        # Calculate fee (2%)
        fee = int(amount_int * 0.02)
        final_amount = amount_int - fee
        
        # Convert coins to INR (1000 coins = ₹10)
        inr_amount = (final_amount / 1000) * 10
        
        # Update user coins
        user.coins -= amount_int
        user.save()
        
        # Create withdrawal record
        try:
            withdrawal_data = {
                "user_id": telegram_id,
                "amount": amount_int,
                "final_amount": final_amount,
                "fee": fee,
                "inr_amount": inr_amount,
                "upi_id": upi_id,
                "status": "pending",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Insert withdrawal record
            response = supabase.table("withdrawals").insert(withdrawal_data).execute()
            
            if not response.data:
                logger.warning(f"Failed to insert full withdrawal record. Trying without fee: {withdrawal_data}")
                # If the insert fails due to missing 'fee' column, try without it
                withdrawal_data_alt = {
                    "user_id": telegram_id,
                    "amount": amount_int,
                    "final_amount": final_amount,
                    "inr_amount": inr_amount,
                    "upi_id": upi_id,
                    "status": "pending",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                response = supabase.table("withdrawals").insert(withdrawal_data_alt).execute()

        except Exception as e:
            logger.error(f"Error creating withdrawal record: {str(e)}")
            # If that also fails, try with minimal fields
            try:
                withdrawal_data_min = {
                    "user_id": telegram_id,
                    "amount": amount_int,
                    "upi_id": upi_id,
                    "status": "pending",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                response = supabase.table("withdrawals").insert(withdrawal_data_min).execute()
            except Exception as e2:
                logger.error(f"Error creating minimal withdrawal record: {str(e2)}")
                # Return success even if withdrawal record creation fails
                # The coins have been deducted, so the withdrawal is technically processed
                return jsonify({
                    "success": True,
                    "message": "Withdrawal processed successfully, but record creation failed. Please contact support.",
                    "coins": user.coins,
                    "amount": amount_int,
                    "fee": fee,
                    "final_amount": final_amount,
                    "inr_amount": inr_amount
                })
        
        # Return success message
        return jsonify({
            "success": True,
            "message": "Withdrawal processed successfully",
            "coins": user.coins,
            "amount": amount_int,
            "fee": fee,
            "final_amount": final_amount,
            "inr_amount": inr_amount
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
        response = supabase.table("withdrawals").select("*").eq("user_id", telegram_id).order("created_at", desc=True).execute()
        
        if response.data:
            withdrawals = response.data
            return jsonify({"withdrawals": withdrawals})
        else:
            return jsonify({"withdrawals": []})
    except Exception as e:
        logger.error(f"Error in withdrawal_history: {str(e)}")
        return jsonify({"error": str(e)}), 500




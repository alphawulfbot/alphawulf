from flask import Blueprint, request, jsonify
from src.models.user import User, Transaction
from datetime import datetime

referrals_bp = Blueprint("referrals", __name__)

@referrals_bp.route("/info/<int:telegram_id>", methods=["GET"])
def get_referral_info(telegram_id):
    """Get user's referral information"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "referral_code": user.referral_code,
            "referral_count": user.referral_count,
            "referral_earnings": user.referral_earnings,
            "referral_level": user.referral_level
        })
    
    except Exception as e:
        print(f"Get referral info error: {e}")
        return jsonify({"error": str(e)}), 500

@referrals_bp.route("/use_code", methods=["POST"])
def use_referral_code():
    """Use a referral code"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        referral_code = data.get("referral_code")
        
        if not all([telegram_id, referral_code]):
            return jsonify({"error": "Missing required fields"}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user already used a referral code
        if user.referred_by:
            return jsonify({"error": "You have already used a referral code"}), 400
        
        # Find referrer
        referrer = User.query.filter_by(referral_code=referral_code).first()
        if not referrer:
            return jsonify({"error": "Invalid referral code"}), 400
        
        # Prevent self-referral
        if referrer.telegram_id == telegram_id:
            return jsonify({"error": "Cannot refer yourself"}), 400
        
        # Apply referral
        user.referred_by = referrer.telegram_id
        user.save()
        
        # Reward referrer
        referrer.referral_count += 1
        referral_bonus = 500 # Example bonus
        referrer.coins += referral_bonus
        referrer.referral_earnings += referral_bonus
        referrer.save()
        
        # Log transactions
        user_transaction = Transaction(
            user_id=user.id,
            transaction_type="referral_used",
            amount=0, # No direct coins for user using code
            description=f"Used referral code from {referrer.username or referrer.telegram_id}"
        )
        user_transaction.save()

        referrer_transaction = Transaction(
            user_id=referrer.id,
            transaction_type="referral_bonus",
            amount=referral_bonus,
            description=f"Earned from referral of {user.username or user.telegram_id}"
        )
        referrer_transaction.save()
        
        return jsonify({
            "success": True,
            "message": "Referral code applied successfully",
            "user": user.to_dict(),
            "referrer": referrer.to_dict()
        })
    
    except Exception as e:
        print(f"Use referral code error: {e}")
        return jsonify({"error": str(e)}), 500

@referrals_bp.route("/process_referral", methods=["POST"])
def process_referral():
    """Internal endpoint to process referral bonuses (called by bot) - REMOVE IN PRODUCTION"""
    try:
        data = request.json
        referrer_telegram_id = data.get("referrer_telegram_id")
        referred_telegram_id = data.get("referred_telegram_id")

        referrer = User.get_by_telegram_id(referrer_telegram_id)
        referred_user = User.get_by_telegram_id(referred_telegram_id)

        if not referrer or not referred_user:
            return jsonify({"error": "Referrer or referred user not found"}), 404

        # Check if referral already processed
        if referred_user.referred_by:
            return jsonify({"message": "Referral already processed"}), 200

        # Apply referral
        referred_user.referred_by = referrer.telegram_id
        referred_user.save()

        # Reward referrer
        referrer.referral_count += 1
        referral_bonus = 500 # Example bonus
        referrer.coins += referral_bonus
        referrer.referral_earnings += referral_bonus
        referrer.save()

        # Log transactions
        user_transaction = Transaction(
            user_id=referred_user.id,
            transaction_type="referral_used",
            amount=0, # No direct coins for user using code
            description=f"Used referral code from {referrer.username or referrer.telegram_id}"
        )
        user_transaction.save()

        referrer_transaction = Transaction(
            user_id=referrer.id,
            transaction_type="referral_bonus",
            amount=referral_bonus,
            description=f"Earned from referral of {referred_user.username or referred_user.telegram_id}"
        )
        referrer_transaction.save()

        return jsonify({"success": True, "message": "Referral processed successfully"})

    except Exception as e:
        print(f"Process referral error: {e}")
        return jsonify({"error": str(e)}), 500

from flask import Blueprint, request, jsonify
from src.models.user import User
import time
import uuid

withdraw_bp = Blueprint('withdraw', __name__)

@withdraw_bp.route('/api/withdraw', methods=['POST'])
def withdraw():
    """
    Handle withdrawal requests
    """
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        upi_id = data.get('upi_id')
        
        if not telegram_id or not amount or not upi_id:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Validate amount
        if amount < 1000:
            return jsonify({'error': 'Minimum withdrawal amount is 1,000 coins'}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has enough coins
        if user.coins < amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Calculate final amount (after fees)
        rupee_amount = amount / 100  # 100 coins = 1 rupee
        fee = rupee_amount * 0.02  # 2% fee
        final_amount = rupee_amount - fee
        
        # Create withdrawal record
        withdrawal_id = str(uuid.uuid4())
        withdrawal = {
            'id': withdrawal_id,
            'telegram_id': telegram_id,
            'amount': amount,
            'rupee_amount': rupee_amount,
            'fee': fee,
            'final_amount': final_amount,
            'upi_id': upi_id,
            'status': 'pending',
            'created_at': int(time.time())
        }
        
        # Save withdrawal to database
        from src.config.database import supabase
        supabase.table('withdrawals').insert(withdrawal).execute()
        
        # Update user's balance
        user.coins -= amount
        
        # Save UPI ID for future withdrawals
        user.upi_id = upi_id
        
        # Save user
        user.save()
        
        return jsonify({
            'success': True,
            'withdrawal_id': withdrawal_id,
            'amount': amount,
            'rupee_amount': rupee_amount,
            'fee': fee,
            'final_amount': final_amount,
            'user': user.to_dict()
        })
        
    except Exception as e:
        print(f"Error in withdraw: {str(e)}")
        return jsonify({'error': str(e)}), 500

@withdraw_bp.route('/api/withdrawal_history/<telegram_id>', methods=['GET'])
def withdrawal_history(telegram_id):
    """
    Get withdrawal history for a user
    """
    try:
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get withdrawals from database
        from src.config.database import supabase
        response = supabase.table('withdrawals').select('*').eq('telegram_id', telegram_id).order('created_at', desc=True).execute()
        
        withdrawals = response.data
        
        return jsonify({
            'success': True,
            'withdrawals': withdrawals
        })
        
    except Exception as e:
        print(f"Error in withdrawal_history: {str(e)}")
        return jsonify({'error': str(e)}), 500


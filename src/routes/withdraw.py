from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging
from src.models.user import User
from src.config.database import supabase

logger = logging.getLogger(__name__)

withdraw_bp = Blueprint('withdraw', __name__)

@withdraw_bp.route('/api/withdraw/info/<int:telegram_id>', methods=['GET'])
def get_withdraw_info(telegram_id):
    """Get withdrawal information for user with real-time data"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get real-time user data
        user_data = user.get_real_time_data()
        
        # Calculate withdrawal info
        min_withdrawal = 1000  # Minimum 1000 coins
        withdrawal_fee = 0.02  # 2% fee
        
        available_amount = user.coins
        can_withdraw = available_amount >= min_withdrawal
        
        if can_withdraw:
            net_amount = available_amount * (1 - withdrawal_fee)
            fee_amount = available_amount * withdrawal_fee
        else:
            net_amount = 0
            fee_amount = 0
        
        withdraw_info = {
            'user': user_data,
            'available_coins': available_amount,
            'min_withdrawal': min_withdrawal,
            'can_withdraw': can_withdraw,
            'withdrawal_fee_percent': withdrawal_fee * 100,
            'fee_amount': int(fee_amount),
            'net_amount': int(net_amount),
            'conversion_rate': 0.01,  # 1000 coins = ₹10
            'inr_amount': int(net_amount * 0.01)
        }
        
        return jsonify(withdraw_info)
        
    except Exception as e:
        logger.error(f"Error getting withdraw info for {telegram_id}: {str(e)}")
        return jsonify({'error': 'Failed to get withdrawal info'}), 500

@withdraw_bp.route('/api/withdraw/request', methods=['POST'])
def request_withdrawal():
    """Request withdrawal with real-time validation"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        upi_id = data.get('upi_id')
        
        if not telegram_id or not amount or not upi_id:
            return jsonify({'error': 'telegram_id, amount, and upi_id are required'}), 400
        
        amount = int(float(amount))
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Validate withdrawal
        if amount < 1000:
            return jsonify({'error': 'Minimum withdrawal is 1000 coins'}), 400
        
        if user.coins < amount:
            return jsonify({'error': 'Insufficient coins'}), 400
        
        # Calculate fee
        fee = int(amount * 0.02)  # 2% fee
        net_amount = amount - fee
        inr_amount = int(net_amount * 0.01)  # 1000 coins = ₹10
        
        # Deduct coins from user
        if not user.subtract_coins(amount):
            return jsonify({'error': 'Failed to deduct coins'}), 500
        
        # Update user UPI ID
        user.upi_id = upi_id
        user.save()
        
        # Create withdrawal record
        withdrawal_data = {
            'user_id': user.telegram_id,
            'username': user.username,
            'amount': amount,
            'fee': fee,
            'net_amount': net_amount,
            'inr_amount': inr_amount,
            'upi_id': upi_id,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = supabase.table('withdrawals').insert(withdrawal_data).execute()
        
        if response.data:
            withdrawal = response.data[0]
            logger.info(f"Withdrawal request created: {withdrawal['id']} for user {telegram_id}, amount {amount}")
            
            return jsonify({
                'success': True,
                'withdrawal': withdrawal,
                'user': user.get_real_time_data()
            })
        else:
            # Rollback coins if withdrawal creation failed
            user.add_coins(amount)
            return jsonify({'error': 'Failed to create withdrawal request'}), 500
            
    except Exception as e:
        logger.error(f"Error requesting withdrawal: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@withdraw_bp.route('/api/withdraw/history/<int:telegram_id>', methods=['GET'])
def get_withdrawal_history(telegram_id):
    """Get withdrawal history for user"""
    try:
        response = supabase.table('withdrawals').select('*').eq('user_id', telegram_id).order('created_at', desc=True).execute()
        
        withdrawals = response.data if response.data else []
        
        return jsonify({
            'withdrawals': withdrawals,
            'count': len(withdrawals)
        })
        
    except Exception as e:
        logger.error(f"Error getting withdrawal history for {telegram_id}: {str(e)}")
        return jsonify({'error': 'Failed to get withdrawal history'}), 500

@withdraw_bp.route('/api/withdraw/status/<int:withdrawal_id>', methods=['GET'])
def get_withdrawal_status(withdrawal_id):
    """Get withdrawal status"""
    try:
        response = supabase.table('withdrawals').select('*').eq('id', withdrawal_id).execute()
        
        if response.data and len(response.data) > 0:
            withdrawal = response.data[0]
            return jsonify(withdrawal)
        else:
            return jsonify({'error': 'Withdrawal not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting withdrawal status {withdrawal_id}: {str(e)}")
        return jsonify({'error': 'Failed to get withdrawal status'}), 500

@withdraw_bp.route('/api/withdraw/cancel/<int:withdrawal_id>', methods=['POST'])
def cancel_withdrawal(withdrawal_id):
    """Cancel withdrawal and refund coins"""
    try:
        # Get withdrawal
        response = supabase.table('withdrawals').select('*').eq('id', withdrawal_id).execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({'error': 'Withdrawal not found'}), 404
        
        withdrawal = response.data[0]
        
        if withdrawal['status'] != 'pending':
            return jsonify({'error': 'Can only cancel pending withdrawals'}), 400
        
        # Get user and refund coins
        user = User.get_by_telegram_id(withdrawal['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Refund coins
        if user.add_coins(withdrawal['amount']):
            # Update withdrawal status
            update_response = supabase.table('withdrawals').update({
                'status': 'cancelled',
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', withdrawal_id).execute()
            
            if update_response.data:
                logger.info(f"Withdrawal {withdrawal_id} cancelled and {withdrawal['amount']} coins refunded to user {user.telegram_id}")
                
                return jsonify({
                    'success': True,
                    'withdrawal': update_response.data[0],
                    'user': user.get_real_time_data()
                })
            else:
                # Rollback coin addition if status update failed
                user.subtract_coins(withdrawal['amount'])
                return jsonify({'error': 'Failed to update withdrawal status'}), 500
        else:
            return jsonify({'error': 'Failed to refund coins'}), 500
            
    except Exception as e:
        logger.error(f"Error cancelling withdrawal {withdrawal_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


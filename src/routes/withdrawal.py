from flask import Blueprint, request, jsonify
from src.models.user import db, User, Transaction, WithdrawalRequest
from datetime import datetime
import re

withdrawal_bp = Blueprint('withdrawal', __name__)

@withdrawal_bp.route('/withdraw', methods=['POST'])
def process_withdrawal():
    """Process a withdrawal request"""
    data = request.json
    telegram_id = data.get('telegram_id')
    amount_coins = data.get('amount', 0)
    upi_id = data.get('upi_id', '').strip()
    
    # Validate input
    if not telegram_id or not amount_coins or not upi_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if amount_coins < 1000:
        return jsonify({'error': 'Minimum withdrawal amount is 1,000 coins'}), 400
    
    # Validate UPI ID format
    if not is_valid_upi_id(upi_id):
        return jsonify({'error': 'Invalid UPI ID format'}), 400
    
    # Get user
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check balance
    if user.coins < amount_coins:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Calculate amounts
    amount_rupees = amount_coins / 100  # 100 coins = 1 rupee
    fee_amount = amount_rupees * 0.02  # 2% processing fee
    final_amount = amount_rupees - fee_amount
    
    # Check daily withdrawal limit (optional)
    today = datetime.utcnow().date()
    daily_withdrawals = WithdrawalRequest.query.filter(
        WithdrawalRequest.user_id == user.id,
        db.func.date(WithdrawalRequest.created_at) == today
    ).all()
    
    daily_total = sum(w.amount_coins for w in daily_withdrawals)
    if daily_total + amount_coins > 100000:  # 100k coins per day limit
        return jsonify({'error': 'Daily withdrawal limit exceeded (100,000 coins)'}), 400
    
    try:
        # Deduct coins from user
        user.coins -= amount_coins
        user.total_withdrawn += final_amount
        
        # Update UPI ID if provided
        if upi_id:
            user.upi_id = upi_id
        
        # Create withdrawal request
        withdrawal = WithdrawalRequest(
            user_id=user.id,
            amount_coins=amount_coins,
            amount_rupees=amount_rupees,
            fee_amount=fee_amount,
            final_amount=final_amount,
            upi_id=upi_id,
            status='pending'
        )
        
        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            transaction_type='withdrawal',
            amount=-amount_coins,  # Negative for withdrawal
            description=f'Withdrawal request: ₹{final_amount:.2f} to {upi_id}'
        )
        
        db.session.add(withdrawal)
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'withdrawal_id': withdrawal.id,
            'amount_coins': amount_coins,
            'final_amount': final_amount,
            'new_balance': user.coins,
            'status': 'pending',
            'message': 'Withdrawal request submitted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to process withdrawal'}), 500

@withdrawal_bp.route('/withdrawal_history/<int:telegram_id>', methods=['GET'])
def get_withdrawal_history(telegram_id):
    """Get user's withdrawal history"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    withdrawals = WithdrawalRequest.query.filter_by(user_id=user.id)\
        .order_by(WithdrawalRequest.created_at.desc())\
        .limit(20).all()
    
    withdrawal_data = []
    for w in withdrawals:
        withdrawal_data.append({
            'id': w.id,
            'amount_coins': w.amount_coins,
            'amount_rupees': w.amount_rupees,
            'fee_amount': w.fee_amount,
            'final_amount': w.final_amount,
            'upi_id': w.upi_id,
            'status': w.status,
            'created_at': w.created_at.isoformat(),
            'processed_at': w.processed_at.isoformat() if w.processed_at else None
        })
    
    return jsonify({
        'user_id': telegram_id,
        'withdrawals': withdrawal_data,
        'total_withdrawn': user.total_withdrawn
    })

@withdrawal_bp.route('/admin/withdrawals', methods=['GET'])
def get_pending_withdrawals():
    """Get pending withdrawal requests (admin only)"""
    status = request.args.get('status', 'pending')
    
    withdrawals = WithdrawalRequest.query.filter_by(status=status)\
        .order_by(WithdrawalRequest.created_at.desc())\
        .limit(50).all()
    
    withdrawal_data = []
    for w in withdrawals:
        withdrawal_data.append({
            'id': w.id,
            'user_name': w.user.first_name or w.user.username or f'User{w.user.id}',
            'telegram_id': w.user.telegram_id,
            'amount_coins': w.amount_coins,
            'final_amount': w.final_amount,
            'upi_id': w.upi_id,
            'status': w.status,
            'created_at': w.created_at.isoformat()
        })
    
    return jsonify({
        'status': status,
        'withdrawals': withdrawal_data,
        'count': len(withdrawal_data)
    })

@withdrawal_bp.route('/admin/withdrawal/<int:withdrawal_id>', methods=['PUT'])
def update_withdrawal_status(withdrawal_id):
    """Update withdrawal status (admin only)"""
    data = request.json
    new_status = data.get('status')
    admin_notes = data.get('notes', '')
    
    if new_status not in ['pending', 'processing', 'completed', 'failed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    withdrawal = WithdrawalRequest.query.get_or_404(withdrawal_id)
    old_status = withdrawal.status
    
    withdrawal.status = new_status
    withdrawal.admin_notes = admin_notes
    
    if new_status in ['completed', 'failed']:
        withdrawal.processed_at = datetime.utcnow()
    
    # If withdrawal failed, refund coins to user
    if new_status == 'failed' and old_status != 'failed':
        user = withdrawal.user
        user.coins += withdrawal.amount_coins
        user.total_withdrawn -= withdrawal.final_amount
        
        # Create refund transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type='refund',
            amount=withdrawal.amount_coins,
            description=f'Refund for failed withdrawal: ₹{withdrawal.final_amount:.2f}'
        )
        db.session.add(transaction)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'withdrawal_id': withdrawal_id,
        'old_status': old_status,
        'new_status': new_status,
        'message': f'Withdrawal status updated to {new_status}'
    })

@withdrawal_bp.route('/withdrawal_stats', methods=['GET'])
def get_withdrawal_stats():
    """Get withdrawal statistics"""
    total_requests = WithdrawalRequest.query.count()
    pending_requests = WithdrawalRequest.query.filter_by(status='pending').count()
    completed_requests = WithdrawalRequest.query.filter_by(status='completed').count()
    failed_requests = WithdrawalRequest.query.filter_by(status='failed').count()
    
    total_amount = db.session.query(db.func.sum(WithdrawalRequest.final_amount))\
        .filter_by(status='completed').scalar() or 0
    
    return jsonify({
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'completed_requests': completed_requests,
        'failed_requests': failed_requests,
        'total_amount_paid': float(total_amount),
        'success_rate': (completed_requests / max(total_requests, 1)) * 100
    })

def is_valid_upi_id(upi_id):
    """Validate UPI ID format"""
    # Basic UPI ID validation: username@provider
    pattern = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$'
    return re.match(pattern, upi_id) is not None


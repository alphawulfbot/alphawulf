from flask import Blueprint, request, jsonify
from src.models.user import db, User, Transaction
from datetime import datetime

game_bp = Blueprint('game', __name__)

@game_bp.route('/users/telegram/<int:telegram_id>', methods=['GET'])
def get_user_by_telegram_id(telegram_id):
    """Get user by Telegram ID"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update energy before returning data
    user.update_energy()
    return jsonify(user.to_dict())

@game_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.json
    
    # Check if user already exists
    existing_user = User.query.filter_by(telegram_id=data['telegram_id']).first()
    if existing_user:
        return jsonify(existing_user.to_dict()), 200
    
    user = User(
        telegram_id=data['telegram_id'],
        username=data.get('username'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        coins=2500,  # Welcome bonus
        energy=100
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify(user.to_dict()), 201

@game_bp.route('/tap', methods=['POST'])
def handle_tap():
    """Handle tap action"""
    data = request.json
    telegram_id = data.get('telegram_id')
    taps = data.get('taps', 1)
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update energy first
    user.update_energy()
    
    # Check if user has enough energy
    if user.energy < taps:
        return jsonify({'error': 'Not enough energy'}), 400
    
    # Process taps
    coins_earned = taps * user.tap_power
    user.energy -= taps
    user.coins += coins_earned
    user.total_earned += coins_earned
    
    # Create transaction record
    transaction = Transaction(
        user_id=user.id,
        transaction_type='tap',
        amount=coins_earned,
        description=f'Earned {coins_earned} coins from {taps} taps'
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'coins_earned': coins_earned,
        'new_balance': user.coins,
        'energy_remaining': user.energy
    })

@game_bp.route('/energy', methods=['POST'])
def update_energy():
    """Manually update user energy"""
    data = request.json
    telegram_id = data.get('telegram_id')
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.update_energy()
    
    return jsonify({
        'energy': user.energy,
        'max_energy': user.max_energy
    })

@game_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top users by coins"""
    users = User.query.order_by(User.coins.desc()).limit(10).all()
    
    leaderboard = []
    for i, user in enumerate(users, 1):
        leaderboard.append({
            'rank': i,
            'name': user.first_name or user.username or f'User{user.id}',
            'coins': user.coins
        })
    
    return jsonify(leaderboard)

@game_bp.route('/stats/<int:telegram_id>', methods=['GET'])
def get_user_stats(telegram_id):
    """Get detailed user statistics"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=user.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(10).all()
    
    transactions_data = []
    for tx in recent_transactions:
        transactions_data.append({
            'type': tx.transaction_type,
            'amount': tx.amount,
            'description': tx.description,
            'date': tx.created_at.isoformat()
        })
    
    return jsonify({
        'user': user.to_dict(),
        'recent_transactions': transactions_data
    })


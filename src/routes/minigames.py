from flask import Blueprint, request, jsonify
from src.models.user import db, User, Transaction
from datetime import datetime

minigames_bp = Blueprint('minigames', __name__)

@minigames_bp.route('/minigame_reward', methods=['POST'])
def award_minigame_reward():
    """Award coins for completing a mini-game"""
    data = request.json
    telegram_id = data.get('telegram_id')
    amount = data.get('amount', 0)
    game_name = data.get('game_name', 'Unknown Game')
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Award coins
    user.coins += amount
    user.total_earned += amount
    
    # Create transaction record
    transaction = Transaction(
        user_id=user.id,
        transaction_type='minigame',
        amount=amount,
        description=f'Earned {amount} coins from {game_name}'
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'coins_awarded': amount,
        'new_balance': user.coins,
        'game_name': game_name
    })

@minigames_bp.route('/minigame_stats/<int:telegram_id>', methods=['GET'])
def get_minigame_stats(telegram_id):
    """Get user's mini-game statistics"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get mini-game transactions
    minigame_transactions = Transaction.query.filter_by(
        user_id=user.id,
        transaction_type='minigame'
    ).all()
    
    # Calculate stats by game
    game_stats = {}
    total_minigame_earnings = 0
    
    for tx in minigame_transactions:
        game_name = tx.description.split(' from ')[-1] if ' from ' in tx.description else 'Unknown'
        
        if game_name not in game_stats:
            game_stats[game_name] = {
                'games_played': 0,
                'total_earned': 0,
                'best_score': 0
            }
        
        game_stats[game_name]['games_played'] += 1
        game_stats[game_name]['total_earned'] += tx.amount
        game_stats[game_name]['best_score'] = max(game_stats[game_name]['best_score'], tx.amount)
        total_minigame_earnings += tx.amount
    
    return jsonify({
        'user_id': telegram_id,
        'total_minigame_earnings': total_minigame_earnings,
        'games_played': len(minigame_transactions),
        'game_stats': game_stats
    })

@minigames_bp.route('/minigame_leaderboard', methods=['GET'])
def get_minigame_leaderboard():
    """Get mini-game leaderboard"""
    game_name = request.args.get('game', None)
    
    # Get all mini-game transactions
    query = Transaction.query.filter_by(transaction_type='minigame')
    
    if game_name:
        query = query.filter(Transaction.description.contains(game_name))
    
    transactions = query.all()
    
    # Calculate user scores
    user_scores = {}
    for tx in transactions:
        user_id = tx.user_id
        if user_id not in user_scores:
            user_scores[user_id] = {
                'total_earned': 0,
                'games_played': 0,
                'best_score': 0
            }
        
        user_scores[user_id]['total_earned'] += tx.amount
        user_scores[user_id]['games_played'] += 1
        user_scores[user_id]['best_score'] = max(user_scores[user_id]['best_score'], tx.amount)
    
    # Get user details and create leaderboard
    leaderboard = []
    for user_id, stats in user_scores.items():
        user = User.query.get(user_id)
        if user:
            leaderboard.append({
                'name': user.first_name or user.username or f'User{user.id}',
                'telegram_id': user.telegram_id,
                'total_earned': stats['total_earned'],
                'games_played': stats['games_played'],
                'best_score': stats['best_score']
            })
    
    # Sort by total earned (descending)
    leaderboard.sort(key=lambda x: x['total_earned'], reverse=True)
    
    # Add ranks
    for i, entry in enumerate(leaderboard[:20], 1):  # Top 20
        entry['rank'] = i
    
    return jsonify({
        'game_name': game_name or 'All Games',
        'leaderboard': leaderboard[:20]
    })

@minigames_bp.route('/daily_challenge', methods=['GET'])
def get_daily_challenge():
    """Get today's daily challenge"""
    # Simple daily challenge based on date
    today = datetime.utcnow().date()
    day_of_year = today.timetuple().tm_yday
    
    challenges = [
        {
            'name': 'Wolf Hunt Master',
            'description': 'Find all wolves in Wolf Hunt with 5+ attempts remaining',
            'reward': 500,
            'game': 'Wolf Hunt'
        },
        {
            'name': 'Memory Champion',
            'description': 'Complete Pack Leader in under 20 moves',
            'reward': 400,
            'game': 'Pack Leader'
        },
        {
            'name': 'Perfect Howler',
            'description': 'Achieve 90%+ accuracy in Howl Challenge',
            'reward': 450,
            'game': 'Howl Challenge'
        }
    ]
    
    challenge = challenges[day_of_year % len(challenges)]
    
    return jsonify({
        'date': today.isoformat(),
        'challenge': challenge
    })


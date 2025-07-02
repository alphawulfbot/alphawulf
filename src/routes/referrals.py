from flask import Blueprint, request, jsonify
from src.models.user import db, User, Transaction, Referral
from datetime import datetime, timedelta

referrals_bp = Blueprint('referrals', __name__)

@referrals_bp.route('/referral_stats/<int:telegram_id>', methods=['GET'])
def get_referral_stats(telegram_id):
    """Get user's referral statistics"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get all referrals made by this user
    referrals = Referral.query.filter_by(referrer_id=user.id).all()
    
    # Calculate statistics
    total_referrals = len(referrals)
    total_earnings = sum(ref.total_earnings for ref in referrals)
    
    # Active referrals this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_this_week = len([ref for ref in referrals if ref.created_at >= week_ago])
    
    # Get referral details
    referral_details = []
    for ref in referrals:
        referred_user = ref.referred
        referral_details.append({
            'name': referred_user.first_name or referred_user.username or 'Anonymous Wolf',
            'joined_date': ref.created_at.isoformat(),
            'earnings_from_referral': ref.total_earnings,
            'is_active': referred_user.last_activity and 
                        (datetime.utcnow() - referred_user.last_activity).days < 7
        })
    
    return jsonify({
        'user_id': telegram_id,
        'total_referrals': total_referrals,
        'total_earnings': total_earnings,
        'active_this_week': active_this_week,
        'referrals': referral_details
    })

@referrals_bp.route('/process_referral', methods=['POST'])
def process_referral():
    """Process a new referral when someone joins via referral link"""
    data = request.json
    referrer_telegram_id = data.get('referrer_telegram_id')
    referred_telegram_id = data.get('referred_telegram_id')
    
    if not referrer_telegram_id or not referred_telegram_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Don't allow self-referral
    if referrer_telegram_id == referred_telegram_id:
        return jsonify({'error': 'Cannot refer yourself'}), 400
    
    referrer = User.query.filter_by(telegram_id=referrer_telegram_id).first()
    referred = User.query.filter_by(telegram_id=referred_telegram_id).first()
    
    if not referrer or not referred:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if referral already exists
    existing_referral = Referral.query.filter_by(
        referrer_id=referrer.id,
        referred_id=referred.id
    ).first()
    
    if existing_referral:
        return jsonify({'error': 'Referral already exists'}), 400
    
    try:
        # Create referral record
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=referred.id
        )
        
        # Give bonus to referrer
        referral_bonus = 500
        referrer.coins += referral_bonus
        referrer.total_earned += referral_bonus
        
        # Give bonus to referred user
        referred_bonus = 250
        referred.coins += referred_bonus
        referred.total_earned += referred_bonus
        
        # Create transaction records
        referrer_transaction = Transaction(
            user_id=referrer.id,
            transaction_type='referral',
            amount=referral_bonus,
            description=f'Referral bonus for inviting {referred.first_name or "new user"}'
        )
        
        referred_transaction = Transaction(
            user_id=referred.id,
            transaction_type='referral',
            amount=referred_bonus,
            description=f'Welcome bonus for joining via referral'
        )
        
        db.session.add(referral)
        db.session.add(referrer_transaction)
        db.session.add(referred_transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'referrer_bonus': referral_bonus,
            'referred_bonus': referred_bonus,
            'referrer_new_balance': referrer.coins,
            'referred_new_balance': referred.coins
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to process referral'}), 500

@referrals_bp.route('/referral_leaderboard', methods=['GET'])
def get_referral_leaderboard():
    """Get referral leaderboard"""
    # Get top referrers
    referrers = db.session.query(
        User.telegram_id,
        User.first_name,
        User.username,
        db.func.count(Referral.id).label('referral_count'),
        db.func.sum(Referral.total_earnings).label('total_earnings')
    ).join(
        Referral, User.id == Referral.referrer_id
    ).group_by(
        User.id
    ).order_by(
        db.func.count(Referral.id).desc()
    ).limit(20).all()
    
    leaderboard = []
    for i, referrer in enumerate(referrers, 1):
        leaderboard.append({
            'rank': i,
            'name': referrer.first_name or referrer.username or f'User{referrer.telegram_id}',
            'telegram_id': referrer.telegram_id,
            'referral_count': referrer.referral_count,
            'total_earnings': referrer.total_earnings or 0
        })
    
    return jsonify({
        'leaderboard': leaderboard
    })

@referrals_bp.route('/weekly_referral_bonus', methods=['POST'])
def process_weekly_referral_bonus():
    """Process weekly referral bonuses (10% of referred user's earnings)"""
    data = request.json
    referred_telegram_id = data.get('referred_telegram_id')
    weekly_earnings = data.get('weekly_earnings', 0)
    
    if not referred_telegram_id or weekly_earnings <= 0:
        return jsonify({'error': 'Invalid data'}), 400
    
    referred_user = User.query.filter_by(telegram_id=referred_telegram_id).first()
    if not referred_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Find who referred this user
    referral = Referral.query.filter_by(referred_id=referred_user.id).first()
    if not referral:
        return jsonify({'message': 'No referrer found'}), 200
    
    referrer = referral.referrer
    
    # Calculate 10% bonus
    bonus_amount = int(weekly_earnings * 0.1)
    
    if bonus_amount > 0:
        try:
            # Give bonus to referrer
            referrer.coins += bonus_amount
            referrer.total_earned += bonus_amount
            
            # Update referral earnings
            referral.total_earnings += bonus_amount
            
            # Create transaction record
            transaction = Transaction(
                user_id=referrer.id,
                transaction_type='referral',
                amount=bonus_amount,
                description=f'Weekly referral bonus (10% of {referred_user.first_name or "referred user"}\'s earnings)'
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'bonus_amount': bonus_amount,
                'referrer_new_balance': referrer.coins
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to process weekly bonus'}), 500
    
    return jsonify({'message': 'No bonus to process'}), 200


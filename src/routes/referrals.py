from flask import Blueprint, request, jsonify
from src.models.user import User
import time

referral_bp = Blueprint('referral', __name__)

@referral_bp.route('/api/referral/<referral_code>', methods=['POST'])
def use_referral(referral_code):
    """
    Use a referral code
    """
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        username = data.get('username', f"user_{telegram_id}")
        first_name = data.get('first_name', "User")
        
        if not telegram_id:
            return jsonify({'error': 'Missing telegram_id'}), 400
        
        # Check if referral code is valid (it's the referrer's telegram_id)
        referrer_id = referral_code.replace('ref_', '')
        
        # Don't allow self-referral
        if str(telegram_id) == str(referrer_id):
            return jsonify({'error': 'Cannot refer yourself'}), 400
        
        # Get referrer from database
        referrer = User.get_by_telegram_id(referrer_id)
        if not referrer:
            return jsonify({'error': 'Invalid referral code'}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            # Create a new user if not found
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                coins=500,  # Bonus coins for using referral
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=int(time.time()),
                referred_by=referrer_id
            )
            user.save()
            
            # Add referral bonus to referrer
            referrer.coins += 500
            referrer.referral_count = (referrer.referral_count or 0) + 1
            referrer.referral_earnings = (referrer.referral_earnings or 0) + 500
            referrer.save()
            
            # Add to referred_users table
            from src.config.database import supabase
            referred_user = {
                'referrer_id': referrer_id,
                'user_id': telegram_id,
                'username': username,
                'name': first_name,
                'joined_date': int(time.time()),
                'earnings_from_referral': 500
            }
            supabase.table('referred_users').insert(referred_user).execute()
            
            return jsonify({
                'success': True,
                'message': 'Referral code used successfully',
                'user': user.to_dict()
            })
        else:
            # User already exists
            if user.referred_by:
                return jsonify({'error': 'Already used a referral code'}), 400
            
            # Update user with referral
            user.referred_by = referrer_id
            user.coins += 500  # Bonus coins for using referral
            user.save()
            
            # Add referral bonus to referrer
            referrer.coins += 500
            referrer.referral_count = (referrer.referral_count or 0) + 1
            referrer.referral_earnings = (referrer.referral_earnings or 0) + 500
            referrer.save()
            
            # Add to referred_users table
            from src.config.database import supabase
            referred_user = {
                'referrer_id': referrer_id,
                'user_id': telegram_id,
                'username': username,
                'name': first_name,
                'joined_date': int(time.time()),
                'earnings_from_referral': 500
            }
            supabase.table('referred_users').insert(referred_user).execute()
            
            return jsonify({
                'success': True,
                'message': 'Referral code used successfully',
                'user': user.to_dict()
            })
        
    except Exception as e:
        print(f"Error in use_referral: {str(e)}")
        return jsonify({'error': str(e)}), 500

@referral_bp.route('/api/referral_stats/<telegram_id>', methods=['GET'])
def referral_stats(telegram_id):
    """
    Get referral stats for a user
    """
    try:
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get referred users from database
        from src.config.database import supabase
        response = supabase.table('referred_users').select('*').eq('referrer_id', telegram_id).execute()
        
        referred_users = response.data
        
        # Calculate stats
        total_referrals = len(referred_users)
        total_earnings = sum(user.get('earnings_from_referral', 0) for user in referred_users)
        
        # Active referrals in last week (placeholder - would need last_active in user model)
        active_this_week = total_referrals  # For now, assume all are active
        
        return jsonify({
            'success': True,
            'total_referrals': total_referrals,
            'total_earnings': total_earnings,
            'active_this_week': active_this_week,
            'referrals': referred_users
        })
        
    except Exception as e:
        print(f"Error in referral_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


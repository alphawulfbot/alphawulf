from flask import Blueprint, request, jsonify
from src.models.user import User
import time

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/user/<telegram_id>', methods=['GET'])
def get_user(telegram_id):
    """
    Get user data by Telegram ID
    """
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            # Create a new user if not found
            user = User(
                telegram_id=telegram_id,
                username="user_" + str(telegram_id),
                first_name="User",
                coins=0,
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=None
            )
            user.save()
        
        # Update energy based on regeneration rate
        current_time = int(time.time())
        if user.last_energy_update:
            time_diff = current_time - user.last_energy_update
            energy_to_add = (time_diff // 60) * user.energy_regen_rate  # 1 energy per minute * regen rate
            
            if energy_to_add > 0:
                user.energy = min(user.energy + energy_to_add, user.max_energy)
                user.last_energy_update = current_time
                user.save()
        else:
            user.last_energy_update = current_time
            user.save()
        
        return jsonify(user.to_dict())
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/api/user/update', methods=['POST'])
def update_user():
    """
    Update user data (coins, energy, etc.)
    """
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'error': 'Missing telegram_id'}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            # Create a new user if not found
            user = User(
                telegram_id=telegram_id,
                username=data.get('username', "user_" + str(telegram_id)),
                first_name=data.get('first_name', "User"),
                coins=0,
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=int(time.time())
            )
        
        # Update user fields
        if 'coins' in data:
            coins_to_add = data.get('coins', 0)
            user.coins += coins_to_add
        
        if 'energy' in data:
            energy_to_use = data.get('energy', 0)
            # Only deduct energy if user has enough and energy is positive
            if energy_to_use > 0 and user.energy >= energy_to_use:
                user.energy -= energy_to_use
                user.last_energy_update = int(time.time())
            elif energy_to_use < 0:
                # Negative energy means adding energy (for testing)
                user.energy = min(user.energy - energy_to_use, user.max_energy)
                user.last_energy_update = int(time.time())
        
        # Update other fields if provided
        if 'username' in data:
            user.username = data.get('username')
        
        if 'first_name' in data:
            user.first_name = data.get('first_name')
        
        if 'upi_id' in data:
            user.upi_id = data.get('upi_id')
        
        # Save user
        user.save()
        
        return jsonify(user.to_dict())
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@user_bp.route('/api/tap', methods=['POST'])
def tap():
    """
    Handle user taps to earn coins
    """
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        taps = data.get('taps', 1)
        
        if not telegram_id:
            return jsonify({'error': 'Missing telegram_id'}), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            # Create a new user if not found
            user = User(
                telegram_id=telegram_id,
                username="user_" + str(telegram_id),
                first_name="User",
                coins=0,
                energy=100,
                max_energy=100,
                tap_power=1,
                energy_regen_rate=1,
                last_energy_update=int(time.time())
            )
        
        # Update energy based on regeneration rate
        current_time = int(time.time())
        if user.last_energy_update:
            time_diff = current_time - user.last_energy_update
            energy_to_add = (time_diff // 60) * user.energy_regen_rate  # 1 energy per minute * regen rate
            
            if energy_to_add > 0:
                user.energy = min(user.energy + energy_to_add, user.max_energy)
                user.last_energy_update = current_time
        else:
            user.last_energy_update = current_time
        
        # Calculate energy needed for taps
        energy_needed = taps
        
        # Check if user has enough energy
        if user.energy < energy_needed:
            # Adjust taps based on available energy
            taps = user.energy
            energy_needed = taps
        
        # If no energy, return early
        if taps <= 0:
            user.save()
            return jsonify({
                'success': False,
                'error': 'Not enough energy',
                'user': user.to_dict()
            })
        
        # Calculate coins earned
        coins_earned = taps * user.tap_power
        
        # Update user
        user.coins += coins_earned
        user.energy -= energy_needed
        
        # Save user
        user.save()
        
        return jsonify({
            'success': True,
            'coins_earned': coins_earned,
            'energy_used': energy_needed,
            'user': user.to_dict()
        })
    except Exception as e:
        print(f"Error in tap: {str(e)}")
        return jsonify({'error': str(e)}), 500


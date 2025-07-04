from flask import Blueprint, request, jsonify
from src.models.user import User

minigames_bp = Blueprint('minigames', __name__)

@minigames_bp.route('/api/minigame_reward', methods=['POST'])
def minigame_reward():
    """
    Award coins for completing minigames
    """
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        game_name = data.get('game_name')
        
        if not telegram_id or not amount or not game_name:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Get user from database
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            # Create user if not exists
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
        
        # Add coins to user
        user.coins += amount
        
        # Save user
        user.save()
        
        # Log minigame reward
        from src.config.database import supabase
        minigame_log = {
            'telegram_id': telegram_id,
            'game_name': game_name,
            'amount': amount,
            'timestamp': int(time.time())
        }
        supabase.table('minigame_rewards').insert(minigame_log).execute()
        
        return jsonify({
            'success': True,
            'message': f'Awarded {amount} coins for {game_name}',
            'user': user.to_dict()
        })
        
    except Exception as e:
        print(f"Error in minigame_reward: {str(e)}")
        return jsonify({'error': str(e)}), 500


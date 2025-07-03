from flask import Blueprint, request, jsonify
from src.models.user import User, Transaction
from datetime import datetime
import random

minigames_bp = Blueprint("minigames", __name__)

@minigames_bp.route("/spin_wheel", methods=["POST"])
def spin_wheel():
    """Handle spin wheel minigame"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user has enough coins to spin (cost: 100 coins)
        spin_cost = 100
        if user.coins < spin_cost:
            return jsonify({"error": "Not enough coins"}), 400
        
        # Deduct spin cost
        user.coins -= spin_cost
        
        # Generate random reward
        rewards = [50, 100, 150, 200, 250, 500, 1000]
        reward = random.choice(rewards)
        
        # Add reward to user
        user.coins += reward
        user.save()
        
        # Log transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type="minigame",
            amount=reward,
            description=f"Earned {reward} coins from Spin Wheel"
        )
        transaction.save()
        
        return jsonify({
            "success": True,
            "reward": reward,
            "user": user.to_dict()
        })
    
    except Exception as e:
        print(f"Spin wheel error: {e}")
        return jsonify({"error": str(e)}), 500

@minigames_bp.route("/daily_bonus", methods=["POST"])
def daily_bonus():
    """Handle daily bonus claim"""
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # For now, just give a fixed daily bonus
        daily_bonus_amount = 500
        user.coins += daily_bonus_amount
        user.save()
        
        # Log transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type="daily_bonus",
            amount=daily_bonus_amount,
            description="Daily bonus claim"
        )
        transaction.save()
        
        return jsonify({
            "success": True,
            "bonus": daily_bonus_amount,
            "user": user.to_dict()
        })
    
    except Exception as e:
        print(f"Daily bonus error: {e}")
        return jsonify({"error": str(e)}), 500

@minigames_bp.route("/minigame_stats/<int:telegram_id>", methods=["GET"])
def get_minigame_stats(telegram_id):
    """Get user's mini-game statistics"""
    try:
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        minigame_transactions = Transaction.get_by_user_id(user.id)
        minigame_transactions = [tx for tx in minigame_transactions if tx.transaction_type == "minigame"]

        game_stats = {}
        total_minigame_earnings = 0
        
        for tx in minigame_transactions:
            game_name = tx.description.split(" from ")[-1] if " from " in tx.description else "Unknown"
            
            if game_name not in game_stats:
                game_stats[game_name] = {
                    "games_played": 0,
                    "total_earned": 0,
                    "best_score": 0
                }
            
            game_stats[game_name]["games_played"] += 1
            game_stats[game_name]["total_earned"] += tx.amount
            game_stats[game_name]["best_score"] = max(game_stats[game_name]["best_score"], tx.amount)
            total_minigame_earnings += tx.amount
        
        return jsonify({
            "user_id": telegram_id,
            "total_minigame_earnings": total_minigame_earnings,
            "games_played": len(minigame_transactions),
            "game_stats": game_stats
        })
    
    except Exception as e:
        print(f"Get minigame stats error: {e}")
        return jsonify({"error": str(e)}), 500

@minigames_bp.route("/minigame_leaderboard", methods=["GET"])
def get_minigame_leaderboard():
    """Get mini-game leaderboard"""
    try:
        game_name = request.args.get("game", None)
        
        all_transactions = []
        # This would ideally be a Supabase query for transactions by type
        # For now, fetching all users and their transactions
        all_users = User.get_all_users()
        for user_data in all_users:
            user_obj = User(**user_data)
            user_transactions = Transaction.get_by_user_id(user_obj.id)
            all_transactions.extend([tx for tx in user_transactions if tx.transaction_type == "minigame"])

        # Filter by game name if provided
        if game_name:
            all_transactions = [tx for tx in all_transactions if game_name in tx.description]

        # Calculate user scores
        user_scores = {}
        for tx in all_transactions:
            user_id = tx.user_id
            if user_id not in user_scores:
                user_scores[user_id] = {
                    "total_earned": 0,
                    "games_played": 0,
                    "best_score": 0
                }
            
            user_scores[user_id]["total_earned"] += tx.amount
            user_scores[user_id]["games_played"] += 1
            user_scores[user_id]["best_score"] = max(user_scores[user_id]["best_score"], tx.amount)
        
        # Get user details and create leaderboard
        leaderboard = []
        for user_id, stats in user_scores.items():
            user = User.get_by_id(user_id) # Assuming a get_by_id method exists or fetch from all_users
            if user:
                leaderboard.append({
                    "name": user.first_name or user.username or f"User{user.telegram_id}",
                    "telegram_id": user.telegram_id,
                    "total_earned": stats["total_earned"],
                    "games_played": stats["games_played"],
                    "best_score": stats["best_score"]
                })
        
        # Sort by total earned (descending)
        leaderboard.sort(key=lambda x: x["total_earned"], reverse=True)
        
        # Add ranks
        for i, entry in enumerate(leaderboard[:20], 1):  # Top 20
            entry["rank"] = i
        
        return jsonify({
            "game_name": game_name or "All Games",
            "leaderboard": leaderboard[:20]
        })
    
    except Exception as e:
        print(f"Minigame leaderboard error: {e}")
        return jsonify([])

@minigames_bp.route("/daily_challenge", methods=["GET"])
def get_daily_challenge():
    """Get today's daily challenge"""
    # Simple daily challenge based on date
    today = datetime.utcnow().date()
    day_of_year = today.timetuple().tm_yday
    
    challenges = [
        {
            "name": "Wolf Hunt Master",
            "description": "Find all wolves in Wolf Hunt with 5+ attempts remaining",
            "reward": 500,
            "game": "Wolf Hunt"
        },
        {
            "name": "Memory Champion",
            "description": "Complete Pack Leader in under 20 moves",
            "reward": 400,
            "game": "Pack Leader"
        },
        {
            "name": "Perfect Howler",
            "description": "Achieve 90%+ accuracy in Howl Challenge",
            "reward": 450,
            "game": "Howl Challenge"
        }
    ]
    
    challenge = challenges[day_of_year % len(challenges)]
    
    return jsonify({
        "date": today.isoformat(),
        "challenge": challenge
    })

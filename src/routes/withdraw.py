from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging
from src.config.database import supabase
from src.models.user import User

logger = logging.getLogger(__name__)

withdraw_bp = Blueprint('withdraw', __name__)

class Withdrawal:
    def __init__(self, id=None, user_id=None, telegram_id=None, amount=None, 
                 final_amount=None, upi_id=None, status='pending', 
                 created_at=None, processed_at=None):
        self.id = id
        self.user_id = user_id
        self.telegram_id = int(telegram_id) if telegram_id else None
        self.amount = int(float(amount)) if amount is not None else 0
        self.final_amount = int(float(final_amount)) if final_amount is not None else 0
        self.upi_id = upi_id or ""
        self.status = status or 'pending'
        self.created_at = created_at or datetime.now(timezone.utc)
        self.processed_at = processed_at

    @classmethod
    def create_withdrawal(cls, telegram_id, amount, upi_id):
        """Create a new withdrawal request"""
        try:
            telegram_id = int(telegram_id)
            amount = int(float(amount))
            
            # Calculate final amount (2% fee)
            fee_percentage = 0.02
            final_amount = int(amount * (1 - fee_percentage))
            
            withdrawal_data = {
                'telegram_id': telegram_id,
                'amount': amount,
                'final_amount': final_amount,
                'upi_id': str(upi_id),
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = supabase.table('withdrawals').insert(withdrawal_data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Withdrawal created: {response.data[0]}")
                return cls(**response.data[0])
            else:
                logger.error(f"Failed to create withdrawal: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating withdrawal: {str(e)}")
            return None

    @classmethod
    def get_user_withdrawals(cls, telegram_id):
        """Get all withdrawals for a user"""
        try:
            telegram_id = int(telegram_id)
            
            response = supabase.table('withdrawals').select('*').eq('telegram_id', telegram_id).order('created_at', desc=True).execute()
            
            withdrawals = []
            if response.data:
                for withdrawal_data in response.data:
                    try:
                        # Convert datetime strings
                        created_at = None
                        processed_at = None
                        
                        if withdrawal_data.get('created_at'):
                            try:
                                created_at = datetime.fromisoformat(withdrawal_data['created_at'].replace('Z', '+00:00'))
                            except:
                                created_at = datetime.now(timezone.utc)
                        
                        if withdrawal_data.get('processed_at'):
                            try:
                                processed_at = datetime.fromisoformat(withdrawal_data['processed_at'].replace('Z', '+00:00'))
                            except:
                                processed_at = None
                        
                        withdrawal = cls(
                            id=withdrawal_data.get('id'),
                            user_id=withdrawal_data.get('user_id'),
                            telegram_id=withdrawal_data.get('telegram_id'),
                            amount=withdrawal_data.get('amount'),
                            final_amount=withdrawal_data.get('final_amount'),
                            upi_id=withdrawal_data.get('upi_id'),
                            status=withdrawal_data.get('status', 'pending'),
                            created_at=created_at,
                            processed_at=processed_at
                        )
                        withdrawals.append(withdrawal)
                    except Exception as e:
                        logger.error(f"Error processing withdrawal data: {withdrawal_data}, error: {str(e)}")
                        continue
            
            logger.info(f"Retrieved {len(withdrawals)} withdrawals for user {telegram_id}")
            return withdrawals
            
        except Exception as e:
            logger.error(f"Error getting user withdrawals: {str(e)}")
            return []

    @classmethod
    def get_all_withdrawals(cls):
        """Get all withdrawals"""
        try:
            response = supabase.table('withdrawals').select('*').order('created_at', desc=True).execute()
            
            withdrawals = []
            if response.data:
                for withdrawal_data in response.data:
                    try:
                        # Convert datetime strings
                        created_at = None
                        processed_at = None
                        
                        if withdrawal_data.get('created_at'):
                            try:
                                created_at = datetime.fromisoformat(withdrawal_data['created_at'].replace('Z', '+00:00'))
                            except:
                                created_at = datetime.now(timezone.utc)
                        
                        if withdrawal_data.get('processed_at'):
                            try:
                                processed_at = datetime.fromisoformat(withdrawal_data['processed_at'].replace('Z', '+00:00'))
                            except:
                                processed_at = None
                        
                        withdrawal = cls(
                            id=withdrawal_data.get('id'),
                            user_id=withdrawal_data.get('user_id'),
                            telegram_id=withdrawal_data.get('telegram_id'),
                            amount=withdrawal_data.get('amount'),
                            final_amount=withdrawal_data.get('final_amount'),
                            upi_id=withdrawal_data.get('upi_id'),
                            status=withdrawal_data.get('status', 'pending'),
                            created_at=created_at,
                            processed_at=processed_at
                        )
                        withdrawals.append(withdrawal)
                    except Exception as e:
                        logger.error(f"Error processing withdrawal data: {withdrawal_data}, error: {str(e)}")
                        continue
            
            logger.info(f"Retrieved {len(withdrawals)} total withdrawals")
            return withdrawals
            
        except Exception as e:
            logger.error(f"Error getting all withdrawals: {str(e)}")
            return []

    def update_status(self, status):
        """Update withdrawal status"""
        try:
            update_data = {
                'status': status
            }
            
            if status in ['completed', 'rejected']:
                update_data['processed_at'] = datetime.now(timezone.utc).isoformat()
            
            response = supabase.table('withdrawals').update(update_data).eq('id', self.id).execute()
            
            if response.data and len(response.data) > 0:
                self.status = status
                if status in ['completed', 'rejected']:
                    self.processed_at = datetime.now(timezone.utc)
                logger.info(f"Withdrawal {self.id} status updated to {status}")
                return True
            else:
                logger.error(f"Failed to update withdrawal status: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating withdrawal status: {str(e)}")
            return False

    def to_dict(self):
        """Convert withdrawal to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'telegram_id': self.telegram_id,
            'amount': self.amount,
            'final_amount': self.final_amount,
            'upi_id': self.upi_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

@withdraw_bp.route('/api/withdraw/request', methods=['POST'])
def request_withdrawal():
    """Request a withdrawal"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        upi_id = data.get('upi_id')
        
        if not telegram_id or not amount or not upi_id:
            return jsonify({
                "error": "telegram_id, amount, and upi_id are required",
                "success": False
            }), 400
        
        amount = int(float(amount))
        
        # Check minimum withdrawal amount
        if amount < 1000:
            return jsonify({
                "error": "Minimum withdrawal amount is 1000 coins",
                "success": False
            }), 400
        
        # Get user and check balance
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                "error": "User not found",
                "success": False
            }), 404
        
        if user.coins < amount:
            return jsonify({
                "error": "Insufficient balance",
                "success": False
            }), 400
        
        # Create withdrawal request
        withdrawal = Withdrawal.create_withdrawal(telegram_id, amount, upi_id)
        
        if not withdrawal:
            return jsonify({
                "error": "Failed to create withdrawal request",
                "success": False
            }), 500
        
        # Deduct coins from user
        if user.subtract_coins(amount):
            response = jsonify({
                "success": True,
                "withdrawal": withdrawal.to_dict(),
                "user": user.to_dict(),
                "message": "Withdrawal request created successfully"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            return jsonify({
                "error": "Failed to deduct coins",
                "success": False
            }), 500
            
    except Exception as e:
        logger.error(f"Withdrawal request error: {str(e)}")
        return jsonify({
            "error": "Withdrawal request failed",
            "message": str(e),
            "success": False
        }), 500

@withdraw_bp.route('/api/withdraw/history', methods=['GET'])
def get_withdrawal_history():
    """Get withdrawal history for a user"""
    try:
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id:
            return jsonify({
                "error": "telegram_id is required",
                "success": False
            }), 400
        
        withdrawals = Withdrawal.get_user_withdrawals(telegram_id)
        
        response = jsonify({
            "success": True,
            "withdrawals": [w.to_dict() for w in withdrawals]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Get withdrawal history error: {str(e)}")
        return jsonify({
            "error": "Failed to get withdrawal history",
            "message": str(e),
            "success": False
        }), 500

@withdraw_bp.route('/api/admin/withdrawals', methods=['GET'])
def get_all_withdrawals_admin():
    """Get all withdrawals for admin"""
    try:
        withdrawals = Withdrawal.get_all_withdrawals()
        
        # Get user information for each withdrawal
        withdrawal_data = []
        for withdrawal in withdrawals:
            withdrawal_dict = withdrawal.to_dict()
            
            # Get user info
            user = User.get_by_telegram_id(withdrawal.telegram_id)
            if user:
                withdrawal_dict['user'] = {
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            else:
                withdrawal_dict['user'] = {
                    'username': 'Unknown',
                    'first_name': 'Unknown',
                    'last_name': 'User'
                }
            
            withdrawal_data.append(withdrawal_dict)
        
        response = jsonify({
            "success": True,
            "withdrawals": withdrawal_data
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Get all withdrawals error: {str(e)}")
        return jsonify({
            "error": "Failed to get withdrawals",
            "message": str(e),
            "success": False
        }), 500

@withdraw_bp.route('/api/admin/withdrawal/update', methods=['POST'])
def update_withdrawal_status():
    """Update withdrawal status (admin only)"""
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        status = data.get('status')
        
        if not withdrawal_id or not status:
            return jsonify({
                "error": "withdrawal_id and status are required",
                "success": False
            }), 400
        
        if status not in ['pending', 'completed', 'rejected']:
            return jsonify({
                "error": "Invalid status",
                "success": False
            }), 400
        
        # Get withdrawal
        response = supabase.table('withdrawals').select('*').eq('id', withdrawal_id).execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({
                "error": "Withdrawal not found",
                "success": False
            }), 404
        
        withdrawal_data = response.data[0]
        withdrawal = Withdrawal(**withdrawal_data)
        
        # Update status
        if withdrawal.update_status(status):
            return jsonify({
                "success": True,
                "withdrawal": withdrawal.to_dict(),
                "message": f"Withdrawal status updated to {status}"
            }), 200
        else:
            return jsonify({
                "error": "Failed to update withdrawal status",
                "success": False
            }), 500
            
    except Exception as e:
        logger.error(f"Update withdrawal status error: {str(e)}")
        return jsonify({
            "error": "Failed to update withdrawal status",
            "message": str(e),
            "success": False
        }), 500


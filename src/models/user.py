from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    coins = db.Column(db.Integer, default=2500)  # Starting with 2.5k coins as mentioned
    energy = db.Column(db.Integer, default=100)
    max_energy = db.Column(db.Integer, default=100)
    last_energy_update = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    tap_power = db.Column(db.Integer, default=1)  # Coins per tap
    energy_regen_rate = db.Column(db.Integer, default=1)  # Energy per minute
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    upi_id = db.Column(db.String(100), nullable=True)
    total_earned = db.Column(db.Integer, default=2500)
    total_withdrawn = db.Column(db.Float, default=0.0)
    
    # Referral system fields
    referred_by = db.Column(db.BigInteger, nullable=True)  # Telegram ID of referrer
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    total_referrals = db.Column(db.Integer, default=0)
    referral_earnings = db.Column(db.Integer, default=0)
    referral_level = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<User {self.telegram_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'coins': self.coins,
            'energy': self.energy,
            'max_energy': self.max_energy,
            'tap_power': self.tap_power,
            'energy_regen_rate': self.energy_regen_rate,
            'upi_id': self.upi_id,
            'total_earned': self.total_earned,
            'total_withdrawn': self.total_withdrawn,
            'referred_by': self.referred_by,
            'referral_code': self.referral_code,
            'total_referrals': self.total_referrals,
            'referral_earnings': self.referral_earnings,
            'referral_level': self.referral_level
        }

    def update_energy(self):
        """Update energy based on time passed since last update"""
        now = datetime.utcnow()
        time_diff = (now - self.last_energy_update).total_seconds() / 60  # minutes
        energy_to_add = int(time_diff * self.energy_regen_rate)
        
        if energy_to_add > 0:
            self.energy = min(self.energy + energy_to_add, self.max_energy)
            self.last_energy_update = now
            self.last_activity = now
            db.session.commit()

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'tap', 'minigame', 'withdrawal', 'upgrade', 'referral'
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

class Upgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    base_cost = db.Column(db.Integer, nullable=False)
    cost_multiplier = db.Column(db.Float, default=1.5)
    effect_type = db.Column(db.String(20), nullable=False)  # 'tap_power', 'energy_regen', 'max_energy'
    effect_value = db.Column(db.Integer, nullable=False)

class UserUpgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    upgrade_id = db.Column(db.Integer, db.ForeignKey('upgrade.id'), nullable=False)
    level = db.Column(db.Integer, default=1)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('upgrades', lazy=True))
    upgrade = db.relationship('Upgrade', backref=db.backref('user_upgrades', lazy=True))

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bonus_paid = db.Column(db.Boolean, default=False)
    total_earnings = db.Column(db.Integer, default=0)
    
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_made')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referral_source')

class WithdrawalRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount_coins = db.Column(db.Integer, nullable=False)  # Amount in coins
    amount_rupees = db.Column(db.Float, nullable=False)  # Amount in rupees before fee
    fee_amount = db.Column(db.Float, nullable=False)  # Processing fee
    final_amount = db.Column(db.Float, nullable=False)  # Final amount after fee
    upi_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', backref=db.backref('withdrawal_requests', lazy=True))


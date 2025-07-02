from flask import Blueprint, request, jsonify, render_template_string
from src.models.user import db, User, Transaction, WithdrawalRequest, Referral
from datetime import datetime, timedelta
import hashlib
import hmac

admin_bp = Blueprint('admin', __name__)

# Simple admin authentication (you should change this password)
ADMIN_PASSWORD = "alphawulf2025admin"

def verify_admin_auth(password):
    """Simple admin authentication"""
    return password == ADMIN_PASSWORD

@admin_bp.route('/admin')
def admin_dashboard():
    """Admin dashboard main page"""
    return render_template_string(ADMIN_DASHBOARD_HTML)

@admin_bp.route('/admin/auth', methods=['POST'])
def admin_auth():
    """Admin authentication endpoint"""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if verify_admin_auth(password):
            return jsonify({'success': True, 'message': 'Authentication successful'})
        else:
            return jsonify({'success': False, 'message': 'Invalid password'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/stats')
def admin_stats():
    """Get overall bot statistics"""
    try:
        # User statistics
        total_users = User.query.count()
        active_users_today = User.query.filter(
            User.last_activity >= datetime.utcnow() - timedelta(days=1)
        ).count()
        active_users_week = User.query.filter(
            User.last_activity >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        # Financial statistics
        total_coins_distributed = db.session.query(db.func.sum(User.total_earned)).scalar() or 0
        total_withdrawn = db.session.query(db.func.sum(User.total_withdrawn)).scalar() or 0
        pending_withdrawals = WithdrawalRequest.query.filter_by(status='pending').count()
        pending_withdrawal_amount = db.session.query(
            db.func.sum(WithdrawalRequest.final_amount)
        ).filter_by(status='pending').scalar() or 0
        
        # Referral statistics
        total_referrals = Referral.query.count()
        referral_earnings = db.session.query(db.func.sum(User.referral_earnings)).scalar() or 0
        
        return jsonify({
            'success': True,
            'stats': {
                'users': {
                    'total': total_users,
                    'active_today': active_users_today,
                    'active_week': active_users_week
                },
                'financial': {
                    'total_coins_distributed': total_coins_distributed,
                    'total_withdrawn': total_withdrawn,
                    'pending_withdrawals': pending_withdrawals,
                    'pending_withdrawal_amount': pending_withdrawal_amount
                },
                'referrals': {
                    'total_referrals': total_referrals,
                    'referral_earnings': referral_earnings
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/users')
def admin_users():
    """Get all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        users = User.query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        user_list = []
        for user in users.items:
            user_data = user.to_dict()
            user_data['referrals_count'] = Referral.query.filter_by(referrer_id=user.id).count()
            user_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': user_list,
            'pagination': {
                'page': page,
                'pages': users.pages,
                'per_page': per_page,
                'total': users.total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/withdrawals')
def admin_withdrawals():
    """Get all withdrawal requests"""
    try:
        status = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = WithdrawalRequest.query
        if status != 'all':
            query = query.filter_by(status=status)
            
        withdrawals = query.order_by(WithdrawalRequest.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        withdrawal_list = []
        for withdrawal in withdrawals.items:
            withdrawal_data = {
                'id': withdrawal.id,
                'user_id': withdrawal.user_id,
                'user_name': withdrawal.user.first_name or withdrawal.user.username,
                'telegram_id': withdrawal.user.telegram_id,
                'amount_coins': withdrawal.amount_coins,
                'amount_rupees': withdrawal.amount_rupees,
                'fee_amount': withdrawal.fee_amount,
                'final_amount': withdrawal.final_amount,
                'upi_id': withdrawal.upi_id,
                'status': withdrawal.status,
                'created_at': withdrawal.created_at.isoformat(),
                'processed_at': withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
                'admin_notes': withdrawal.admin_notes
            }
            withdrawal_list.append(withdrawal_data)
        
        return jsonify({
            'success': True,
            'withdrawals': withdrawal_list,
            'pagination': {
                'page': page,
                'pages': withdrawals.pages,
                'per_page': per_page,
                'total': withdrawals.total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/withdrawal/<int:withdrawal_id>/process', methods=['POST'])
def process_withdrawal(withdrawal_id):
    """Process a withdrawal request (approve/reject)"""
    try:
        data = request.get_json()
        action = data.get('action')  # 'approve' or 'reject'
        admin_notes = data.get('admin_notes', '')
        
        withdrawal = WithdrawalRequest.query.get_or_404(withdrawal_id)
        
        if action == 'approve':
            withdrawal.status = 'completed'
            withdrawal.processed_at = datetime.utcnow()
            withdrawal.admin_notes = admin_notes
            
            # Update user's total withdrawn amount
            user = withdrawal.user
            user.total_withdrawn += withdrawal.final_amount
            
        elif action == 'reject':
            withdrawal.status = 'failed'
            withdrawal.processed_at = datetime.utcnow()
            withdrawal.admin_notes = admin_notes
            
            # Refund coins to user
            user = withdrawal.user
            user.coins += withdrawal.amount_coins
            
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Withdrawal {action}d successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/referrals')
def admin_referrals():
    """Get referral statistics and chains"""
    try:
        # Top referrers
        top_referrers = db.session.query(
            User.telegram_id,
            User.first_name,
            User.username,
            User.total_referrals,
            User.referral_earnings
        ).filter(User.total_referrals > 0).order_by(User.total_referrals.desc()).limit(10).all()
        
        # Recent referrals
        recent_referrals = db.session.query(
            Referral,
            User.first_name.label('referrer_name'),
            User.username.label('referrer_username')
        ).join(User, Referral.referrer_id == User.id).order_by(Referral.created_at.desc()).limit(20).all()
        
        referrer_list = []
        for referrer in top_referrers:
            referrer_list.append({
                'telegram_id': referrer.telegram_id,
                'name': referrer.first_name or referrer.username,
                'total_referrals': referrer.total_referrals,
                'referral_earnings': referrer.referral_earnings
            })
        
        recent_list = []
        for referral, referrer_name, referrer_username in recent_referrals:
            recent_list.append({
                'id': referral.id,
                'referrer_name': referrer_name or referrer_username,
                'created_at': referral.created_at.isoformat(),
                'bonus_paid': referral.bonus_paid,
                'total_earnings': referral.total_earnings
            })
        
        return jsonify({
            'success': True,
            'top_referrers': referrer_list,
            'recent_referrals': recent_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/user/<int:telegram_id>')
def admin_user_details(telegram_id):
    """Get detailed information about a specific user"""
    try:
        user = User.query.filter_by(telegram_id=telegram_id).first_or_404()
        
        # Get user's transactions
        transactions = Transaction.query.filter_by(user_id=user.id).order_by(
            Transaction.created_at.desc()
        ).limit(50).all()
        
        # Get user's referrals
        referrals = Referral.query.filter_by(referrer_id=user.id).all()
        
        # Get user's withdrawal requests
        withdrawals = WithdrawalRequest.query.filter_by(user_id=user.id).order_by(
            WithdrawalRequest.created_at.desc()
        ).all()
        
        user_data = user.to_dict()
        user_data['transactions'] = [
            {
                'id': t.id,
                'type': t.transaction_type,
                'amount': t.amount,
                'description': t.description,
                'created_at': t.created_at.isoformat()
            } for t in transactions
        ]
        user_data['referrals'] = [
            {
                'id': r.id,
                'referred_id': r.referred_id,
                'created_at': r.created_at.isoformat(),
                'bonus_paid': r.bonus_paid,
                'total_earnings': r.total_earnings
            } for r in referrals
        ]
        user_data['withdrawals'] = [
            {
                'id': w.id,
                'amount_coins': w.amount_coins,
                'final_amount': w.final_amount,
                'status': w.status,
                'created_at': w.created_at.isoformat()
            } for w in withdrawals
        ]
        
        return jsonify({
            'success': True,
            'user': user_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Admin Dashboard HTML Template
ADMIN_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha Wulf - Admin Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #FFD700;
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 215, 0, 0.1);
            border: 2px solid #FFD700;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }

        .title {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .subtitle {
            font-size: 16px;
            color: #DAA520;
        }

        .auth-section {
            max-width: 400px;
            margin: 50px auto;
            padding: 30px;
            background: rgba(255, 215, 0, 0.1);
            border: 2px solid #FFD700;
            border-radius: 15px;
            text-align: center;
        }

        .auth-input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            background: rgba(0, 0, 0, 0.3);
            border: 2px solid #FFD700;
            border-radius: 8px;
            color: #FFD700;
            font-size: 16px;
        }

        .auth-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
            border: none;
            border-radius: 8px;
            color: #1a1a1a;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .auth-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4);
        }

        .dashboard {
            display: none;
        }

        .nav-tabs {
            display: flex;
            margin-bottom: 20px;
            background: rgba(255, 215, 0, 0.1);
            border-radius: 10px;
            padding: 5px;
        }

        .nav-tab {
            flex: 1;
            padding: 12px;
            text-align: center;
            background: transparent;
            border: none;
            color: #DAA520;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
        }

        .nav-tab.active {
            background: #FFD700;
            color: #1a1a1a;
            font-weight: bold;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255, 215, 0, 0.1);
            border: 2px solid #FFD700;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 14px;
            color: #DAA520;
        }

        .data-table {
            width: 100%;
            background: rgba(255, 215, 0, 0.1);
            border: 2px solid #FFD700;
            border-radius: 15px;
            overflow: hidden;
        }

        .data-table th,
        .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 215, 0, 0.2);
        }

        .data-table th {
            background: rgba(255, 215, 0, 0.2);
            font-weight: bold;
        }

        .action-button {
            padding: 6px 12px;
            margin: 2px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.3s ease;
        }

        .approve-btn {
            background: #28a745;
            color: white;
        }

        .reject-btn {
            background: #dc3545;
            color: white;
        }

        .view-btn {
            background: #007bff;
            color: white;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #DAA520;
        }

        .error {
            background: rgba(220, 53, 69, 0.2);
            border: 2px solid #dc3545;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            color: #ff6b6b;
        }

        @media (max-width: 768px) {
            .nav-tabs {
                flex-direction: column;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">🐺 Alpha Wulf Admin Dashboard</div>
            <div class="subtitle">Monitor and control your bot empire</div>
        </div>

        <!-- Authentication Section -->
        <div id="authSection" class="auth-section">
            <h3>Admin Authentication</h3>
            <input type="password" id="adminPassword" class="auth-input" placeholder="Enter admin password">
            <button onclick="authenticate()" class="auth-button">Login</button>
            <div id="authError" class="error" style="display: none;"></div>
        </div>

        <!-- Dashboard Section -->
        <div id="dashboard" class="dashboard">
            <div class="nav-tabs">
                <button class="nav-tab active" onclick="showTab('overview')">Overview</button>
                <button class="nav-tab" onclick="showTab('users')">Users</button>
                <button class="nav-tab" onclick="showTab('withdrawals')">Withdrawals</button>
                <button class="nav-tab" onclick="showTab('referrals')">Referrals</button>
            </div>

            <!-- Overview Tab -->
            <div id="overview" class="tab-content active">
                <div class="stats-grid" id="statsGrid">
                    <div class="loading">Loading statistics...</div>
                </div>
            </div>

            <!-- Users Tab -->
            <div id="users" class="tab-content">
                <div id="usersContent">
                    <div class="loading">Loading users...</div>
                </div>
            </div>

            <!-- Withdrawals Tab -->
            <div id="withdrawals" class="tab-content">
                <div id="withdrawalsContent">
                    <div class="loading">Loading withdrawals...</div>
                </div>
            </div>

            <!-- Referrals Tab -->
            <div id="referrals" class="tab-content">
                <div id="referralsContent">
                    <div class="loading">Loading referrals...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isAuthenticated = false;

        async function authenticate() {
            const password = document.getElementById('adminPassword').value;
            const errorDiv = document.getElementById('authError');
            
            try {
                const response = await fetch('/admin/auth', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    isAuthenticated = true;
                    document.getElementById('authSection').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'block';
                    loadOverviewData();
                } else {
                    errorDiv.textContent = data.message;
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Authentication failed: ' + error.message;
                errorDiv.style.display = 'block';
            }
        }

        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all nav tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // Load data for the selected tab
            switch(tabName) {
                case 'overview':
                    loadOverviewData();
                    break;
                case 'users':
                    loadUsersData();
                    break;
                case 'withdrawals':
                    loadWithdrawalsData();
                    break;
                case 'referrals':
                    loadReferralsData();
                    break;
            }
        }

        async function loadOverviewData() {
            try {
                const response = await fetch('/admin/stats');
                const data = await response.json();
                
                if (data.success) {
                    const stats = data.stats;
                    document.getElementById('statsGrid').innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${stats.users.total}</div>
                            <div class="stat-label">Total Users</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.users.active_today}</div>
                            <div class="stat-label">Active Today</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.users.active_week}</div>
                            <div class="stat-label">Active This Week</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.financial.total_coins_distributed.toLocaleString()}</div>
                            <div class="stat-label">Total Coins Distributed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">₹${stats.financial.total_withdrawn.toFixed(2)}</div>
                            <div class="stat-label">Total Withdrawn</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.financial.pending_withdrawals}</div>
                            <div class="stat-label">Pending Withdrawals</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">₹${stats.financial.pending_withdrawal_amount.toFixed(2)}</div>
                            <div class="stat-label">Pending Amount</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.referrals.total_referrals}</div>
                            <div class="stat-label">Total Referrals</div>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('statsGrid').innerHTML = '<div class="error">Failed to load statistics</div>';
            }
        }

        async function loadUsersData() {
            try {
                const response = await fetch('/admin/users');
                const data = await response.json();
                
                if (data.success) {
                    let html = '<table class="data-table"><thead><tr>';
                    html += '<th>Telegram ID</th><th>Name</th><th>Coins</th><th>Referrals</th><th>Last Activity</th><th>Actions</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.users.forEach(user => {
                        html += `<tr>
                            <td>${user.telegram_id}</td>
                            <td>${user.first_name || user.username || 'N/A'}</td>
                            <td>${user.coins.toLocaleString()}</td>
                            <td>${user.referrals_count}</td>
                            <td>${new Date(user.last_activity).toLocaleDateString()}</td>
                            <td><button class="action-button view-btn" onclick="viewUser(${user.telegram_id})">View</button></td>
                        </tr>`;
                    });
                    
                    html += '</tbody></table>';
                    document.getElementById('usersContent').innerHTML = html;
                }
            } catch (error) {
                document.getElementById('usersContent').innerHTML = '<div class="error">Failed to load users</div>';
            }
        }

        async function loadWithdrawalsData() {
            try {
                const response = await fetch('/admin/withdrawals');
                const data = await response.json();
                
                if (data.success) {
                    let html = '<table class="data-table"><thead><tr>';
                    html += '<th>ID</th><th>User</th><th>Amount</th><th>UPI ID</th><th>Status</th><th>Date</th><th>Actions</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.withdrawals.forEach(withdrawal => {
                        html += `<tr>
                            <td>${withdrawal.id}</td>
                            <td>${withdrawal.user_name}</td>
                            <td>₹${withdrawal.final_amount.toFixed(2)}</td>
                            <td>${withdrawal.upi_id}</td>
                            <td>${withdrawal.status}</td>
                            <td>${new Date(withdrawal.created_at).toLocaleDateString()}</td>
                            <td>`;
                        
                        if (withdrawal.status === 'pending') {
                            html += `<button class="action-button approve-btn" onclick="processWithdrawal(${withdrawal.id}, 'approve')">Approve</button>`;
                            html += `<button class="action-button reject-btn" onclick="processWithdrawal(${withdrawal.id}, 'reject')">Reject</button>`;
                        }
                        
                        html += `</td></tr>`;
                    });
                    
                    html += '</tbody></table>';
                    document.getElementById('withdrawalsContent').innerHTML = html;
                }
            } catch (error) {
                document.getElementById('withdrawalsContent').innerHTML = '<div class="error">Failed to load withdrawals</div>';
            }
        }

        async function loadReferralsData() {
            try {
                const response = await fetch('/admin/referrals');
                const data = await response.json();
                
                if (data.success) {
                    let html = '<h3>Top Referrers</h3>';
                    html += '<table class="data-table"><thead><tr>';
                    html += '<th>Name</th><th>Total Referrals</th><th>Earnings</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.top_referrers.forEach(referrer => {
                        html += `<tr>
                            <td>${referrer.name}</td>
                            <td>${referrer.total_referrals}</td>
                            <td>${referrer.referral_earnings} coins</td>
                        </tr>`;
                    });
                    
                    html += '</tbody></table>';
                    document.getElementById('referralsContent').innerHTML = html;
                }
            } catch (error) {
                document.getElementById('referralsContent').innerHTML = '<div class="error">Failed to load referrals</div>';
            }
        }

        async function processWithdrawal(withdrawalId, action) {
            const notes = prompt(`Enter admin notes for ${action}ing this withdrawal:`);
            if (notes === null) return;
            
            try {
                const response = await fetch(`/admin/withdrawal/${withdrawalId}/process`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: action,
                        admin_notes: notes
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    loadWithdrawalsData(); // Reload the withdrawals table
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Failed to process withdrawal: ' + error.message);
            }
        }

        function viewUser(telegramId) {
            // This could open a modal or navigate to a detailed user page
            alert(`View user details for Telegram ID: ${telegramId}`);
        }

        // Handle Enter key in password field
        document.getElementById('adminPassword').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                authenticate();
            }
        });
    </script>
</body>
</html>
'''


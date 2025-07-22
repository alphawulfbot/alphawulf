from flask import Blueprint, request, jsonify, render_template_string
from datetime import datetime, timezone, timedelta
import logging
from src.models.user import User
from src.config.database import supabase

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

# Simple admin authentication (in production, use proper authentication)
ADMIN_PASSWORD = "alphawulf2024"

@admin_bp.route('/admin', methods=['GET'])
def admin_dashboard():
    """Admin dashboard HTML page"""
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha Wulf Admin Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #ffffff;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(0, 0, 0, 0.3);
            padding: 1rem 2rem;
            border-bottom: 2px solid #ffd700;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            font-weight: bold;
            color: #ffd700;
        }
        
        .nav-buttons {
            display: flex;
            gap: 1rem;
        }
        
        .nav-btn {
            padding: 0.5rem 1rem;
            background: #ffd700;
            color: #000;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .nav-btn:hover {
            background: #ffed4e;
            transform: translateY(-2px);
        }
        
        .nav-btn.active {
            background: #ff6b35;
            color: #fff;
        }
        
        .container {
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: rgba(255, 215, 0, 0.1);
            border: 1px solid #ffd700;
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #ffd700;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            color: #ccc;
            font-size: 0.9rem;
        }
        
        .section {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid #333;
        }
        
        .section-title {
            color: #ffd700;
            font-size: 1.3rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #ffd700;
            padding-bottom: 0.5rem;
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        
        .table th,
        .table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        
        .table th {
            background: rgba(255, 215, 0, 0.1);
            color: #ffd700;
            font-weight: bold;
        }
        
        .table tr:hover {
            background: rgba(255, 215, 0, 0.05);
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9rem;
            margin: 0.2rem;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: #007bff;
            color: white;
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-warning {
            background: #ffc107;
            color: #000;
        }
        
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #ffd700;
        }
        
        .error {
            background: rgba(220, 53, 69, 0.1);
            border: 1px solid #dc3545;
            color: #dc3545;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }
        
        .success {
            background: rgba(40, 167, 69, 0.1);
            border: 1px solid #28a745;
            color: #28a745;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }
        
        .hidden {
            display: none;
        }
        
        .refresh-btn {
            background: #17a2b8;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 1rem;
        }
        
        .refresh-btn:hover {
            background: #138496;
        }
        
        .status-pending {
            color: #ffc107;
            font-weight: bold;
        }
        
        .status-completed {
            color: #28a745;
            font-weight: bold;
        }
        
        .status-rejected {
            color: #dc3545;
            font-weight: bold;
        }
        
        .user-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .coin-input {
            width: 80px;
            padding: 0.3rem;
            border: 1px solid #333;
            border-radius: 3px;
            background: #2d2d2d;
            color: #fff;
            margin-right: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            🐺 Alpha Wulf Admin
        </div>
        <div class="nav-buttons">
            <button class="nav-btn active" onclick="showSection('dashboard')">Dashboard</button>
            <button class="nav-btn" onclick="showSection('users')">Users</button>
            <button class="nav-btn" onclick="showSection('withdrawals')">Withdrawals</button>
            <button class="nav-btn" onclick="logout()">Logout</button>
        </div>
    </div>
    
    <div class="container">
        <!-- Dashboard Section -->
        <div id="dashboard-section" class="section">
            <div class="section-title">Dashboard Overview</div>
            <div class="stats-grid" id="stats-grid">
                <div class="loading">Loading statistics...</div>
            </div>
            <button class="refresh-btn" onclick="loadStats()">🔄 Refresh Stats</button>
        </div>
        
        <!-- Users Section -->
        <div id="users-section" class="section hidden">
            <div class="section-title">User Management</div>
            <button class="refresh-btn" onclick="loadUsers()">🔄 Refresh Users</button>
            <div id="users-content">
                <div class="loading">Loading users...</div>
            </div>
        </div>
        
        <!-- Withdrawals Section -->
        <div id="withdrawals-section" class="section hidden">
            <div class="section-title">Withdrawal Management</div>
            <button class="refresh-btn" onclick="loadWithdrawals()">🔄 Refresh Withdrawals</button>
            <div id="withdrawals-content">
                <div class="loading">Loading withdrawals...</div>
            </div>
        </div>
    </div>
    
    <script>
        let currentSection = 'dashboard';
        
        // Show/hide sections
        function showSection(section) {
            // Hide all sections
            document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            
            // Show selected section
            document.getElementById(section + '-section').classList.remove('hidden');
            event.target.classList.add('active');
            
            currentSection = section;
            
            // Load data for the section
            if (section === 'dashboard') {
                loadStats();
            } else if (section === 'users') {
                loadUsers();
            } else if (section === 'withdrawals') {
                loadWithdrawals();
            }
        }
        
        // Load statistics
        async function loadStats() {
            try {
                const response = await fetch('/api/admin/stats');
                const data = await response.json();
                
                if (data.success) {
                    const statsGrid = document.getElementById('stats-grid');
                    statsGrid.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.total_users}</div>
                            <div class="stat-label">Total Users</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.active_users}</div>
                            <div class="stat-label">Active Users (24h)</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.total_coins.toLocaleString()}</div>
                            <div class="stat-label">Total Coins</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.total_withdrawals}</div>
                            <div class="stat-label">Total Withdrawals</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.pending_withdrawals}</div>
                            <div class="stat-label">Pending Withdrawals</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">₹${data.stats.total_withdrawn}</div>
                            <div class="stat-label">Total Withdrawn</div>
                        </div>
                    `;
                } else {
                    document.getElementById('stats-grid').innerHTML = `<div class="error">Error loading stats: ${data.message}</div>`;
                }
            } catch (error) {
                document.getElementById('stats-grid').innerHTML = `<div class="error">Error loading stats: ${error.message}</div>`;
            }
        }
        
        // Load users
        async function loadUsers() {
            try {
                const response = await fetch('/api/admin/users');
                const data = await response.json();
                
                if (data.success) {
                    const usersContent = document.getElementById('users-content');
                    
                    if (data.users.length === 0) {
                        usersContent.innerHTML = '<div class="loading">No users found</div>';
                        return;
                    }
                    
                    let tableHTML = `
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Username</th>
                                    <th>Name</th>
                                    <th>Coins</th>
                                    <th>Energy</th>
                                    <th>Tap Power</th>
                                    <th>Referrals</th>
                                    <th>Last Active</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    
                    data.users.forEach(user => {
                        const lastActive = user.last_active ? new Date(user.last_active).toLocaleString() : 'Never';
                        tableHTML += `
                            <tr>
                                <td>${user.telegram_id}</td>
                                <td>@${user.username || 'N/A'}</td>
                                <td>${user.first_name} ${user.last_name || ''}</td>
                                <td>${user.coins.toLocaleString()}</td>
                                <td>${user.energy}</td>
                                <td>${user.tap_power}</td>
                                <td>${user.referrals}</td>
                                <td>${lastActive}</td>
                                <td class="user-actions">
                                    <input type="number" class="coin-input" id="coins-${user.telegram_id}" placeholder="Amount">
                                    <button class="btn btn-success" onclick="adjustCoins(${user.telegram_id}, 'add')">Add</button>
                                    <button class="btn btn-warning" onclick="adjustCoins(${user.telegram_id}, 'subtract')">Sub</button>
                                    <button class="btn btn-primary" onclick="resetUser(${user.telegram_id})">Reset</button>
                                    <button class="btn btn-danger" onclick="deleteUser(${user.telegram_id})">Delete</button>
                                </td>
                            </tr>
                        `;
                    });
                    
                    tableHTML += '</tbody></table>';
                    usersContent.innerHTML = tableHTML;
                } else {
                    document.getElementById('users-content').innerHTML = `<div class="error">Error loading users: ${data.message}</div>`;
                }
            } catch (error) {
                document.getElementById('users-content').innerHTML = `<div class="error">Error loading users: ${error.message}</div>`;
            }
        }
        
        // Load withdrawals
        async function loadWithdrawals() {
            try {
                const response = await fetch('/api/admin/withdrawals');
                const data = await response.json();
                
                if (data.success) {
                    const withdrawalsContent = document.getElementById('withdrawals-content');
                    
                    if (data.withdrawals.length === 0) {
                        withdrawalsContent.innerHTML = '<div class="loading">No withdrawals found</div>';
                        return;
                    }
                    
                    let tableHTML = `
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>User</th>
                                    <th>Amount</th>
                                    <th>Final Amount</th>
                                    <th>UPI ID</th>
                                    <th>Date</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    
                    data.withdrawals.forEach(withdrawal => {
                        const createdAt = new Date(withdrawal.created_at).toLocaleString();
                        const userName = withdrawal.user ? `${withdrawal.user.first_name} ${withdrawal.user.last_name || ''}` : 'Unknown';
                        const statusClass = `status-${withdrawal.status}`;
                        
                        tableHTML += `
                            <tr>
                                <td>${withdrawal.id}</td>
                                <td>${userName}<br><small>@${withdrawal.user?.username || 'N/A'}</small></td>
                                <td>${withdrawal.amount} coins</td>
                                <td>₹${withdrawal.final_amount}</td>
                                <td>${withdrawal.upi_id}</td>
                                <td>${createdAt}</td>
                                <td class="${statusClass}">${withdrawal.status.toUpperCase()}</td>
                                <td>
                                    ${withdrawal.status === 'pending' ? `
                                        <button class="btn btn-success" onclick="updateWithdrawalStatus(${withdrawal.id}, 'completed')">Approve</button>
                                        <button class="btn btn-danger" onclick="updateWithdrawalStatus(${withdrawal.id}, 'rejected')">Reject</button>
                                    ` : `<span class="${statusClass}">${withdrawal.status.toUpperCase()}</span>`}
                                </td>
                            </tr>
                        `;
                    });
                    
                    tableHTML += '</tbody></table>';
                    withdrawalsContent.innerHTML = tableHTML;
                } else {
                    document.getElementById('withdrawals-content').innerHTML = `<div class="error">Error loading withdrawals: ${data.message}</div>`;
                }
            } catch (error) {
                document.getElementById('withdrawals-content').innerHTML = `<div class="error">Error loading withdrawals: ${error.message}</div>`;
            }
        }
        
        // Adjust user coins
        async function adjustCoins(telegramId, action) {
            const input = document.getElementById(`coins-${telegramId}`);
            const amount = parseInt(input.value);
            
            if (!amount || amount <= 0) {
                alert('Please enter a valid amount');
                return;
            }
            
            try {
                const response = await fetch('/api/admin/user/coins', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        telegram_id: telegramId,
                        action: action,
                        amount: amount
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    input.value = '';
                    loadUsers(); // Refresh users list
                    alert(`Successfully ${action}ed ${amount} coins`);
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        // Reset user
        async function resetUser(telegramId) {
            if (!confirm('Are you sure you want to reset this user? This will set their coins to 2500, energy to 100, and tap power to 1.')) {
                return;
            }
            
            try {
                const response = await fetch('/api/admin/user/reset', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        telegram_id: telegramId
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    loadUsers(); // Refresh users list
                    alert('User reset successfully');
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        // Delete user
        async function deleteUser(telegramId) {
            if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
                return;
            }
            
            try {
                const response = await fetch('/api/admin/user/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        telegram_id: telegramId
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    loadUsers(); // Refresh users list
                    alert('User deleted successfully');
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        // Update withdrawal status
        async function updateWithdrawalStatus(withdrawalId, status) {
            try {
                const response = await fetch('/api/admin/withdrawal/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        withdrawal_id: withdrawalId,
                        status: status
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    loadWithdrawals(); // Refresh withdrawals list
                    alert(`Withdrawal ${status} successfully`);
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        // Logout
        function logout() {
            if (confirm('Are you sure you want to logout?')) {
                window.location.href = '/admin/login';
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (currentSection === 'dashboard') {
                loadStats();
            }
        }, 30000);
        
        // Load initial data
        loadStats();
    </script>
</body>
</html>
    """
    return render_template_string(html_template)

@admin_bp.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get admin statistics"""
    try:
        # Get all users
        users = User.get_all_users()
        
        # Calculate stats
        total_users = len(users)
        total_coins = sum(user.coins for user in users)
        
        # Active users (last 24 hours)
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        active_users = sum(1 for user in users if user.last_active and user.last_active > yesterday)
        
        # Get withdrawal stats
        try:
            withdrawals_response = supabase.table('withdrawals').select('*').execute()
            withdrawals = withdrawals_response.data or []
            
            total_withdrawals = len(withdrawals)
            pending_withdrawals = sum(1 for w in withdrawals if w.get('status') == 'pending')
            total_withdrawn = sum(w.get('final_amount', 0) for w in withdrawals if w.get('status') == 'completed')
        except Exception as e:
            logger.error(f"Error getting withdrawal stats: {str(e)}")
            total_withdrawals = 0
            pending_withdrawals = 0
            total_withdrawn = 0
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_coins': total_coins,
            'total_withdrawals': total_withdrawals,
            'pending_withdrawals': pending_withdrawals,
            'total_withdrawn': total_withdrawn
        }
        
        logger.info(f"Stats: {total_users} users, {active_users} active, {total_coins} coins, {total_withdrawals} withdrawals")
        
        response = jsonify({
            "success": True,
            "stats": stats
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        return jsonify({
            "error": "Failed to get stats",
            "message": str(e),
            "success": False
        }), 500

@admin_bp.route('/api/admin/users', methods=['GET'])
def get_all_users():
    """Get all users for admin"""
    try:
        users = User.get_all_users()
        
        users_data = []
        for user in users:
            users_data.append(user.to_dict())
        
        response = jsonify({
            "success": True,
            "users": users_data
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        return jsonify({
            "error": "Failed to get users",
            "message": str(e),
            "success": False
        }), 500

@admin_bp.route('/api/admin/user/coins', methods=['POST'])
def adjust_user_coins():
    """Adjust user coins (admin only)"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        action = data.get('action')  # 'add' or 'subtract'
        amount = data.get('amount')
        
        if not telegram_id or not action or not amount:
            return jsonify({
                "error": "telegram_id, action, and amount are required",
                "success": False
            }), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                "error": "User not found",
                "success": False
            }), 404
        
        amount = int(float(amount))
        
        if action == 'add':
            success = user.add_coins(amount)
            message = f"Added {amount} coins"
        elif action == 'subtract':
            success = user.subtract_coins(amount)
            message = f"Subtracted {amount} coins"
        else:
            return jsonify({
                "error": "Invalid action",
                "success": False
            }), 400
        
        if success:
            return jsonify({
                "success": True,
                "user": user.to_dict(),
                "message": message
            }), 200
        else:
            return jsonify({
                "error": "Failed to adjust coins",
                "success": False
            }), 500
            
    except Exception as e:
        logger.error(f"Error adjusting user coins: {str(e)}")
        return jsonify({
            "error": "Failed to adjust coins",
            "message": str(e),
            "success": False
        }), 500

@admin_bp.route('/api/admin/user/reset', methods=['POST'])
def reset_user():
    """Reset user data (admin only)"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({
                "error": "telegram_id is required",
                "success": False
            }), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                "error": "User not found",
                "success": False
            }), 404
        
        if user.reset_user_data():
            return jsonify({
                "success": True,
                "user": user.to_dict(),
                "message": "User data reset successfully"
            }), 200
        else:
            return jsonify({
                "error": "Failed to reset user data",
                "success": False
            }), 500
            
    except Exception as e:
        logger.error(f"Error resetting user: {str(e)}")
        return jsonify({
            "error": "Failed to reset user",
            "message": str(e),
            "success": False
        }), 500

@admin_bp.route('/api/admin/user/delete', methods=['POST'])
def delete_user():
    """Delete user (admin only)"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({
                "error": "telegram_id is required",
                "success": False
            }), 400
        
        user = User.get_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                "error": "User not found",
                "success": False
            }), 404
        
        if user.delete():
            return jsonify({
                "success": True,
                "message": "User deleted successfully"
            }), 200
        else:
            return jsonify({
                "error": "Failed to delete user",
                "success": False
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({
            "error": "Failed to delete user",
            "message": str(e),
            "success": False
        }), 500


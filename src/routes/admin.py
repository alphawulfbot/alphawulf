from flask import Blueprint, request, jsonify, render_template_string
from src.models.user import User, Transaction, Upgrade
from datetime import datetime, timedelta
import hashlib
import hmac
import os

admin_bp = Blueprint('admin', __name__)

# Simple admin authentication (you should change this password)
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'alphawulf2025admin')

def verify_admin_auth(password):
    """Simple admin authentication"""
    return password == ADMIN_PASSWORD

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha Wulf Admin Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #0056b3; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-card h3 { margin-top: 0; color: #007bff; }
        .stat-card p { font-size: 1.5em; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #007bff; color: white; }
        .auth-section { margin-bottom: 20px; }
        .auth-section input { padding: 8px; margin-right: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .auth-section button { padding: 8px 15px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .auth-section button:hover { background-color: #218838; }
        #auth-message { margin-top: 10px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Alpha Wulf Admin Dashboard</h1>

        <div id="auth-section" class="auth-section">
            <input type="password" id="admin-password" placeholder="Admin Password">
            <button onclick="authenticateAdmin()">Login</button>
            <p id="auth-message"></p>
        </div>

        <div id="dashboard-content" style="display:none;">
            <h2>Overall Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <p id="total-users">Loading...</p>
                </div>
                <div class="stat-card">
                    <h3>Total Coins in Circulation</h3>
                    <p id="total-coins">Loading...</p>
                </div>
                <div class="stat-card">
                    <h3>Total Taps</h3>
                    <p id="total-taps">Loading...</p>
                </div>
            </div>

            <h2>User List</h2>
            <table>
                <thead>
                    <tr>
                        <th>Telegram ID</th>
                        <th>Name</th>
                        <th>Username</th>
                        <th>Coins</th>
                        <th>Energy</th>
                        <th>Tap Power</th>
                        <th>Referrals</th>
                    </tr>
                </thead>
                <tbody id="user-list-body">
                    <!-- User data will be loaded here -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const ADMIN_API_BASE = '/admin/api';

        async function authenticateAdmin() {
            const password = document.getElementById('admin-password').value;
            const authMessage = document.getElementById('auth-message');
            try {
                const response = await fetch(`${ADMIN_API_BASE}/auth`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: password })
                });
                const data = await response.json();
                if (data.success) {
                    authMessage.textContent = data.message;
                    authMessage.style.color = 'green';
                    document.getElementById('auth-section').style.display = 'none';
                    document.getElementById('dashboard-content').style.display = 'block';
                    loadDashboardData();
                } else {
                    authMessage.textContent = data.message;
                    authMessage.style.color = 'red';
                }
            } catch (error) {
                authMessage.textContent = 'Error during authentication.';
                authMessage.style.color = 'red';
                console.error('Authentication error:', error);
            }
        }

        async function loadDashboardData() {
            try {
                // Load stats
                const statsResponse = await fetch(`${ADMIN_API_BASE}/stats`);
                const statsData = await statsResponse.json();
                if (statsData.success) {
                    document.getElementById('total-users').textContent = statsData.stats.total_users.toLocaleString();
                    document.getElementById('total-coins').textContent = statsData.stats.total_coins.toLocaleString();
                    document.getElementById('total-taps').textContent = statsData.stats.total_taps.toLocaleString();
                } else {
                    console.error('Failed to load stats:', statsData.message);
                }

                // Load user list
                const usersResponse = await fetch(`${ADMIN_API_BASE}/users`);
                const usersData = await usersResponse.json();
                const userListBody = document.getElementById('user-list-body');
                userListBody.innerHTML = ''; // Clear existing rows
                if (Array.isArray(usersData)) {
                    usersData.forEach(user => {
                        const row = userListBody.insertRow();
                        row.insertCell().textContent = user.telegram_id;
                        row.insertCell().textContent = `${user.first_name || ''} ${user.last_name || ''}`.trim();
                        row.insertCell().textContent = user.username || 'N/A';
                        row.insertCell().textContent = user.coins.toLocaleString();
                        row.insertCell().textContent = `${user.energy}/${user.max_energy}`;
                        row.insertCell().textContent = user.tap_power;
                        row.insertCell().textContent = user.referral_count;
                    });
                } else {
                    console.error('Failed to load users:', usersData.message);
                }

            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }
    </script>
</body>
</html>
"""

@admin_bp.route('/admin')
def admin_dashboard():
    """Admin dashboard main page"""
    return render_template_string(ADMIN_DASHBOARD_HTML)

@admin_bp.route('/admin/api/auth', methods=['POST'])
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

@admin_bp.route('/admin/api/stats', methods=['GET'])
def admin_api_stats():
    """API endpoint for admin statistics"""
    try:
        stats = User.get_user_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/api/users', methods=['GET'])
def admin_api_users():
    """API endpoint for user list"""
    try:
        users = User.get_all_users()
        return jsonify(users)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

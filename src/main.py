import os
import logging
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure CORS to allow all origins and methods
    CORS(app, 
         origins=['*'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'Access-Control-Allow-Credentials'],
         supports_credentials=True)
    
    # Import and register all blueprints
    try:
        # Import blueprints
        from src.routes.auth import auth_bp
        from src.routes.user import user_bp
        from src.routes.admin import admin_bp
        from src.routes.withdraw import withdraw_bp
        from src.routes.upgrades import upgrades_bp
        
        # Register blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(withdraw_bp)
        app.register_blueprint(upgrades_bp)
        
        logger.info("All blueprints registered successfully")
        
    except ImportError as e:
        logger.error(f"Error importing blueprints: {str(e)}")
        # Create minimal auth blueprint if import fails
        from flask import Blueprint
        
        auth_bp = Blueprint('auth', __name__)
        
        @auth_bp.route('/api/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'timestamp': int(datetime.now(timezone.utc).timestamp()),
                'service': 'Alpha Wulf Backend'
            })
        
        @auth_bp.route('/api/auth', methods=['POST', 'OPTIONS'])
        def auth():
            if request.method == 'OPTIONS':
                response = jsonify({'status': 'ok'})
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
                response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
                return response
            
            try:
                data = request.get_json()
                telegram_id = data.get('telegram_id')
                username = data.get('username')
                first_name = data.get('first_name')
                
                # Return success response with user data
                return jsonify({
                    'success': True,
                    'user': {
                        'telegram_id': telegram_id,
                        'username': username,
                        'first_name': first_name,
                        'coins': 2500,
                        'energy': 100,
                        'tap_power': 1
                    }
                })
                
            except Exception as e:
                logger.error(f"Auth error: {str(e)}")
                return jsonify({'error': 'Authentication failed'}), 500
        
        app.register_blueprint(auth_bp)
        logger.info("Minimal auth blueprint registered as fallback")
    
    # Root route
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Alpha Wulf Backend API',
            'status': 'running',
            'endpoints': [
                '/api/health',
                '/api/auth',
                '/api/tap',
                '/api/users/telegram/<id>',
                '/api/withdraw/request',
                '/api/withdraw/history',
                '/api/upgrades/info',
                '/api/upgrades/purchase',
                '/api/admin/stats',
                '/api/admin/users',
                '/admin'
            ]
        })
    
    # Admin panel route
    @app.route('/admin')
    def admin_panel():
        admin_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Alpha Wulf Admin Panel</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
                .container { max-width: 1200px; margin: 0 auto; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
                .stat-card { background: #2a2a2a; padding: 20px; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 2em; font-weight: bold; color: #4CAF50; }
                .stat-label { color: #ccc; margin-top: 5px; }
                .section { background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .users-table { width: 100%; border-collapse: collapse; }
                .users-table th, .users-table td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
                .users-table th { background: #333; }
                .btn { background: #4CAF50; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
                .btn:hover { background: #45a049; }
                .btn-danger { background: #f44336; }
                .btn-danger:hover { background: #da190b; }
                .loading { text-align: center; color: #ccc; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Alpha Wulf Admin Panel</h1>
                
                <div class="stats" id="stats">
                    <div class="stat-card">
                        <div class="stat-value" id="totalUsers">-</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="activeUsers">-</div>
                        <div class="stat-label">Active Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalCoins">-</div>
                        <div class="stat-label">Total Coins</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalWithdrawals">-</div>
                        <div class="stat-label">Withdrawals</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Users</h2>
                    <div id="usersContent" class="loading">Loading users...</div>
                </div>
                
                <div class="section">
                    <h2>Withdrawals</h2>
                    <div id="withdrawalsContent" class="loading">Loading withdrawals...</div>
                </div>
            </div>
            
            <script>
                async function loadStats() {
                    try {
                        const response = await fetch('/api/admin/stats');
                        const data = await response.json();
                        
                        document.getElementById('totalUsers').textContent = data.total_users || 0;
                        document.getElementById('activeUsers').textContent = data.active_users || 0;
                        document.getElementById('totalCoins').textContent = data.total_coins || 0;
                        document.getElementById('totalWithdrawals').textContent = data.total_withdrawals || 0;
                    } catch (error) {
                        console.error('Error loading stats:', error);
                    }
                }
                
                async function loadUsers() {
                    try {
                        const response = await fetch('/api/admin/users');
                        const data = await response.json();
                        
                        if (data.users && Array.isArray(data.users)) {
                            let html = '<table class="users-table"><tr><th>ID</th><th>Username</th><th>Coins</th><th>Energy</th><th>Actions</th></tr>';
                            data.users.forEach(user => {
                                html += `<tr>
                                    <td>${user.telegram_id}</td>
                                    <td>${user.username || 'N/A'}</td>
                                    <td>${user.coins}</td>
                                    <td>${user.energy}</td>
                                    <td>
                                        <button class="btn" onclick="adjustCoins(${user.telegram_id}, 1000)">+1000</button>
                                        <button class="btn btn-danger" onclick="resetUser(${user.telegram_id})">Reset</button>
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                            document.getElementById('usersContent').innerHTML = html;
                        } else {
                            document.getElementById('usersContent').innerHTML = 'No users found';
                        }
                    } catch (error) {
                        console.error('Error loading users:', error);
                        document.getElementById('usersContent').innerHTML = 'Error loading users';
                    }
                }
                
                async function loadWithdrawals() {
                    try {
                        const response = await fetch('/api/admin/withdrawals');
                        const data = await response.json();
                        
                        if (data.withdrawals && Array.isArray(data.withdrawals)) {
                            let html = '<table class="users-table"><tr><th>User ID</th><th>Amount</th><th>Status</th><th>Date</th><th>Actions</th></tr>';
                            data.withdrawals.forEach(withdrawal => {
                                html += `<tr>
                                    <td>${withdrawal.user_id}</td>
                                    <td>${withdrawal.amount}</td>
                                    <td>${withdrawal.status}</td>
                                    <td>${new Date(withdrawal.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <button class="btn" onclick="approveWithdrawal(${withdrawal.id})">Approve</button>
                                        <button class="btn btn-danger" onclick="rejectWithdrawal(${withdrawal.id})">Reject</button>
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                            document.getElementById('withdrawalsContent').innerHTML = html;
                        } else {
                            document.getElementById('withdrawalsContent').innerHTML = 'No withdrawals found';
                        }
                    } catch (error) {
                        console.error('Error loading withdrawals:', error);
                        document.getElementById('withdrawalsContent').innerHTML = 'Error loading withdrawals';
                    }
                }
                
                async function adjustCoins(userId, amount) {
                    try {
                        const response = await fetch('/api/admin/user/coins', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: userId, amount: amount })
                        });
                        
                        if (response.ok) {
                            loadUsers();
                            loadStats();
                        }
                    } catch (error) {
                        console.error('Error adjusting coins:', error);
                    }
                }
                
                async function resetUser(userId) {
                    if (confirm('Are you sure you want to reset this user?')) {
                        try {
                            const response = await fetch('/api/admin/user/reset', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ user_id: userId })
                            });
                            
                            if (response.ok) {
                                loadUsers();
                                loadStats();
                            }
                        } catch (error) {
                            console.error('Error resetting user:', error);
                        }
                    }
                }
                
                // Load data on page load
                loadStats();
                loadUsers();
                loadWithdrawals();
                
                // Refresh data every 30 seconds
                setInterval(() => {
                    loadStats();
                    loadUsers();
                    loadWithdrawals();
                }, 30000);
            </script>
        </body>
        </html>
        """
        return render_template_string(admin_html)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # Global CORS handler for all OPTIONS requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
            response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
            return response
    
    logger.info("Flask application created and configured successfully")
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os

# Import routes
from src.routes.user import user_bp
from src.routes.upgrades import upgrades_bp
from src.routes.withdrawal import withdraw_bp
from src.routes.admin import admin_bp
from src.routes.referrals import referral_bp
from src.routes.minigames import minigames_bp

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(upgrades_bp)
app.register_blueprint(withdraw_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(referral_bp)
app.register_blueprint(minigames_bp)

# Serve static files
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)


from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os
from src.routes.user import user_bp
from src.routes.admin import admin_bp
from src.routes.upgrades import upgrades_bp
from src.routes.withdraw import withdraw_bp
from src.routes.referral import referral_bp
from src.routes.minigames import minigames_bp

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'alphawulf2025secretkey')

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(upgrades_bp)
app.register_blueprint(withdraw_bp)
app.register_blueprint(referral_bp)
app.register_blueprint(minigames_bp)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)


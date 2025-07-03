import os
import sys

# DON\'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_cors import CORS

from src.routes.user import user_bp
from src.routes.bot import bot_bp
from src.routes.game import game_bp
from src.routes.minigames import minigames_bp
from src.routes.withdrawal import withdrawal_bp
from src.routes.upgrades import upgrades_bp
from src.routes.referrals import referrals_bp
from src.routes.admin import admin_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = "asdf#FGSgvasgf$5$WGT"

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(bot_bp, url_prefix="/api/bot")
app.register_blueprint(game_bp, url_prefix="/api")
app.register_blueprint(minigames_bp, url_prefix="/api")
app.register_blueprint(withdrawal_bp, url_prefix="/api")
app.register_blueprint(upgrades_bp, url_prefix="/api")
app.register_blueprint(referrals_bp, url_prefix="/api")
app.register_blueprint(admin_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

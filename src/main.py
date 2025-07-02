import os
import sys

# DON\"T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_cors import CORS

# No longer importing db from src.models.user or SQLAlchemy here
# Database interactions will be handled directly within models using the Supabase client

from src.routes.user import user_bp
from src.routes.bot import bot_bp
from src.routes.game import game_bp
from src.routes.minigames import minigames_bp
from src.routes.withdrawal import withdrawal_bp
from src.routes.upgrades import upgrades_bp
from src.routes.referrals import referrals_bp
from src.routes.admin import admin_bp

app = Flask(__name__)
app.config[\"SECRET_KEY\"] = \"asdf#FGSgvasgf$5$WGT\"

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix=\"/api\")
app.register_blueprint(bot_bp, url_prefix=\"/api/bot\")
app.register_blueprint(game_bp, url_prefix=\"/api\")
app.register_blueprint(minigames_bp, url_prefix=\"/api\")
app.register_blueprint(withdrawal_bp, url_prefix=\"/api\")
app.register_blueprint(upgrades_bp, url_prefix=\"/api\")
app.register_blueprint(referrals_bp, url_prefix=\"/api\")
app.register_blueprint(admin_bp)

# Remove SQLAlchemy database initialization
# app.config[\"SQLALCHEMY_DATABASE_URI\"] = f\"sqlite:///{os.path.join(os.path.dirname(__file__), \"database\", \"app.db\")}\"
# app.config[\"SQLALCHEMY_TRACK_MODIFICATIONS\"] = False
# db.init_app(app)
# with app.app_context():
#     db.create_all()



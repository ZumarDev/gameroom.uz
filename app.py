import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
import pytz
from datetime import datetime

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Set timezone to Uzbekistan/Tashkent
os.environ['TZ'] = 'Asia/Tashkent'

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)

# Load secret key from env with fallback for development
secret_key = os.environ.get("SESSION_SECRET")
if not secret_key:
    # For development/migration purposes, provide a fallback
    import secrets
    secret_key = secrets.token_hex(32)
    logging.warning("SESSION_SECRET not found, using generated key for development")
app.secret_key = secret_key
app.config['WTF_CSRF_SECRET_KEY'] = secret_key
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///gaming_center.db")
if database_url.startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize CSRF protection
csrf = CSRFProtect(app)

@login_manager.user_loader
def load_user(user_id):
    from models import AdminUser
    return AdminUser.query.get(int(user_id))

with app.app_context():
    import models  # noqa: F401
    db.create_all()

import views  # noqa: F401

# Import translation helper
from translations import get_translation, get_current_language

# Timezone utility function
def get_tashkent_time():
    """Get current time in Tashkent timezone"""
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    return datetime.now(tashkent_tz)

@app.template_filter('translate')
def translate_filter(key, lang=None):
    from flask_login import current_user
    if not lang:
        lang = get_current_language(current_user if hasattr(current_user, 'preferred_language') else None)
    return get_translation(key, lang)

@app.context_processor
def inject_translation_context():
    from flask_login import current_user
    from flask_wtf.csrf import generate_csrf
    current_lang = get_current_language(current_user if hasattr(current_user, 'preferred_language') else None)
    return {
        'current_lang': current_lang,
        't': lambda key: get_translation(key, current_lang),
        'csrf_token': generate_csrf
    }

from views import *  # noqa: F401, F403

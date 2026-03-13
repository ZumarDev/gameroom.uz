import os
import logging
from flask import Flask, flash, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import selectinload
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import CSRFError
import pytz
from datetime import datetime

# Load environment variables from .env
load_dotenv()

# Configure logging
log_level_name = os.environ.get("LOG_LEVEL")
if not log_level_name:
    is_debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes", "on"}
    log_level_name = "DEBUG" if is_debug else "INFO"
log_level = getattr(logging, log_level_name.upper(), logging.INFO)
logging.basicConfig(level=log_level)

# Set timezone to Uzbekistan/Tashkent
os.environ['TZ'] = 'Asia/Tashkent'

# Create timezone object for consistent use
TASHKENT_TZ = pytz.timezone('Asia/Tashkent')

def get_tashkent_time():
    """Get current time in Tashkent timezone"""
    return datetime.now(TASHKENT_TZ)

def is_superadmin_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    usernames_raw = os.environ.get("SUPERADMIN_USERS", "").strip()
    if usernames_raw:
        usernames = {u.strip() for u in usernames_raw.split(",") if u.strip()}
        return getattr(user, "username", None) in usernames

    return getattr(user, "id", None) == 1

def utc_to_tashkent(utc_time):
    """Convert UTC time to Tashkent time"""
    if utc_time.tzinfo is None:
        utc_time = pytz.utc.localize(utc_time)
    return utc_time.astimezone(TASHKENT_TZ)

db = SQLAlchemy()

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
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

import models  # noqa: F401

# Initialize extensions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize CSRF protection
csrf = CSRFProtect(app)

with app.app_context():
    db.create_all()

    # Lightweight schema migrations (no Alembic in this project).
    insp = inspect(db.engine)
    if insp.has_table("admin_user"):
        existing_cols = {c["name"] for c in insp.get_columns("admin_user")}

        def _add_col(name, ddl_sqlite, ddl_postgres=None):
            if name in existing_cols:
                return
            dialect = db.engine.dialect.name
            if dialect == "postgresql" and ddl_postgres:
                db.session.execute(text(ddl_postgres))
            else:
                db.session.execute(text(ddl_sqlite))

        # Subscription / validity tracking
        _add_col(
            "subscription_expires_at",
            "ALTER TABLE admin_user ADD COLUMN subscription_expires_at DATETIME",
            "ALTER TABLE admin_user ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP",
        )
        _add_col(
            "last_expiry_warning_date",
            "ALTER TABLE admin_user ADD COLUMN last_expiry_warning_date DATE",
            "ALTER TABLE admin_user ADD COLUMN IF NOT EXISTS last_expiry_warning_date DATE",
        )

        db.session.commit()

import views  # noqa: F401

@login_manager.user_loader
def load_user(user_id):
    return models.AdminUser.query.get(int(user_id))

# Import translation helper
from translations import get_translation, get_current_language

@app.template_filter('translate')
def translate_filter(key, lang=None):
    if not lang:
        lang = get_current_language()
    return get_translation(key, lang)

@app.context_processor
def inject_translation_context():
    from flask_login import current_user
    from flask_wtf.csrf import generate_csrf
    current_lang = get_current_language()
    return {
        'current_lang': current_lang,
        't': lambda key: get_translation(key, current_lang),
        'csrf_token': generate_csrf,
        'utc_to_tashkent': utc_to_tashkent,
        'get_tashkent_time': get_tashkent_time,
        'is_superadmin': is_superadmin_user(current_user),
    }

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    lang = get_current_language()
    flash(get_translation('msg_csrf_expired', lang), 'warning')
    return redirect(request.referrer or url_for('login'))

@app.template_filter('tashkent_time')
def tashkent_time_filter(utc_time, format='%H:%M'):
    """Convert UTC time to Tashkent time and format it"""
    if utc_time:
        tashkent_time = utc_to_tashkent(utc_time)
        return tashkent_time.strftime(format)
    return 'N/A'

@app.template_filter('tashkent_date') 
def tashkent_date_filter(utc_time, format='%d.%m.%Y'):
    """Convert UTC time to Tashkent date and format it"""
    if utc_time:
        tashkent_time = utc_to_tashkent(utc_time)
        return tashkent_time.strftime(format)
    return 'N/A'

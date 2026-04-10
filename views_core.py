from flask import flash, g, redirect, request, session, url_for
from flask_login import current_user, logout_user

from app import app, db, get_tashkent_time, is_superadmin_user
from route_helpers import subscription_days_left
from translations import DEFAULT_LANGUAGE, get_all_translations, get_languages, get_translation, t


@app.before_request
def before_request():
    g.lang = session.get('language', DEFAULT_LANGUAGE)
    g.t = lambda key: get_translation(key, g.lang)
    g.languages = get_languages()
    g.current_language = g.lang

    if current_user.is_authenticated and not getattr(current_user, "is_admin_active", True):
        logout_user()
        flash(t('msg_account_inactive'), 'danger')
        return redirect(url_for('login'))

    if current_user.is_authenticated and not is_superadmin_user(current_user):
        endpoint = request.endpoint or ""
        allowed_when_expired = {
            'profile',
            'remove_logo',
            'change_password',
            'logout',
            'set_language',
            'static',
        }

        days_left = subscription_days_left(current_user)
        if days_left is not None:
            today_local = get_tashkent_time().date()
            if 0 < days_left <= 10 and getattr(current_user, "last_expiry_warning_date", None) != today_local:
                flash(t('msg_subscription_expiring').format(days=days_left), 'warning')
                current_user.last_expiry_warning_date = today_local
                db.session.commit()

            if days_left <= 0 and endpoint not in allowed_when_expired and not endpoint.startswith('static'):
                flash(t('msg_subscription_expired'), 'danger')
                return redirect(url_for('profile'))


@app.context_processor
def inject_translations():
    lang = session.get('language', DEFAULT_LANGUAGE)
    return {
        't': lambda key: get_translation(key, lang),
        'translations': get_all_translations(lang),
        'current_language': lang,
        'languages': get_languages(),
    }


@app.route('/set-language/<lang>')
def set_language(lang):
    valid_langs = [l['code'] for l in get_languages()]
    if lang in valid_langs:
        session['language'] = lang
        flash(get_translation('msg_updated', lang), 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

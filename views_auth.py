import os
import secrets
import string
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from werkzeug.security import check_password_hash

from app import app, db, is_superadmin_user
from forms import ChangePasswordForm, LoginForm, ProfileForm, RegisterForm, ResetPasswordForm
from models import AdminUser, Product, ProductCategory
from route_helpers import build_plan_usage, get_plan_catalog, get_plan_config, set_user_password, subscription_days_left
from translations import t


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if AdminUser.query.count() == 0:
        flash(t('msg_create_first_admin'), 'info')
        return redirect(url_for('register'))

    form = LoginForm()
    if form.validate_on_submit():
        username_input = (form.username.data or "").strip()
        password_data = form.password.data or ""
        user = AdminUser.query.filter(func.lower(AdminUser.username) == username_input.lower()).first()
        if user and user.password_hash and password_data and check_password_hash(str(user.password_hash), password_data):
            if not getattr(user, "is_admin_active", True):
                flash(t('msg_account_inactive'), 'danger')
                return render_template('login.html', form=form)
            login_user(user)
            if user.is_temp_password:
                flash(t('msg_temp_password'), 'warning')
                return redirect(url_for('change_password'))
            flash(t('msg_login_success'), 'success')
            return redirect(url_for('dashboard'))
        flash(t('msg_invalid_credentials'), 'danger')

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    allow_public = os.environ.get("ALLOW_PUBLIC_REGISTRATION", "").lower() in {"1", "true", "yes", "on"}
    has_any_admin = AdminUser.query.count() > 0
    if has_any_admin and not allow_public:
        if current_user.is_authenticated and is_superadmin_user(current_user):
            return redirect(url_for('admin_create_user'))
        abort(404)

    form = RegisterForm()
    if form.validate_on_submit():
        secret_key = os.environ.get('SECRET_ADMIN_KEY', 'gameroom2026')
        if form.secret_key.data != secret_key:
            flash(t('msg_secret_key_invalid'), 'danger')
            return render_template('register.html', form=form)

        username = (form.username.data or "").strip()
        existing_user = AdminUser.query.filter(func.lower(AdminUser.username) == username.lower()).first()
        if existing_user:
            flash(t('msg_username_taken'), 'danger')
            return render_template('register.html', form=form)

        user = AdminUser()
        user.username = username
        user.gaming_center_name = (form.gaming_center_name.data or "").strip()
        set_user_password(user, form.password.data)

        db.session.add(user)
        db.session.commit()

        flash(t('msg_admin_created'), 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(t('msg_logout'), 'info')
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.gaming_center_name = form.gaming_center_name.data

        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
                filename = logo_file.filename
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    if current_user.logo_filename:
                        old_logo_path = os.path.join(app.root_path, 'static', 'uploads', current_user.logo_filename)
                        if os.path.exists(old_logo_path):
                            os.remove(old_logo_path)

                    ext = filename.rsplit('.', 1)[1].lower()
                    new_filename = f"logo_{current_user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
                    logo_path = os.path.join(app.root_path, 'static', 'uploads', new_filename)
                    logo_file.save(logo_path)
                    current_user.logo_filename = new_filename
                    flash(t('msg_logo_uploaded'), 'success')
                else:
                    flash(t('msg_only_images'), 'warning')

        db.session.commit()
        flash(t('msg_profile_updated'), 'success')
        return redirect(url_for('profile'))

    form.gaming_center_name.data = current_user.gaming_center_name
    days_left = subscription_days_left(current_user)
    total_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    total_categories = ProductCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    plan_details = get_plan_config(current_user)
    plan_usage = build_plan_usage(plan_details, total_products, total_categories)
    return render_template(
        'profile.html',
        form=form,
        subscription_days_left=days_left,
        plan_details=plan_details,
        plan_catalog=get_plan_catalog(),
        plan_usage=plan_usage,
    )


@app.route('/profile/remove-logo', methods=['POST'])
@login_required
def remove_logo():
    if current_user.logo_filename:
        logo_path = os.path.join(app.root_path, 'static', 'uploads', current_user.logo_filename)
        if os.path.exists(logo_path):
            os.remove(logo_path)
        current_user.logo_filename = None
        db.session.commit()
        flash(t('msg_logo_removed'), 'success')
    else:
        flash(t('msg_logo_not_found'), 'info')
    return redirect(url_for('profile'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.is_temp_password:
            if not current_user.password_hash or not form.current_password.data or not check_password_hash(str(current_user.password_hash), form.current_password.data):
                flash(t('msg_current_password_wrong'), 'danger')
                return render_template('change_password.html', form=form)

        if form.new_password.data:
            set_user_password(current_user, form.new_password.data)
        db.session.commit()
        flash(t('msg_password_changed'), 'success')
        return redirect(url_for('dashboard'))

    return render_template('change_password.html', form=form)


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        secret_key = os.environ.get('SECRET_ADMIN_KEY', 'gameroom2026')
        if form.secret_key.data != secret_key:
            flash(t('msg_secret_key_invalid'), 'danger')
            return render_template('reset_password.html', form=form)

        user = AdminUser.query.filter_by(username=form.username.data).first()
        if not user:
            flash(t('msg_user_not_found'), 'danger')
            return render_template('reset_password.html', form=form)

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        set_user_password(user, temp_password, is_temp_password=True)
        db.session.commit()

        flash(f"{t('msg_temp_password_created')}: {temp_password}", 'success')
        flash(t('msg_change_password_required'), 'info')
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)

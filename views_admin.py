from datetime import datetime, timedelta

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import app, db, is_superadmin_user
from forms import AdminCreateUserForm
from models import AdminUser
from route_helpers import set_user_password, subscription_days_left
from translations import t


def _parse_subscription_days():
    days_raw = request.form.get("days", "").strip()
    try:
        days = int(days_raw)
    except ValueError:
        days = 0
    return days


@app.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if not is_superadmin_user(current_user):
        abort(403)

    form = AdminCreateUserForm()
    if form.validate_on_submit():
        username = (form.username.data or "").strip()
        existing_user = AdminUser.query.filter(func.lower(AdminUser.username) == username.lower()).first()
        if existing_user:
            flash(t('msg_username_taken'), 'danger')
            return render_template('admin_create_user.html', form=form)

        user = AdminUser()
        user.username = username
        user.gaming_center_name = (form.gaming_center_name.data or "").strip()
        set_user_password(user, form.password.data)
        if getattr(form, "subscription_days", None) and form.subscription_days.data:
            user.subscription_expires_at = datetime.utcnow() + timedelta(days=int(form.subscription_days.data))
        db.session.add(user)
        db.session.commit()

        flash(t('msg_admin_created'), 'success')
        return redirect(url_for('dashboard'))

    return render_template('admin_create_user.html', form=form)


@app.route('/admin/users')
@login_required
def admin_users():
    if not is_superadmin_user(current_user):
        abort(403)

    users = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    days_left_by_id = {u.id: subscription_days_left(u) for u in users}
    return render_template('admin_users.html', users=users, days_left_by_id=days_left_by_id)


@app.route('/admin/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
def admin_toggle_user_active(user_id):
    if not is_superadmin_user(current_user):
        abort(403)

    if user_id == current_user.id:
        flash(t('msg_cannot_deactivate_self'), 'warning')
        return redirect(url_for('admin_users'))

    user = AdminUser.query.get_or_404(user_id)
    user.is_admin_active = not bool(user.is_admin_active)
    db.session.commit()

    flash(t('msg_updated'), 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/extend-subscription', methods=['POST'])
@login_required
def admin_extend_subscription(user_id):
    if not is_superadmin_user(current_user):
        abort(403)

    days = _parse_subscription_days()
    if days <= 0 or days > 3650:
        flash(t('msg_invalid_duration_days'), 'warning')
        return redirect(url_for('admin_users'))

    user = AdminUser.query.get_or_404(user_id)
    now_utc = datetime.utcnow()
    base = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now_utc else now_utc
    user.subscription_expires_at = base + timedelta(days=days)
    user.is_admin_active = True
    user.last_expiry_warning_date = None
    db.session.commit()

    flash(t('msg_updated'), 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/set-subscription', methods=['POST'])
@login_required
def admin_set_subscription(user_id):
    if not is_superadmin_user(current_user):
        abort(403)

    days = _parse_subscription_days()
    if days <= 0 or days > 3650:
        flash(t('msg_invalid_duration_days'), 'warning')
        return redirect(url_for('admin_users'))

    user = AdminUser.query.get_or_404(user_id)
    user.subscription_expires_at = datetime.utcnow() + timedelta(days=days)
    user.is_admin_active = True
    user.last_expiry_warning_date = None
    db.session.commit()

    flash(t('msg_updated'), 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/set-unlimited', methods=['POST'])
@login_required
def admin_set_unlimited(user_id):
    if not is_superadmin_user(current_user):
        abort(403)

    user = AdminUser.query.get_or_404(user_id)
    user.subscription_expires_at = None
    user.last_expiry_warning_date = None
    user.is_admin_active = True
    db.session.commit()

    flash(t('msg_updated'), 'success')
    return redirect(url_for('admin_users'))

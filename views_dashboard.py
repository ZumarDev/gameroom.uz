from flask import render_template
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app import app, db, get_tashkent_time
from models import Product, Room, RoomCategory, Session
from route_helpers import utc_range_for_tashkent_date


@app.route('/dashboard')
@login_required
def dashboard():
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()

    active_sessions = (
        Session.query.join(Room)
        .filter(
            Room.admin_user_id == current_user.id,
            Room.is_active == True,
            Session.is_active == True,
        )
        .options(selectinload(Session.room))
        .all()
    )

    today_local = get_tashkent_time().date()
    day_start_utc, day_end_utc = utc_range_for_tashkent_date(today_local)
    today_count, today_revenue = (
        db.session.query(
            func.count(Session.id),
            func.coalesce(func.sum(Session.total_price), 0.0),
        )
        .join(Room, Session.room_id == Room.id)
        .filter(
            Room.admin_user_id == current_user.id,
            Session.is_active == False,
            Session.created_at >= day_start_utc,
            Session.created_at < day_end_utc,
        )
        .one()
    )

    total_rooms = len(user_rooms)
    total_products = Product.query.filter(
        Product.admin_user_id == current_user.id,
        Product.is_active == True,
        Product.stock_quantity > 0
    ).count()

    available_products = Product.query.filter(
        Product.admin_user_id == current_user.id,
        Product.is_active == True,
        Product.stock_quantity > 0
    ).all()
    room_categories = RoomCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).all()

    active_room_ids = {s.room_id for s in active_sessions}
    available_rooms = [r for r in user_rooms if r.id not in active_room_ids]
    busy_rooms = [r for r in user_rooms if r.id in active_room_ids]

    return render_template(
        'dashboard.html',
        active_sessions=active_sessions,
        today_revenue=today_revenue,
        total_rooms=total_rooms,
        total_products=total_products,
        session_count=today_count,
        user_rooms=user_rooms,
        available_rooms=available_rooms,
        busy_rooms=busy_rooms,
        room_categories=room_categories,
        available_products=available_products,
    )

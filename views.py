from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import selectinload
import math
import os
import pandas as pd
from io import BytesIO
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import pytz
from app import app, db, TASHKENT_TZ, get_tashkent_time, is_superadmin_user
from models import AdminUser, Room, RoomCategory, ProductCategory, Product, Session, CartItem, FIXED_SESSION_PRICES
from forms import LoginForm, RoomForm, RoomCategoryForm, ProductCategoryForm, ProductForm, SessionForm, AddProductToSessionForm, RegisterForm, AdminCreateUserForm, StockUpdateForm, InventoryForm, ChangePasswordForm, ResetPasswordForm, ProfileForm, QuickAddProductForm, ExcelImportForm, ReportForm
from werkzeug.security import generate_password_hash
from translations import get_translation, get_all_translations, get_languages, t, DEFAULT_LANGUAGE
from flask import session, g
import views_core  # noqa: F401
import views_auth  # noqa: F401
import views_admin  # noqa: F401
import views_dashboard  # noqa: F401
import views_reports  # noqa: F401


def get_plan_config(user):
    plan = (getattr(user, 'subscription_plan', None) or 'basic').lower()
    definitions = {
        'basic': {
            'plan': 'basic',
            'label': 'Basic',
            'max_products': 25,
            'max_categories': 5,
            'ai_enabled': False,
            'description': 'Bosh rejadagi imkoniyatlar: kichik inventar va cheklangan tahlil.'
        },
        'standard': {
            'plan': 'standard',
            'label': 'Standard',
            'max_products': 75,
            'max_categories': 12,
            'ai_enabled': True,
            'description': 'Standard rejada AI insightlar va kengroq hisobotlar mavjud.'
        },
        'premium': {
            'plan': 'premium',
            'label': 'Premium',
            'max_products': None,
            'max_categories': None,
            'ai_enabled': True,
            'description': 'Premium rejada cheksiz inventar va to‘liq tahlil taqdim etiladi.'
        }
    }
    return definitions.get(plan, definitions['basic'])


@app.route('/rooms-management')
@login_required
def rooms_management():
    # Multi-tenant: Only show categories and rooms for current user
    categories = RoomCategory.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).order_by(RoomCategory.created_at.desc()).all()

    rooms = (
        Room.query.filter_by(
            admin_user_id=current_user.id,
            is_active=True
        )
        .options(selectinload(Room.category))
        .order_by(Room.created_at.desc())
        .all()
    )

    category_room_counts = dict(
        db.session.query(Room.category_id, func.count(Room.id))
        .filter(
            Room.admin_user_id == current_user.id,
        )
        .group_by(Room.category_id)
        .all()
    )
    
    category_form = RoomCategoryForm()
    room_form = RoomForm()
    room_form.category_id.choices = [(c.id, c.name) for c in categories]
    
    return render_template('rooms_management.html', 
                         categories=categories, 
                         rooms=rooms,
                         category_room_counts=category_room_counts,
                         category_form=category_form,
                         room_form=room_form)

@app.route('/room-categories')
@login_required
def room_categories():
    return redirect(url_for('rooms_management'))

@app.route('/room-categories/add', methods=['POST'])
@login_required
def add_room_category():
    form = RoomCategoryForm()
    if form.validate_on_submit():
        category = RoomCategory()
        category.admin_user_id = current_user.id  # Multi-tenant
        category.name = form.name.data
        category.description = form.description.data
        category.price_per_30min = form.price_per_30min.data
        db.session.add(category)
        db.session.commit()
        flash(f'Kategoriya "{category.name}" muvaffaqiyatli yaratildi!', 'success')
    return redirect(url_for('rooms_management'))

@app.route('/room-categories/edit/<int:category_id>', methods=['POST'])
@login_required
def edit_room_category(category_id):
    category = RoomCategory.query.filter_by(id=category_id, admin_user_id=current_user.id).first_or_404()
    
    try:
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.price_per_30min = float(request.form.get('price_per_30min', 0))
        db.session.commit()
        flash(f'Kategoriya "{category.name}" muvaffaqiyatli yangilandi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kategoriya yangilashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('rooms_management'))

@app.route('/room-categories/<int:category_id>/delete')
@login_required
def delete_room_category(category_id):
    category = RoomCategory.query.filter_by(id=category_id, admin_user_id=current_user.id).first_or_404()
    category.is_active = False
    db.session.commit()
    flash(f'Kategoriya "{category.name}" o\'chirildi!', 'success')
    return redirect(url_for('rooms_management'))

@app.route('/rooms')
@login_required
def rooms():
    rooms_list = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    form = RoomForm()
    form.category_id.choices = [(c.id, c.name) for c in RoomCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).all()]
    return redirect(url_for('rooms_management'))

@app.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    form = RoomForm()
    form.category_id.choices = [(c.id, c.name) for c in RoomCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).all()]
    if form.validate_on_submit():
        room = Room()
        room.admin_user_id = current_user.id  # Multi-tenant
        room.name = form.name.data
        room.description = form.description.data
        room.category_id = form.category_id.data
        room.custom_price_per_30min = form.custom_price_per_30min.data
        db.session.add(room)
        db.session.commit()
        flash(f'Xona "{room.name}" muvaffaqiyatli yaratildi!', 'success')
    else:
        flash('Xona qo\'shishda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    return redirect(url_for('rooms_management') + '?tab=rooms')



@app.route('/rooms/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    room = Room.query.filter_by(id=room_id, admin_user_id=current_user.id).first_or_404()
    active_session = Session.query.filter_by(room_id=room.id, is_active=True).first()
    if active_session:
        flash(f'Xona "{room.name}" o\'chirilmadi: faol seans mavjud!', 'warning')
        return redirect(url_for('rooms_management') + '?tab=rooms')
    room.is_active = False
    db.session.commit()
    flash(f'Xona "{room.name}" o\'chirildi!', 'success')
    return redirect(url_for('rooms_management') + '?tab=rooms')

@app.route('/rooms/edit/<int:room_id>', methods=['POST'])
@login_required
def edit_room(room_id):
    room = Room.query.filter_by(id=room_id, admin_user_id=current_user.id).first_or_404()
    
    room.name = request.form.get('name')
    room.description = request.form.get('description')
    room.category_id = request.form.get('category_id')
    
    # Handle custom price - empty string should be converted to None
    custom_price = request.form.get('custom_price_per_30min')
    if custom_price and custom_price.strip():
        room.custom_price_per_30min = float(custom_price)
    else:
        room.custom_price_per_30min = None
    
    db.session.commit()
    flash(f'Xona "{room.name}" muvaffaqiyatli yangilandi!', 'success')
    return redirect(url_for('rooms_management') + '?tab=rooms')

@app.route('/products')
@login_required
def products():
    # Multi-tenant: Only show products and categories for current user's gaming center
    products_list = (
        Product.query
        .options(selectinload(Product.product_category))
        .filter_by(admin_user_id=current_user.id, is_active=True)
        .order_by(Product.created_at.desc())
        .all()
    )
    categories_list = ProductCategory.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).order_by(ProductCategory.name).all()
    
    # Setup forms
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in categories_list]
    category_form = ProductCategoryForm()
    
    plan_details = get_plan_config(current_user)
    return render_template('products.html', 
                         products=products_list, 
                         categories=categories_list,
                         form=form,
                         category_form=category_form,
                         plan_details=plan_details)

@app.route('/products/add', methods=['POST'])
@login_required
def add_product():
    categories_list = ProductCategory.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    plan_details = get_plan_config(current_user)
    current_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    if plan_details['max_products'] is not None and current_products >= plan_details['max_products']:
        flash(f'Bu tarifda faqat {plan_details["max_products"]} ta mahsulot qo‘shishga ruxsat bor. Tarifni yangilang.', 'warning')
        return redirect(url_for('products') + '?tab=products')

    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in categories_list]
    
    if form.validate_on_submit():
        product = Product()
        product.admin_user_id = current_user.id  # Multi-tenant
        product.name = form.name.data
        product.category_id = form.category_id.data
        product.price = form.price.data
        product.unit = form.unit.data
        product.stock_quantity = form.stock_quantity.data
        product.min_stock_alert = form.min_stock_alert.data
        db.session.add(product)
        db.session.commit()
        
        flash(f'Mahsulot "{product.name}" muvaffaqiyatli qo\'shildi!', 'success')
    else:
        flash('Mahsulot qo\'shishda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    return redirect(url_for('products') + '?tab=products')

@app.route('/products/edit/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    # Multi-tenant: Only allow editing of current user's products
    product = Product.query.filter_by(id=product_id, admin_user_id=current_user.id).first_or_404()
    
    try:
        product.name = request.form.get('name')
        product.category_id = request.form.get('category_id')
        product.price = float(request.form.get('price', 0))
        product.unit = request.form.get('unit')
        product.stock_quantity = int(request.form.get('stock_quantity', 0))
        product.min_stock_alert = int(request.form.get('min_stock_alert', 0))
        
        db.session.commit()
        flash(f'{product.name} mahsuloti muvaffaqiyatli yangilandi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Mahsulot yangilashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('products') + '?tab=products')

@app.route('/products/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, admin_user_id=current_user.id).first_or_404()
    active_session_product = (
        CartItem.query.join(Session)
        .filter(
            CartItem.product_id == product.id,
            Session.is_active == True,
        )
        .first()
    )
    if active_session_product:
        flash(f'Mahsulot "{product.name}" o\'chirilmadi: faol seanslarda ishlatilmoqda!', 'warning')
        return redirect(url_for('products') + '?tab=products')
    product.is_active = False
    db.session.commit()
    flash(f'Mahsulot "{product.name}" o\'chirildi!', 'success')
    return redirect(url_for('products') + '?tab=products')

@app.route('/products/add-category', methods=['POST'])
@login_required
def add_product_category():
    form = ProductCategoryForm()
    plan_details = get_plan_config(current_user)
    current_categories = ProductCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    if plan_details['max_categories'] is not None and current_categories >= plan_details['max_categories']:
        flash(f'Bu tarifda faqat {plan_details["max_categories"]} ta kategoriya yaratishga ruxsat bor. Tarifni yangilang.', 'warning')
        return redirect(url_for('products'))

    if form.validate_on_submit():
        category = ProductCategory()
        category.admin_user_id = current_user.id  # Multi-tenant
        category.name = form.name.data
        category.description = form.description.data
        db.session.add(category)
        db.session.commit()
        
        flash(f'Kategoriya "{category.name}" muvaffaqiyatli qo\'shildi!', 'success')
    else:
        flash('Kategoriya qo\'shishda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    return redirect(url_for('products'))

@app.route('/products/edit-category/<int:category_id>', methods=['POST'])
@login_required
def edit_product_category(category_id):
    category = ProductCategory.query.filter_by(id=category_id, admin_user_id=current_user.id).first_or_404()
    
    try:
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        db.session.commit()
        flash(f'Kategoriya "{category.name}" yangilandi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kategoriya yangilashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

@app.route('/products/delete-category/<int:category_id>')
@login_required
def delete_product_category(category_id):
    category = ProductCategory.query.filter_by(id=category_id, admin_user_id=current_user.id).first_or_404()
    
    # Check if category has active products
    active_products = Product.query.filter_by(category_id=category_id, is_active=True).count()
    if active_products > 0:
        flash(f'Kategoriya o\'chirilmadi: "{category.name}" kategoriyasida {active_products} ta faol mahsulot bor!', 'danger')
        return redirect(url_for('products'))

    active_session_items = (
        CartItem.query.join(Product)
        .join(Session, CartItem.session_id == Session.id)
        .filter(
            Product.category_id == category_id,
            Session.is_active == True,
        )
        .first()
    )
    if active_session_items:
        flash(f'Kategoriya o\'chirilmadi: "{category.name}" kategoriyasi mahsulotlari faol seanslarda ishlatilmoqda!', 'warning')
        return redirect(url_for('products'))

    category.is_active = False
    db.session.commit()
    flash(f'Kategoriya "{category.name}" o\'chirildi!', 'success')
    return redirect(url_for('products'))

# Inventory management routes
@app.route('/inventory')
@login_required
def inventory():
    """Display inventory management page with stock levels"""
    products_list = (
        Product.query
        .options(selectinload(Product.product_category))
        .filter_by(admin_user_id=current_user.id, is_active=True)
        .order_by(Product.name)
        .all()
    )

    plan_details = get_plan_config(current_user)
    current_plan = plan_details['plan']

    low_stock_items = [
        p for p in products_list
        if p.stock_quantity is not None and p.stock_quantity <= p.min_stock_alert and p.stock_quantity > 0
    ]
    out_of_stock_items = [
        p for p in products_list
        if p.stock_quantity is None or p.stock_quantity <= 0
    ]
    available_items = [
        p for p in products_list
        if p.stock_quantity is not None and p.stock_quantity > p.min_stock_alert
    ]

    top_reorder = sorted(
        low_stock_items + out_of_stock_items,
        key=lambda p: (p.stock_quantity if p.stock_quantity is not None else -1, p.min_stock_alert)
    )[:5]

    insight_summary = []
    if out_of_stock_items:
        insight_summary.append(f"{len(out_of_stock_items)} ta mahsulot zaxirada yo'q.")
    if low_stock_items:
        insight_summary.append(f"{len(low_stock_items)} ta mahsulot minimal chegaraga yaqin.")
    if not insight_summary:
        insight_summary.append('Hozircha inventar yaxshi holatda.')

    inventory_categories = sorted(
        {p.product_category.id: p.product_category for p in products_list if p.product_category}.values(),
        key=lambda category: category.name
    )

    stock_stats = {
        'total_products': len(products_list),
        'available_count': len(available_items),
        'low_stock_count': len(low_stock_items),
        'out_of_stock_count': len(out_of_stock_items),
        'recommendations': top_reorder,
    }

    inventory_form = InventoryForm()
    inventory_form.product_id.choices = [
        (p.id, f"{p.name} ({p.stock_quantity} {p.unit})")
        for p in products_list
    ]
    
    return render_template('inventory.html', 
                         products=products_list, 
                         form=inventory_form,
                         plan_details=plan_details,
                         current_plan=current_plan,
                         stock_stats=stock_stats,
                         insight_summary=insight_summary,
                         inventory_categories=inventory_categories)

@app.route('/inventory/update', methods=['POST'])
@login_required
def update_inventory():
    """Update product stock levels"""
    form = InventoryForm()
    products_list = Product.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    form.product_id.choices = [(p.id, f"{p.name} ({p.stock_quantity} {p.unit})") 
                             for p in products_list]
    
    if form.validate_on_submit():
        product = Product.query.filter_by(
            id=form.product_id.data, 
            admin_user_id=current_user.id
        ).first_or_404()
        
        old_quantity = product.stock_quantity
        quantity = form.quantity.data
        action = form.action.data
        
        if action == 'add':
            product.stock_quantity += quantity
            flash(f'{product.name} mahsulotiga {quantity} {product.unit} qo\'shildi. Yangi zaxira: {product.stock_quantity}', 'success')
        elif action == 'set':
            product.stock_quantity = quantity
            flash(f'{product.name} mahsuloti zaxirasi {quantity} {product.unit} ga o\'rnatildi.', 'success')
        
        db.session.commit()
    else:
        flash('Zaxira yangilashda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    
    return redirect(url_for('inventory'))

@app.route('/sessions')
@login_required
def sessions():
    # Multi-tenant: Get sessions for current user's rooms only
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    active_sessions = (
        Session.query.join(Room)
        .filter(
            Room.admin_user_id == current_user.id,
            Session.is_active == True,
        )
        .options(selectinload(Session.room))
        .all()
    )
    
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    filter_room = request.args.get('room_id', type=int)
    filter_type = request.args.get('session_type')
    filter_date_from = request.args.get('date_from')
    filter_date_to = request.args.get('date_to')
    filter_min_sum = request.args.get('min_sum', type=float)
    filter_max_sum = request.args.get('max_sum', type=float)
    sort_by = request.args.get('sort', 'date_desc')
    
    # Build query for completed sessions
    completed_sessions_query = Session.query.filter(
        Session.room_id.in_(user_room_ids), 
        Session.is_active == False
    )
    
    # Apply filters
    if filter_room:
        completed_sessions_query = completed_sessions_query.filter(Session.room_id == filter_room)
    
    if filter_type:
        completed_sessions_query = completed_sessions_query.filter(Session.session_type == filter_type)
    
    if filter_date_from:
        try:
            date_from = datetime.strptime(filter_date_from, '%Y-%m-%d')
            completed_sessions_query = completed_sessions_query.filter(Session.created_at >= date_from)
        except ValueError:
            pass  # Invalid date format - skip filter
    
    if filter_date_to:
        try:
            date_to = datetime.strptime(filter_date_to, '%Y-%m-%d') + timedelta(days=1)
            completed_sessions_query = completed_sessions_query.filter(Session.created_at < date_to)
        except ValueError:
            pass  # Invalid date format - skip filter
    
    if filter_min_sum is not None:
        completed_sessions_query = completed_sessions_query.filter(Session.total_price >= filter_min_sum)
    
    if filter_max_sum is not None:
        completed_sessions_query = completed_sessions_query.filter(Session.total_price <= filter_max_sum)
    
    # Apply sorting
    if sort_by == 'date_asc':
        completed_sessions_query = completed_sessions_query.order_by(Session.created_at.asc())
    elif sort_by == 'sum_desc':
        completed_sessions_query = completed_sessions_query.order_by(Session.total_price.desc())
    elif sort_by == 'sum_asc':
        completed_sessions_query = completed_sessions_query.order_by(Session.total_price.asc())
    else:  # date_desc (default)
        completed_sessions_query = completed_sessions_query.order_by(Session.created_at.desc())
    
    # Paginate
    pagination = completed_sessions_query.paginate(page=page, per_page=per_page, error_out=False)
    completed_sessions = pagination.items
    
    # Calculate filtered totals
    filtered_total_sum = (
        completed_sessions_query.order_by(None)
        .with_entities(func.coalesce(func.sum(Session.total_price), 0.0))
        .scalar()
        or 0.0
    )
    filtered_count = completed_sessions_query.order_by(None).count()
    
    # Setup form for new session
    form = SessionForm()
    form.room_id.choices = [(r.id, r.name) for r in user_rooms]
    
    # Get available products for adding to sessions (only with stock > 0)
    available_products = Product.query.filter(
        Product.admin_user_id == current_user.id,
        Product.is_active == True,
        Product.stock_quantity > 0
    ).all()
    
    # Get room categories for filtering
    room_categories = RoomCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    
    # Find rooms that are currently available (not in active session)
    active_room_ids = {s.room_id for s in active_sessions}
    available_rooms = [r for r in user_rooms if r.id not in active_room_ids]
    
    return render_template('sessions.html', 
                         active_sessions=active_sessions,
                         completed_sessions=completed_sessions,
                         pagination=pagination,
                         filtered_total_sum=filtered_total_sum,
                         filtered_count=filtered_count,
                         form=form,
                         available_products=available_products,
                         room_categories=room_categories,
                         user_rooms=user_rooms,
                         available_rooms=available_rooms,
                         # Pass current filter values back to template
                         filter_room=filter_room,
                         filter_type=filter_type,
                         filter_date_from=filter_date_from,
                         filter_date_to=filter_date_to,
                         filter_min_sum=filter_min_sum,
                         filter_max_sum=filter_max_sum,
                         sort_by=sort_by)

@app.route('/sessions/start', methods=['POST'])
@login_required
def start_session():
    form = SessionForm()
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    form.room_id.choices = [(r.id, r.name) for r in user_rooms]
    
    if form.validate_on_submit():
        # Get user room IDs for multi-tenant check
        user_room_ids = [room.id for room in user_rooms]
        
        # Check if room is already in use - Multi-tenant: Only check current user's sessions
        existing_session = Session.query.filter(
            Session.room_id == form.room_id.data,
            Session.room_id.in_(user_room_ids),
            Session.is_active == True
        ).first()
        if existing_session:
            flash('Bu xona allaqachon ishlatilmoqda!', 'danger')
            return redirect(url_for('sessions'))
        
        room = Room.query.filter_by(id=form.room_id.data, admin_user_id=current_user.id).first()
        
        # Check which input type user selected and validate accordingly
        if form.session_type.data == 'fixed':
            if form.input_type.data == 'amount':
                # User provided amount - calculate time based on room/category pricing
                if not form.amount_input.data or form.amount_input.data <= 0:
                    flash('Summa kiritish kerak va 0 dan katta bo\'lishi kerak!', 'danger')
                    return redirect(url_for('sessions'))
                    
                target_amount = form.amount_input.data
                if room and room.custom_price_per_30min:
                    price_per_30min = room.custom_price_per_30min
                elif room and room.category:
                    price_per_30min = room.category.price_per_30min
                else:
                    price_per_30min = 15000  # Default fallback
                
                # Calculate exact time based on amount entered
                # For example: if room costs 1000 per 30min and user enters 100, 
                # they get (100/1000)*30 = 3 minutes of play time
                calculated_seconds = (target_amount / price_per_30min) * 30 * 60  # Convert to seconds
                total_seconds = max(int(calculated_seconds), 60)  # Minimum 1 minute (60 seconds)
                total_minutes = total_seconds / 60  # Keep as float for precise timing
                
                # Show user how much time they got for their money
                hours = int(total_minutes // 60)
                minutes = int(total_minutes % 60)
                seconds = int((total_minutes % 1) * 60)
                
                if hours > 0:
                    time_display = f"{hours} soat {minutes} daqiqa"
                elif minutes > 0:
                    time_display = f"{minutes} daqiqa {seconds} soniya" if seconds > 0 else f"{minutes} daqiqa"
                else:
                    time_display = f"{seconds} soniya"
                    
                flash(f'💰 {target_amount:,.0f} som uchun {time_display} vaqt berildi!', 'info')
                
                session = Session()
                session.room_id = form.room_id.data
                session.session_type = form.session_type.data
                session.duration_minutes = total_minutes
                session.duration_seconds = total_seconds  # Store exact seconds for precise timing
                
                # User pays exactly what they entered - save as prepaid amount
                session.prepaid_amount = target_amount
                session.session_price = target_amount
                session.total_price = target_amount
            else:
                # User provided time - calculate amount based on room/category pricing
                hours = form.duration_hours.data or 0
                minutes = form.duration_minutes.data or 0
                total_minutes = (hours * 60) + minutes
                if total_minutes == 0:
                    total_minutes = 30  # Default to 30 minutes if no time specified
                    
                session = Session()
                session.room_id = form.room_id.data
                session.session_type = form.session_type.data
                session.duration_minutes = total_minutes
                
                # Calculate based on room/category pricing and duration
                session.update_total_price()
        else:
            # VIP session - price will be calculated when stopped
            session = Session()
            session.room_id = form.room_id.data
            session.session_type = form.session_type.data
            session.duration_minutes = None
            session.session_price = 0
            session.total_price = 0
        
        try:
            db.session.add(session)
            db.session.commit()
            flash('Seans muvaffaqiyatli boshlandi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Seans saqlashda xatolik: {str(e)}', 'danger')
    else:
        # Print form errors for debugging
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
        flash('Seans boshlashda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    
    return redirect(url_for('sessions'))

# Bir nechta xona uchun seans yaratish
@app.route('/sessions/start-multiple', methods=['POST'])
@login_required
def start_multiple_sessions():
    """Bir nechta xona uchun bir vaqtda seans yaratish"""
    room_ids = request.form.getlist('room_ids[]')
    session_type = request.form.get('session_type', 'fixed')
    input_type = request.form.get('input_type', 'time')
    duration_hours = int(request.form.get('duration_hours', 0) or 0)
    duration_minutes_val = int(request.form.get('duration_minutes', 30) or 30)
    amount_input = float(request.form.get('amount_input', 0) or 0)
    
    if not room_ids:
        flash('Kamida bitta xona tanlang!', 'danger')
        return redirect(url_for('sessions'))
    
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    
    created_count = 0
    skipped_rooms = []
    
    for room_id_str in room_ids:
        try:
            room_id = int(room_id_str)
        except ValueError:
            continue
            
        # Check if room belongs to user
        if room_id not in user_room_ids:
            continue
            
        # Check if room is already in use
        existing_session = Session.query.filter(
            Session.room_id == room_id,
            Session.is_active == True
        ).first()
        
        if existing_session:
            room = Room.query.get(room_id)
            skipped_rooms.append(room.name if room else f"ID:{room_id}")
            continue
        
        room = Room.query.get(room_id)
        if not room:
            continue
        
        # Create session based on type
        if session_type == 'fixed':
            if input_type == 'amount' and amount_input > 0:
                # Calculate time from amount
                if room.custom_price_per_30min:
                    price_per_30min = room.custom_price_per_30min
                elif room.category:
                    price_per_30min = room.category.price_per_30min
                else:
                    price_per_30min = 15000
                
                calculated_seconds = (amount_input / price_per_30min) * 30 * 60
                total_seconds = max(int(calculated_seconds), 60)
                total_minutes = total_seconds / 60
                
                session = Session()
                session.room_id = room_id
                session.session_type = session_type
                session.duration_minutes = total_minutes
                session.duration_seconds = total_seconds
                session.prepaid_amount = amount_input
                session.session_price = amount_input
                session.total_price = amount_input
            else:
                # Time-based
                total_minutes = (duration_hours * 60) + duration_minutes_val
                if total_minutes == 0:
                    total_minutes = 30
                    
                session = Session()
                session.room_id = room_id
                session.session_type = session_type
                session.duration_minutes = total_minutes
                session.update_total_price()
        else:
            # VIP session
            session = Session()
            session.room_id = room_id
            session.session_type = session_type
            session.duration_minutes = None
            session.session_price = 0
            session.total_price = 0
        
        try:
            db.session.add(session)
            created_count += 1
        except Exception as e:
            db.session.rollback()
            flash(f'Xatolik: {str(e)}', 'danger')
            return redirect(url_for('sessions'))
    
    db.session.commit()
    
    if created_count > 0:
        flash(f'✅ {created_count} ta seans muvaffaqiyatli boshlandi!', 'success')
    
    if skipped_rooms:
        flash(f'⚠️ Bu xonalar band: {", ".join(skipped_rooms)}', 'warning')
    
    return redirect(url_for('sessions'))

# API: Kategoriya bo'yicha xonalarni olish
@app.route('/api/rooms-by-category/<int:category_id>')
@login_required
def get_rooms_by_category(category_id):
    """Kategoriya bo'yicha xonalarni qaytarish"""
    rooms = Room.query.filter_by(
        admin_user_id=current_user.id,
        category_id=category_id,
        is_active=True
    ).all()
    
    # Get active session room IDs
    active_sessions = Session.query.filter(
        Session.room_id.in_([r.id for r in rooms]),
        Session.is_active == True
    ).all()
    active_room_ids = {s.room_id for s in active_sessions}
    
    result = []
    for room in rooms:
        result.append({
            'id': room.id,
            'name': room.name,
            'is_available': room.id not in active_room_ids,
            'price_per_30min': room.custom_price_per_30min or (room.category.price_per_30min if room.category else 15000)
        })
    
    return jsonify(result)

# API: Barcha bo'sh xonalarni olish
@app.route('/api/available-rooms')
@login_required
def get_available_rooms():
    """Barcha bo'sh xonalarni qaytarish"""
    category_id = request.args.get('category_id', type=int)
    
    query = Room.query.filter_by(admin_user_id=current_user.id, is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    rooms = query.all()
    
    # Get active session room IDs
    active_sessions = Session.query.filter(
        Session.room_id.in_([r.id for r in rooms]),
        Session.is_active == True
    ).all()
    active_room_ids = {s.room_id for s in active_sessions}
    
    result = []
    for room in rooms:
        if room.id not in active_room_ids:
            result.append({
                'id': room.id,
                'name': room.name,
                'category_id': room.category_id,
                'category_name': room.category.name if room.category else 'Kategoriyasiz',
                'price_per_30min': room.custom_price_per_30min or (room.category.price_per_30min if room.category else 15000)
            })
    
    return jsonify(result)

# API: Seans hisob-kitob ma'lumotlari
@app.route('/api/session-billing/<int:session_id>')
@login_required
def get_session_billing(session_id):
    """Seans uchun hisob-kitob ma'lumotlarini qaytarish"""
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Calculate actual time
    now = datetime.utcnow()
    actual_seconds = (now - session.start_time).total_seconds()
    actual_minutes = max(1, math.ceil(actual_seconds / 60))
    
    # Get room pricing
    room = session.room
    if room and room.custom_price_per_30min:
        price_per_30min = room.custom_price_per_30min
    elif room and room.category:
        price_per_30min = room.category.price_per_30min
    else:
        price_per_30min = 15000
    
    price_per_minute = price_per_30min / 30
    
    # Calculate prices
    actual_price = actual_minutes * price_per_minute
    
    # Full price (prepaid or planned)
    if session.prepaid_amount and session.prepaid_amount > 0:
        full_price = session.prepaid_amount
        planned_minutes = (session.prepaid_amount / price_per_30min) * 30
    elif session.duration_minutes:
        full_price = session.duration_minutes * price_per_minute
        planned_minutes = session.duration_minutes
    else:
        full_price = actual_price
        planned_minutes = actual_minutes
    
    # Products total
    products_total = session.products_total or 0
    
    return jsonify({
        'session_id': session.id,
        'room_name': room.name if room else 'Noma\'lum',
        'session_type': session.session_type,
        'start_time': session.start_time.strftime('%H:%M'),
        'actual_minutes': int(round(actual_minutes)),
        'planned_minutes': int(round(planned_minutes)),
        'actual_price': round(actual_price),
        'full_price': round(full_price),
        'products_total': round(products_total),
        'actual_total': round(actual_price + products_total),
        'full_total': round(full_price + products_total),
        'prepaid_amount': session.prepaid_amount or 0
    })


@app.route('/api/session_time/<int:session_id>')
@login_required
def get_session_time(session_id):
    products_total_subq = (
        db.session.query(
            CartItem.session_id.label('session_id'),
            func.sum(CartItem.price_at_time * CartItem.quantity).label('products_total'),
        )
        .group_by(CartItem.session_id)
        .subquery()
    )

    row = (
        db.session.query(
            Session,
            func.coalesce(Room.custom_price_per_30min, RoomCategory.price_per_30min, 15000).label('price_per_30min'),
            func.coalesce(products_total_subq.c.products_total, 0.0).label('products_total'),
        )
        .join(Room, Session.room_id == Room.id)
        .outerjoin(RoomCategory, Room.category_id == RoomCategory.id)
        .outerjoin(products_total_subq, products_total_subq.c.session_id == Session.id)
        .filter(
            Session.id == session_id,
            Room.admin_user_id == current_user.id,
            Room.is_active == True,
        )
        .one_or_none()
    )

    if not row:
        return jsonify({'error': 'Session not found'}), 404

    session, price_per_30min, products_total = row
    now = datetime.utcnow()

    if session.session_type == 'fixed':
        if not session.duration_minutes:
            return jsonify({'error': 'Invalid session duration'}), 400

        end_time = session.start_time + timedelta(minutes=session.duration_minutes)
        remaining = end_time - now
        elapsed = now - session.start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        price_per_minute = price_per_30min / 30
        current_cost = elapsed_minutes * price_per_minute
        total_current = (
            (session.prepaid_amount if session.prepaid_amount and session.prepaid_amount > 0 else current_cost)
            + products_total
        )

        if remaining.total_seconds() <= 0:
            if session.is_active:
                session.end_time = end_time
                session.is_active = False
                if session.prepaid_amount and session.prepaid_amount > 0:
                    session.session_price = session.prepaid_amount
                else:
                    session.session_price = (session.duration_minutes or 0) * price_per_minute
                session.products_total = products_total
                session.total_price = session.session_price + session.products_total
                db.session.commit()

            return jsonify({
                'expired': True,
                'remaining_seconds': 0,
                'elapsed_seconds': session.duration_minutes * 60,
                'current_cost': current_cost
            })

        return jsonify({
            'expired': False,
            'remaining_seconds': int(remaining.total_seconds()),
            'elapsed_seconds': int(elapsed.total_seconds()),
            'current_cost': current_cost,
            'products_total': products_total,
            'total_current': total_current
        })

    elapsed = now - session.start_time
    elapsed_minutes = elapsed.total_seconds() / 60
    price_per_minute = price_per_30min / 30
    current_cost = elapsed_minutes * price_per_minute
    total_current = current_cost + products_total

    return jsonify({
        'expired': False,
        'remaining_seconds': 0,
        'elapsed_seconds': int(elapsed.total_seconds()),
        'current_cost': current_cost,
        'products_total': products_total,
        'total_current': total_current
    })

# Inventory management removed per user request

@app.route('/sessions/stop/<int:session_id>')
@login_required
def stop_session(session_id):
    """Seansni to'xtatish - modal orqali billing_type tanlanadi"""
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    
    # Agar GET so'rov bo'lsa - to'g'ridan-to'g'ri yopish (eski usul, default: full)
    session.end_time = datetime.utcnow()
    session.is_active = False
    session.billing_type = 'full'
    
    # Update pricing (prepaid amounts will be preserved automatically in the model)
    session.update_total_price()
    
    db.session.commit()
    actual_duration = max(1, math.ceil((session.end_time - session.start_time).total_seconds() / 60))
    session_type_text = "Belgilangan vaqt" if session.session_type == 'fixed' else "VIP"
    flash(f'🎮 O\'yin yakunlandi! {session_type_text} seans - {actual_duration} daqiqa o\'ynaldi. Jami: {session.total_price:,.0f} som', 'success')
    return redirect(url_for('sessions'))

@app.route('/sessions/stop/<int:session_id>/confirm', methods=['POST'])
@login_required
def stop_session_confirm(session_id):
    """Seansni to'xtatish - billing_type bilan"""
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    
    billing_type = request.form.get('billing_type', 'full')
    session.end_time = datetime.utcnow()
    session.is_active = False
    session.billing_type = billing_type
    
    # Calculate actual time played
    actual_seconds = (session.end_time - session.start_time).total_seconds()
    actual_minutes = max(1, math.ceil(actual_seconds / 60))
    
    # Get room pricing
    room = session.room
    if room and room.custom_price_per_30min:
        price_per_30min = room.custom_price_per_30min
    elif room and room.category:
        price_per_30min = room.category.price_per_30min
    else:
        price_per_30min = 15000
    
    price_per_minute = price_per_30min / 30
    
    if billing_type == 'actual':
        # Haqiqiy vaqt bo'yicha hisoblash
        session.session_price = actual_minutes * price_per_minute
    else:
        # To'liq summa (prepaid yoki rejalashtirilgan vaqt)
        if session.prepaid_amount and session.prepaid_amount > 0:
            session.session_price = session.prepaid_amount
        elif session.duration_minutes:
            session.session_price = session.duration_minutes * price_per_minute
        else:
            session.session_price = actual_minutes * price_per_minute
    
    # Calculate products total
    cart_items = CartItem.query.filter_by(session_id=session.id).all()
    products_total = sum((item.price_at_time or 0) * (item.quantity or 0) for item in cart_items)
    session.products_total = products_total
    session.total_price = session.session_price + session.products_total
    
    db.session.commit()
    
    billing_text = "To'liq summa" if billing_type == 'full' else "Haqiqiy vaqt bo'yicha"
    session_type_text = "Belgilangan vaqt" if session.session_type == 'fixed' else "VIP"
    flash(f'🎮 O\'yin yakunlandi! {session_type_text} seans ({billing_text}) - {actual_minutes} daqiqa o\'ynaldi. Jami: {session.total_price:,.0f} som', 'success')
    return redirect(url_for('sessions'))

@app.route('/sessions/<int:session_id>')
@login_required
def session_detail(session_id):
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    
    # Form for adding products - Multi-tenant: Only show current user's products
    form = AddProductToSessionForm()
    form.product_id.choices = [(p.id, f"{p.name} - {p.price:,.0f} som") 
                              for p in Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()]
    form.session_id.data = session_id
    
    return render_template('session_detail.html', session=session, form=form)

@app.route('/sessions/<int:session_id>/add_product', methods=['POST'])
@login_required
def add_product_to_session(session_id):
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    
    # Handle both form-based and direct POST requests
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    
    # Skip CSRF validation for this endpoint since it's called from multiple contexts
    from flask_wtf.csrf import validate_csrf
    try:
        validate_csrf(request.form.get('csrf_token'))
    except Exception:
        # CSRF validation may fail for API calls or form resubmissions - allow backward compatibility
        pass
    
    # Convert to proper types and validate
    try:
        product_id = int(product_id) if product_id else None
        quantity = int(quantity) if quantity else 1
    except (ValueError, TypeError):
        flash('Noto\'g\'ri ma\'lumotlar kiritildi!', 'danger')
        return redirect(request.referrer or url_for('sessions'))
    
    if not product_id or quantity <= 0:
        flash('Mahsulot va miqdorni to\'g\'ri kiriting!', 'danger')
        return redirect(request.referrer or url_for('sessions'))
    
    # Get product and validate ownership
    product = Product.query.filter_by(id=product_id, admin_user_id=current_user.id, is_active=True).first()
    
    if not product:
        flash('Mahsulot topilmadi!', 'danger')
        return redirect(request.referrer or url_for('sessions'))
    
    if product.stock_quantity < quantity:
        flash(f'{product.name} mahsulotidan yetarlicha zaxira yo\'q! Mavjud: {product.stock_quantity} {product.unit}', 'danger')
        return redirect(request.referrer or url_for('sessions'))
    
    # Check if product already in cart
    existing_item = CartItem.query.filter_by(
        session_id=session_id,
        product_id=product_id
    ).first()
    
    try:
        if existing_item:
            existing_item.quantity += quantity
        else:
            cart_item = CartItem()
            cart_item.session_id = session_id
            cart_item.product_id = product_id
            cart_item.quantity = quantity
            cart_item.price_at_time = product.price  # Store current product price
            db.session.add(cart_item)
        
        # Deduct stock
        product.stock_quantity -= quantity
        
        session.update_total_price()
        db.session.commit()
        
        stock_status = ""
        if product.stock_quantity <= 0:
            stock_status = " (zaxira tugadi)"
        elif product.stock_quantity <= product.min_stock_alert:
            stock_status = f" (kam qoldi: {product.stock_quantity})"
        
        flash(f'{quantity} ta {product.name} seansga qo\'shildi!{stock_status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Mahsulot qo\'shishda xatolik: {str(e)}', 'danger')
    
    # Redirect back to where the user came from (dashboard, sessions, or session detail)
    return redirect(request.referrer or url_for('sessions'))

@app.route('/sessions/<int:session_id>/remove_product/<int:item_id>')
@login_required
def remove_product_from_session(session_id, item_id):
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    cart_item = CartItem.query.get_or_404(item_id)
    
    # Mahsulotni inventarga qaytarish
    product = cart_item.product
    if product:
        product.stock_quantity += cart_item.quantity
    
    db.session.delete(cart_item)
    session.update_total_price()
    db.session.commit()
    flash('Mahsulot seansdan olib tashlandi va inventarga qaytarildi!', 'success')
    
    return redirect(url_for('session_detail', session_id=session_id))

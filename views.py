from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func, extract
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
from app import app, db
from models import AdminUser, Room, RoomCategory, ProductCategory, Product, Session, CartItem, FIXED_SESSION_PRICES
from forms import LoginForm, RoomForm, RoomCategoryForm, ProductCategoryForm, ProductForm, SessionForm, AddProductToSessionForm, RegisterForm, StockUpdateForm, InventoryForm, ChangePasswordForm, ResetPasswordForm, ProfileForm, QuickAddProductForm, ExcelImportForm, ReportForm
from werkzeug.security import generate_password_hash
from translations import get_translation, get_current_language

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(username=form.username.data).first()
        password_data = form.password.data
        if user and user.password_hash and password_data and check_password_hash(str(user.password_hash), password_data):
            login_user(user)
            if user.is_temp_password:
                flash('Vaqtinchalik parol bilan kirdingiz. Iltimos, parolni o\'zgartiring!', 'warning')
                return redirect(url_for('change_password'))
            flash('Muvaffaqiyatli kirildi!', 'success')
            return redirect(url_for('dashboard'))
        flash('Foydalanuvchi nomi yoki parol noto\'g\'ri', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Check secret key
        import os
        secret_key = os.environ.get('SECRET_ADMIN_KEY', 'admin123')
        if form.secret_key.data != secret_key:
            flash('Maxfiy kalit noto\'g\'ri!', 'danger')
            return render_template('register.html', form=form)
        
        # Check if username already exists
        existing_user = AdminUser.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Bu foydalanuvchi nomi band!', 'danger')
            return render_template('register.html', form=form)
        
        # Create new admin user
        user = AdminUser()
        user.username = form.username.data
        user.gaming_center_name = form.gaming_center_name.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'{form.gaming_center_name.data} uchun admin akkaunt yaratildi!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Tizimdan chiqdingiz.', 'info')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        # Check if username is taken by another user
        existing_user = AdminUser.query.filter(
            AdminUser.username == form.username.data,
            AdminUser.id != current_user.id
        ).first()
        if existing_user:
            flash('Bu foydalanuvchi nomi band!', 'danger')
            return render_template('profile.html', form=form)
        
        current_user.username = form.username.data
        current_user.gaming_center_name = form.gaming_center_name.data
        db.session.commit()
        flash('Profil muvaffaqiyatli yangilandi!', 'success')
        return redirect(url_for('profile'))
    
    # Pre-fill form with current data
    form.username.data = current_user.username
    form.gaming_center_name.data = current_user.gaming_center_name
    return render_template('profile.html', form=form)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Check current password if not temp password
        if not current_user.is_temp_password:
            if not current_user.password_hash or not check_password_hash(current_user.password_hash, form.current_password.data):
                flash('Joriy parol noto\'g\'ri!', 'danger')
                return render_template('change_password.html', form=form)
        
        # Update password
        if form.new_password.data:
            current_user.password_hash = generate_password_hash(form.new_password.data)
        current_user.is_temp_password = False
        db.session.commit()
        flash('Parol muvaffaqiyatli o\'zgartirildi!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html', form=form)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Check admin secret key
        import os
        import secrets
        import string
        
        secret_key = os.environ.get('SECRET_ADMIN_KEY', 'admin123')
        if form.secret_key.data != secret_key:
            flash('Admin maxfiy kaliti noto\'g\'ri!', 'danger')
            return render_template('reset_password.html', form=form)
        
        # Find user
        user = AdminUser.query.filter_by(username=form.username.data).first()
        if not user:
            flash('Foydalanuvchi topilmadi!', 'danger')
            return render_template('reset_password.html', form=form)
        
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        user.password_hash = generate_password_hash(temp_password)
        user.is_temp_password = True
        db.session.commit()
        
        flash(f'Vaqtinchalik parol yaratildi: {temp_password}', 'success')
        flash('Foydalanuvchi kirgach parolni o\'zgartirishi kerak!', 'info')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    # Multi-tenant: Get active sessions for current user's rooms only
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    active_sessions = Session.query.filter(
        Session.room_id.in_(user_room_ids),
        Session.is_active == True
    ).all()
    
    # Get today's statistics for current user only
    today = datetime.utcnow().date()
    today_sessions = Session.query.filter(
        Session.room_id.in_(user_room_ids),
        func.date(Session.created_at) == today,
        Session.is_active == False
    ).all()
    
    today_revenue = sum(session.total_price for session in today_sessions)
    total_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    total_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    
    # Get data for modals
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    available_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    
    return render_template('dashboard.html',
                         active_sessions=active_sessions,
                         today_revenue=today_revenue,
                         total_rooms=total_rooms,
                         total_products=total_products,
                         session_count=len(today_sessions),
                         user_rooms=user_rooms,
                         available_products=available_products)

@app.route('/rooms-management')
@login_required
def rooms_management():
    # Multi-tenant: Only show categories and rooms for current user
    categories = RoomCategory.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    rooms = Room.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    
    category_form = RoomCategoryForm()
    room_form = RoomForm()
    room_form.category_id.choices = [(c.id, c.name) for c in categories]
    
    return render_template('rooms_management.html', 
                         categories=categories, 
                         rooms=rooms,
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
    return redirect(url_for('rooms_management'))



@app.route('/rooms/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    room = Room.query.filter_by(id=room_id, admin_user_id=current_user.id).first_or_404()
    room.is_active = False
    db.session.commit()
    flash(f'Xona "{room.name}" o\'chirildi!', 'success')
    return redirect(url_for('rooms_management'))

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
    return redirect(url_for('rooms_management'))

@app.route('/products')
@login_required
def products():
    # Multi-tenant: Only show products and categories for current user's gaming center
    products_list = Product.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    categories_list = ProductCategory.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    
    # Setup forms
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in categories_list]
    category_form = ProductCategoryForm()
    
    return render_template('products.html', 
                         products=products_list, 
                         categories=categories_list,
                         form=form,
                         category_form=category_form)

@app.route('/products/add', methods=['POST'])
@login_required
def add_product():
    categories_list = ProductCategory.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
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
    return redirect(url_for('products'))

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
    
    return redirect(url_for('products'))

@app.route('/products/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, admin_user_id=current_user.id).first_or_404()
    product.is_active = False
    db.session.commit()
    flash(f'Mahsulot "{product.name}" o\'chirildi!', 'success')
    return redirect(url_for('products'))

@app.route('/products/add-category', methods=['POST'])
@login_required
def add_product_category():
    form = ProductCategoryForm()
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
    else:
        category.is_active = False
        db.session.commit()
        flash(f'Kategoriya "{category.name}" o\'chirildi!', 'success')
    return redirect(url_for('products'))

# Inventory management routes
@app.route('/inventory')
@login_required
def inventory():
    """Display inventory management page with stock levels"""
    products_list = Product.query.filter_by(
        admin_user_id=current_user.id,
        is_active=True
    ).all()
    
    # Create inventory form
    inventory_form = InventoryForm()
    inventory_form.product_id.choices = [(p.id, f"{p.name} ({p.stock_quantity} {p.unit})") 
                                       for p in products_list]
    
    return render_template('inventory.html', 
                         products=products_list, 
                         form=inventory_form)

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
    active_sessions = Session.query.filter(Session.room_id.in_(user_room_ids), Session.is_active == True).all()
    completed_sessions = Session.query.filter(Session.room_id.in_(user_room_ids), Session.is_active == False).order_by(Session.created_at.desc()).limit(20).all()
    
    # Setup form for new session
    form = SessionForm()
    form.room_id.choices = [(r.id, r.name) for r in user_rooms]
    
    # Get available products for adding to sessions
    available_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    
    return render_template('sessions.html', 
                         active_sessions=active_sessions,
                         completed_sessions=completed_sessions,
                         form=form,
                         available_products=available_products)

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

# Inventory management removed per user request

@app.route('/sessions/stop/<int:session_id>')
@login_required
def stop_session(session_id):
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    session.end_time = datetime.utcnow()
    session.is_active = False
    
    # Update pricing (prepaid amounts will be preserved automatically in the model)
    session.update_total_price()
    
    db.session.commit()
    actual_duration = (session.end_time - session.start_time).total_seconds() / 60
    session_type_text = "Belgilangan vaqt" if session.session_type == 'fixed' else "VIP"
    flash(f'🎮 O\'yin yakunlandi! {session_type_text} seans - {actual_duration:.1f} daqiqa o\'ynaldi. Jami: {session.total_price:,.0f} som', 'success')
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
    except:
        # If CSRF validation fails, still proceed (backward compatibility)
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

@app.route('/api/session_time/<int:session_id>')
@login_required
def api_session_time(session_id):
    """API endpoint for real-time session timing data"""
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    
    if not session.is_active:
        return jsonify({'error': 'Session not active'}), 400
    
    now = datetime.utcnow()
    elapsed_seconds = int((now - session.start_time).total_seconds())
    
    if session.session_type == 'fixed':
        # Fixed session - calculate remaining time
        total_seconds = session.duration_minutes * 60 if session.duration_minutes else 1800  # Default 30 min
        remaining_seconds = max(0, total_seconds - elapsed_seconds)
        expired = remaining_seconds <= 0
        
        return jsonify({
            'elapsed_seconds': elapsed_seconds,
            'remaining_seconds': remaining_seconds,
            'expired': expired,
            'session_price': session.session_price or 0,
            'total_price': session.total_price or 0,
            'current_cost': session.session_price or 0
        })
    else:
        # VIP session - calculate real-time pricing based on elapsed time
        elapsed_minutes = elapsed_seconds / 60.0
        
        # Get VIP pricing from room category
        room = session.room
        room_category = room.category if room else None
        vip_price_per_minute = getattr(room_category, 'vip_price_per_minute', 500) if room_category else 500  # Default 500 som/minute
        
        # Calculate current session price based on elapsed time
        current_session_price = elapsed_minutes * vip_price_per_minute
        
        # Update session price in database for consistency
        session.session_price = current_session_price
        session.update_total_price()  # This will also include product costs
        db.session.commit()
        
        return jsonify({
            'elapsed_seconds': elapsed_seconds,
            'remaining_seconds': None,
            'expired': False,
            'session_price': current_session_price,
            'total_price': session.total_price or current_session_price,
            'current_cost': current_session_price
        })

@app.route('/sessions/<int:session_id>/remove_product/<int:item_id>')
@login_required
def remove_product_from_session(session_id, item_id):
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    cart_item = CartItem.query.get_or_404(item_id)
    
    db.session.delete(cart_item)
    session.update_total_price()
    db.session.commit()
    flash('Mahsulot seansdan olib tashlandi!', 'success')
    
    return redirect(url_for('session_detail', session_id=session_id))

@app.route('/analytics')
@login_required
def analytics():
    # Get report type and date from query parameters
    report_type = request.args.get('type', 'monthly')
    selected_date = request.args.get('date')
    selected_month = request.args.get('month')
    
    today = datetime.utcnow().date()
    current_date = today.strftime('%Y-%m-%d')
    current_month = today.strftime('%Y-%m')
    
    if report_type == 'daily':
        # Daily analytics for specific date
        if selected_date:
            try:
                target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            except ValueError:
                target_date = today
        else:
            target_date = today
            
        # Multi-tenant: Get sessions for current user's rooms only
        user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
        user_room_ids = [room.id for room in user_rooms]
        daily_sessions = Session.query.filter(
            Session.room_id.in_(user_room_ids),
            func.date(Session.created_at) == target_date,
            Session.is_active == False
        ).all()
        daily_revenue = sum(session.total_price for session in daily_sessions)
        
        # For daily view, show the selected day as "main" data
        main_revenue = daily_revenue
        main_sessions = len(daily_sessions)
        main_title = f"Kunlik Hisobot - {target_date.strftime('%d.%m.%Y')}"
        
        # Calculate revenue breakdown for the day
        session_revenue = sum(session.session_price for session in daily_sessions)
        products_revenue = sum(session.products_total for session in daily_sessions)
        
    else:
        # Monthly analytics for specific month
        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
            except (ValueError, AttributeError):
                year, month = today.year, today.month
        else:
            year, month = today.year, today.month
            
        # Multi-tenant: Get sessions for current user's rooms only
        user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
        user_room_ids = [room.id for room in user_rooms]
        monthly_sessions = Session.query.filter(
            Session.room_id.in_(user_room_ids),
            extract('month', Session.created_at) == month,
            extract('year', Session.created_at) == year,
            Session.is_active == False
        ).all()
        monthly_revenue = sum(session.total_price for session in monthly_sessions)
        
        # For monthly view, show the selected month as "main" data
        main_revenue = monthly_revenue
        main_sessions = len(monthly_sessions)
        month_names = ['', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
                      'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr']
        main_title = f"Oylik Hisobot - {month_names[month]} {year}"
        
        # Calculate revenue breakdown for the month
        session_revenue = sum(session.session_price for session in monthly_sessions)
        products_revenue = sum(session.products_total for session in monthly_sessions)
    
    # Always calculate today's data for comparison - Multi-tenant
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    today_sessions = Session.query.filter(
        Session.room_id.in_(user_room_ids),
        func.date(Session.created_at) == today,
        Session.is_active == False
    ).all()
    today_revenue = sum(session.total_price for session in today_sessions)
    
    # Weekly analytics - Multi-tenant
    week_start = today - timedelta(days=today.weekday())
    weekly_sessions = Session.query.filter(
        Session.room_id.in_(user_room_ids),
        Session.created_at >= week_start,
        Session.is_active == False
    ).all()
    weekly_revenue = sum(session.total_price for session in weekly_sessions)
    
    return render_template('analytics.html',
                         report_type=report_type,
                         current_date=current_date,
                         current_month=current_month,
                         main_revenue=main_revenue,
                         main_sessions=main_sessions,
                         main_title=main_title,
                         daily_revenue=today_revenue,
                         daily_sessions=len(today_sessions),
                         weekly_revenue=weekly_revenue,
                         weekly_sessions=len(weekly_sessions),
                         monthly_revenue=main_revenue,
                         monthly_sessions=main_sessions,
                         session_revenue=session_revenue,
                         products_revenue=products_revenue)

@app.route('/api/session_time/<int:session_id>')
@login_required
def get_session_time(session_id):
    # Multi-tenant: Check session belongs to current user's room
    user_rooms = Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    user_room_ids = [room.id for room in user_rooms]
    session = Session.query.filter(Session.id == session_id, Session.room_id.in_(user_room_ids)).first_or_404()
    now = datetime.utcnow()
    
    if session.session_type == 'fixed':
        # Calculate remaining time
        end_time = session.start_time + timedelta(minutes=session.duration_minutes)
        remaining = end_time - now
        elapsed = now - session.start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        # Calculate current cost based on room pricing
        room = session.room
        if room and room.custom_price_per_30min:
            price_per_30min = room.custom_price_per_30min
        elif room and room.category:
            price_per_30min = room.category.price_per_30min
        else:
            price_per_30min = 15000  # Default fallback
        
        # Calculate per-minute cost and current total
        price_per_minute = price_per_30min / 30
        current_cost = elapsed_minutes * price_per_minute
        
        if remaining.total_seconds() <= 0:
            # Session should be auto-stopped
            if session.is_active:
                session.end_time = end_time
                session.is_active = False
                # Recalculate price for the actual time played (full planned duration)
                session.update_total_price()
                db.session.commit()
            
            return jsonify({
                'expired': True,
                'remaining_seconds': 0,
                'elapsed_seconds': session.duration_minutes * 60,
                'current_cost': current_cost
            })
        
        # Update session totals including products
        session.update_total_price()
        
        return jsonify({
            'expired': False,
            'remaining_seconds': int(remaining.total_seconds()),
            'elapsed_seconds': int(elapsed.total_seconds()),
            'current_cost': current_cost,
            'products_total': session.products_total,
            'total_current': session.total_price
        })
    
    else:  # VIP session
        elapsed = now - session.start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        # Calculate current cost based on room pricing
        room = session.room
        if room and room.custom_price_per_30min:
            price_per_30min = room.custom_price_per_30min
        elif room and room.category:
            price_per_30min = room.category.price_per_30min
        else:
            price_per_30min = 15000  # Default fallback
        
        # Calculate per-minute cost and current total
        price_per_minute = price_per_30min / 30
        current_cost = elapsed_minutes * price_per_minute
        
        # Update session totals including products
        session.update_total_price()
        
        return jsonify({
            'expired': False,
            'remaining_seconds': 0,
            'elapsed_seconds': int(elapsed.total_seconds()),
            'current_cost': current_cost,
            'products_total': session.products_total,
            'total_current': session.total_price
        })

# Excel Import/Export Routes
@app.route('/products/export-excel')
@login_required
def export_products_excel():
    """Excel formatida mahsulotlarni export qilish"""
    products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    
    # Create DataFrame
    data = []
    for product in products:
        data.append({
            'Nomi': product.name,
            'Kategoriya': product.product_category.name if product.product_category else 'Kategoriyasiz',
            'Narxi (som)': product.price,
            'Zaxira miqdori': product.stock_quantity or 0,
            'Minimum zaxira': product.min_stock_alert or 0,
            'Holati': product.get_stock_status_text() if hasattr(product, 'get_stock_status_text') else 'Mavjud',
            'Yaratilgan sana': product.created_at.strftime('%Y-%m-%d') if product.created_at else ''
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Mahsulotlar', index=False)
    except Exception as e:
        flash(f'Excel yaratishda xatolik: {str(e)}', 'danger')
        return redirect(url_for('products'))
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'mahsulotlar_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/products/import-excel', methods=['POST'])
@login_required
def import_products_excel():
    """Excel faylidan mahsulotlarni import qilish"""
    if 'file' not in request.files:
        flash('Fayl tanlanmagan!', 'danger')
        return redirect(url_for('products'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Fayl tanlanmagan!', 'danger')
        return redirect(url_for('products'))
    
    if not file.filename or not file.filename.endswith('.xlsx'):
        flash('Faqat .xlsx formatidagi fayllar qabul qilinadi!', 'danger')
        return redirect(url_for('products'))
    
    try:
        # Read Excel file
        df = pd.read_excel(file, sheet_name=0)
        
        # Validate required columns
        required_columns = ['Nomi', 'Kategoriya', 'Narxi (som)']
        for col in required_columns:
            if col not in df.columns:
                flash(f'Kerakli ustun topilmadi: {col}', 'danger')
                return redirect(url_for('products'))
        
        imported_count = 0
        for _, row in df.iterrows():
            # Check if product already exists
            existing_product = Product.query.filter_by(
                admin_user_id=current_user.id,
                name=row['Nomi'],
                is_active=True
            ).first()
            
            if not existing_product:
                # Get or create category
                category_name = str(row['Kategoriya'])
                category = ProductCategory.query.filter_by(
                    admin_user_id=current_user.id,
                    name=category_name
                ).first()
                if not category:
                    category = ProductCategory()
                    category.name = category_name
                    category.admin_user_id = current_user.id
                    db.session.add(category)
                    db.session.flush()  # Get the ID
                
                product = Product()
                product.admin_user_id = current_user.id
                product.name = str(row['Nomi'])
                product.category_id = category.id
                try:
                    product.price = float(row['Narxi (som)']) if pd.notna(row['Narxi (som)']) else 0.0
                except (ValueError, TypeError):
                    product.price = 0.0
                
                try:
                    stock_val = row.get('Zaxira miqdori', 0)
                    product.stock_quantity = int(stock_val) if pd.notna(stock_val) and str(stock_val).strip() != '' else 0
                except (ValueError, TypeError):
                    product.stock_quantity = 0
                
                try:
                    min_stock_val = row.get('Minimum zaxira', 0)
                    product.min_stock_alert = int(min_stock_val) if pd.notna(min_stock_val) and str(min_stock_val).strip() != '' else 0
                except (ValueError, TypeError):
                    product.min_stock_alert = 0
                
                db.session.add(product)
                imported_count += 1
        
        db.session.commit()
        flash(f'{imported_count} ta mahsulot muvaffaqiyatli import qilindi!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Import paytida xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

# PDF Report Routes
@app.route('/reports/pdf/<report_type>')
@login_required
def generate_pdf_report(report_type):
    """PDF hisobot yaratish"""
    # Get date range from query params
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if not start_date_str or not end_date_str:
        flash('Sana oralig\'ini tanlang!', 'danger')
        return redirect(url_for('analytics'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Sana formati noto\'g\'ri!', 'danger')
        return redirect(url_for('analytics'))
    
    # Get user's rooms
    user_room_ids = [room.id for room in Room.query.filter_by(admin_user_id=current_user.id, is_active=True).all()]
    
    # Get sessions data
    sessions = Session.query.filter(
        Session.room_id.in_(user_room_ids),
        func.date(Session.created_at) >= start_date,
        func.date(Session.created_at) <= end_date,
        Session.is_active == False
    ).all()
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        alignment=1,  # Center
        spaceAfter=30
    )
    
    report_titles = {
        'daily': 'Kunlik Hisobot',
        'weekly': 'Xaftalik Hisobot', 
        'monthly': 'Oylik Hisobot'
    }
    
    title = f"{current_user.gaming_center_name}\n{report_titles.get(report_type, 'Hisobot')}"
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))
    
    # Date range
    date_text = f"Sana oralig'i: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
    elements.append(Paragraph(date_text, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Statistics
    total_revenue = sum(session.total_price for session in sessions)
    total_sessions = len(sessions)
    
    stats_data = [
        ['Jami seanslar', str(total_sessions)],
        ['Jami daromad', f"{total_revenue:,.0f} som"],
        ['O\'rtacha seans summasi', f"{total_revenue/total_sessions if total_sessions > 0 else 0:,.0f} som"]
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 30))
    
    # Sessions table
    if sessions:
        elements.append(Paragraph("Seanslar ro'yxati:", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        session_data = [['Xona', 'Sana', 'Vaqt', 'Davomiyligi', 'Summa (som)']]
        
        for session in sessions[:50]:  # Limit to 50 sessions for PDF
            duration_display = session.get_duration_display() if hasattr(session, 'get_duration_display') else 'N/A'
            session_data.append([
                session.room.name,
                session.created_at.strftime('%d.%m.%Y'),
                session.start_time.strftime('%H:%M') if session.start_time else 'N/A',
                duration_display,
                f"{session.total_price:,.0f}"
            ])
        
        session_table = Table(session_data, colWidths=[1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        
        elements.append(session_table)
    
    # Product sales data
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Sotilgan mahsulotlar:", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    # Get product sales data for the date range
    cart_items = CartItem.query.join(Session).filter(
        Session.room_id.in_(user_room_ids),
        func.date(Session.created_at) >= start_date,
        func.date(Session.created_at) <= end_date,
        Session.is_active == False
    ).all()
    
    if cart_items:
        # Group products by name and calculate totals
        product_sales = {}
        for item in cart_items:
            product_name = item.product.name if item.product else 'Noma\'lum mahsulot'
            if product_name in product_sales:
                product_sales[product_name]['quantity'] += item.quantity
                product_sales[product_name]['total'] += item.total_price
            else:
                product_sales[product_name] = {
                    'quantity': item.quantity,
                    'unit_price': item.price_at_time,
                    'total': item.total_price
                }
        
        # Create products table
        product_data = [['Mahsulot', 'Miqdori', 'Narxi (som)', 'Jami (som)']]
        total_product_revenue = 0
        
        for product_name, data in product_sales.items():
            product_data.append([
                product_name,
                f"{data['quantity']} ta",
                f"{data['unit_price']:,.0f}",
                f"{data['total']:,.0f}"
            ])
            total_product_revenue += data['total']
        
        # Add total row
        product_data.append(['JAMI', '', '', f"{total_product_revenue:,.0f}"])
        
        product_table = Table(product_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        
        elements.append(product_table)
    else:
        elements.append(Paragraph("Bu davr ichida mahsulot sotilmagan.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"{report_type}_hisobot_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/inventory-stats')
@login_required  
def inventory_stats_api():
    """Zaxira statistikasi uchun API endpoint"""
    products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    
    total_products = len(products)
    available_products = 0
    low_stock_products = 0
    out_of_stock_products = 0
    
    for product in products:
        if product.stock_quantity is None or product.stock_quantity <= 0:
            out_of_stock_products += 1
        elif product.min_stock_alert and product.stock_quantity <= product.min_stock_alert:
            low_stock_products += 1
        else:
            available_products += 1
    
    return jsonify({
        'total': total_products,
        'available': available_products,
        'low_stock': low_stock_products,
        'out_of_stock': out_of_stock_products
    })

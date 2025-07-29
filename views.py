from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import math
from app import app, db
from models import AdminUser, Room, RoomCategory, ProductCategory, Product, Session, CartItem, FIXED_SESSION_PRICES
from forms import LoginForm, RoomForm, RoomCategoryForm, ProductCategoryForm, ProductForm, SessionForm, AddProductToSessionForm, RegisterForm
from werkzeug.security import generate_password_hash

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
        if user and user.password_hash and password_data and check_password_hash(user.password_hash, password_data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    
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
        
        # Check if email already exists
        existing_email = AdminUser.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Bu email allaqachon ro\'yxatdan o\'tgan!', 'danger')
            return render_template('register.html', form=form)
        
        # Create new admin user
        user = AdminUser()
        user.username = form.username.data
        user.email = form.email.data
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
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

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
    
    return render_template('dashboard.html',
                         active_sessions=active_sessions,
                         today_revenue=today_revenue,
                         total_rooms=total_rooms,
                         total_products=total_products,
                         session_count=len(today_sessions))

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

@app.route('/room-categories/<int:category_id>/edit', methods=['POST'])
@login_required
def edit_room_category(category_id):
    category = RoomCategory.query.filter_by(id=category_id, admin_user_id=current_user.id).first_or_404()
    form = RoomCategoryForm()
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.price_per_30min = form.price_per_30min.data
        db.session.commit()
        flash(f'Kategoriya "{category.name}" yangilandi!', 'success')
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

@app.route('/rooms/<int:room_id>/edit', methods=['POST'])
@login_required
def edit_room(room_id):
    room = Room.query.filter_by(id=room_id, admin_user_id=current_user.id).first_or_404()
    form = RoomForm()
    form.category_id.choices = [(c.id, c.name) for c in RoomCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).all()]
    if form.validate_on_submit():
        room.name = form.name.data
        room.description = form.description.data
        room.category_id = form.category_id.data
        room.custom_price_per_30min = form.custom_price_per_30min.data
        db.session.commit()
        flash(f'Xona "{room.name}" yangilandi!', 'success')
    return redirect(url_for('rooms_management'))

@app.route('/rooms/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    room = Room.query.filter_by(id=room_id, admin_user_id=current_user.id).first_or_404()
    room.is_active = False
    db.session.commit()
    flash(f'Xona "{room.name}" o\'chirildi!', 'success')
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
        db.session.add(product)
        db.session.commit()
        
        flash(f'Mahsulot "{product.name}" muvaffaqiyatli qo\'shildi!', 'success')
    else:
        flash('Mahsulot qo\'shishda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
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
    form = ProductCategoryForm()
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash(f'Kategoriya "{category.name}" yangilandi!', 'success')
    else:
        flash('Kategoriya yangilashda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
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
    
    return render_template('sessions.html', 
                         active_sessions=active_sessions,
                         completed_sessions=completed_sessions,
                         form=form)

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
                # For example: if room costs 20000 per 30min and user enters 1000, 
                # they get (1000/20000)*30 = 1.5 minutes of play time
                calculated_seconds = (target_amount / price_per_30min) * 30 * 60  # Convert to seconds
                total_seconds = max(int(calculated_seconds), 60)  # Minimum 1 minute (60 seconds)
                total_minutes = total_seconds / 60  # Keep as float for precise timing
                
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
    form = AddProductToSessionForm()
    form.product_id.choices = [(p.id, f"{p.name} - {p.price:,.0f} som") 
                              for p in Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()]
    
    if form.validate_on_submit():
        product = Product.query.filter_by(id=form.product_id.data, admin_user_id=current_user.id).first()
        quantity = form.quantity.data
        
        # Check if product already in cart
        existing_item = CartItem.query.filter_by(
            session_id=session_id,
            product_id=form.product_id.data
        ).first()
        
        if existing_item:
            existing_item.quantity += form.quantity.data
        else:
            cart_item = CartItem()
            cart_item.session_id = session_id
            cart_item.product_id = form.product_id.data
            cart_item.quantity = form.quantity.data
            db.session.add(cart_item)
        
        session.update_total_price()
        db.session.commit()
        if product and product.name:
            flash(f'{quantity} ta {product.name} seansga qo\'shildi!', 'success')
        else:
            flash(f'{quantity} ta mahsulot seansga qo\'shildi!', 'success')
    else:
        flash('Mahsulot qo\'shishda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    
    return redirect(url_for('session_detail', session_id=session_id))

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
                         monthly_revenue=main_revenue if report_type == 'monthly' else 0,
                         monthly_sessions=main_sessions if report_type == 'monthly' else 0,
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
        
        return jsonify({
            'expired': False,
            'remaining_seconds': int(remaining.total_seconds()),
            'elapsed_seconds': int(elapsed.total_seconds()),
            'current_cost': current_cost
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
        
        return jsonify({
            'expired': False,
            'remaining_seconds': 0,
            'elapsed_seconds': int(elapsed.total_seconds()),
            'current_cost': current_cost
        })

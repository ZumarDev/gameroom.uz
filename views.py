from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from app import app, db
from models import AdminUser, Room, RoomCategory, Product, Session, CartItem, FIXED_SESSION_PRICES
from forms import LoginForm, RoomForm, RoomCategoryForm, ProductForm, SessionForm, AddProductToSessionForm, RegisterForm
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
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get active sessions
    active_sessions = Session.query.filter_by(is_active=True).all()
    
    # Get today's statistics
    today = datetime.utcnow().date()
    today_sessions = Session.query.filter(
        func.date(Session.created_at) == today,
        Session.is_active == False
    ).all()
    
    today_revenue = sum(session.total_price for session in today_sessions)
    total_rooms = Room.query.filter_by(is_active=True).count()
    total_products = Product.query.filter_by(is_active=True).count()
    
    return render_template('dashboard.html',
                         active_sessions=active_sessions,
                         today_revenue=today_revenue,
                         total_rooms=total_rooms,
                         total_products=total_products,
                         session_count=len(today_sessions))

@app.route('/room-categories')
@login_required
def room_categories():
    categories = RoomCategory.query.filter_by(is_active=True).all()
    form = RoomCategoryForm()
    return render_template('room_categories.html', categories=categories, form=form)

@app.route('/room-categories/add', methods=['POST'])
@login_required
def add_room_category():
    form = RoomCategoryForm()
    if form.validate_on_submit():
        category = RoomCategory(
            name=form.name.data,
            description=form.description.data,
            price_per_30min=form.price_per_30min.data
        )
        db.session.add(category)
        db.session.commit()
        flash(f'Kategoriya "{category.name}" muvaffaqiyatli yaratildi!', 'success')
    return redirect(url_for('room_categories'))

@app.route('/room-categories/<int:category_id>/edit', methods=['POST'])
@login_required
def edit_room_category(category_id):
    category = RoomCategory.query.get_or_404(category_id)
    form = RoomCategoryForm()
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.price_per_30min = form.price_per_30min.data
        db.session.commit()
        flash(f'Kategoriya "{category.name}" yangilandi!', 'success')
    return redirect(url_for('room_categories'))

@app.route('/room-categories/<int:category_id>/delete')
@login_required
def delete_room_category(category_id):
    category = RoomCategory.query.get_or_404(category_id)
    category.is_active = False
    db.session.commit()
    flash(f'Kategoriya "{category.name}" o\'chirildi!', 'success')
    return redirect(url_for('room_categories'))

@app.route('/rooms')
@login_required
def rooms():
    rooms_list = Room.query.filter_by(is_active=True).all()
    form = RoomForm()
    form.category_id.choices = [(c.id, c.name) for c in RoomCategory.query.filter_by(is_active=True).all()]
    return render_template('rooms.html', rooms=rooms_list, form=form)

@app.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    form = RoomForm()
    form.category_id.choices = [(c.id, c.name) for c in RoomCategory.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        room = Room(
            name=form.name.data,
            description=form.description.data,
            category_id=form.category_id.data,
            custom_price_per_30min=form.custom_price_per_30min.data
        )
        db.session.add(room)
        db.session.commit()
        flash(f'Xona "{room.name}" muvaffaqiyatli yaratildi!', 'success')
    else:
        flash('Xona qo\'shishda xatolik. Ma\'lumotlarni tekshiring.', 'danger')
    return redirect(url_for('rooms'))

@app.route('/rooms/<int:room_id>/edit', methods=['POST'])
@login_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomForm()
    form.category_id.choices = [(c.id, c.name) for c in RoomCategory.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        room.name = form.name.data
        room.description = form.description.data
        room.category_id = form.category_id.data
        room.custom_price_per_30min = form.custom_price_per_30min.data
        db.session.commit()
        flash(f'Xona "{room.name}" yangilandi!', 'success')
    return redirect(url_for('rooms'))

@app.route('/rooms/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    room.is_active = False
    db.session.commit()
    flash(f'Xona "{room.name}" o\'chirildi!', 'success')
    return redirect(url_for('rooms'))

@app.route('/products')
@login_required
def products():
    products_list = Product.query.filter_by(is_active=True).all()
    form = ProductForm()
    return render_template('products.html', products=products_list, form=form)

@app.route('/products/add', methods=['POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            category=form.category.data,
            price=form.price.data
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{product.name}" added successfully!', 'success')
    else:
        flash('Error adding product. Please check your input.', 'danger')
    return redirect(url_for('products'))

@app.route('/products/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    flash(f'Product "{product.name}" deleted successfully!', 'success')
    return redirect(url_for('products'))

@app.route('/sessions')
@login_required
def sessions():
    active_sessions = Session.query.filter_by(is_active=True).all()
    completed_sessions = Session.query.filter_by(is_active=False).order_by(Session.created_at.desc()).limit(20).all()
    
    # Setup form for new session
    form = SessionForm()
    form.room_id.choices = [(r.id, r.name) for r in Room.query.filter_by(is_active=True).all()]
    
    return render_template('sessions.html', 
                         active_sessions=active_sessions,
                         completed_sessions=completed_sessions,
                         form=form)

@app.route('/sessions/start', methods=['POST'])
@login_required
def start_session():
    form = SessionForm()
    form.room_id.choices = [(r.id, r.name) for r in Room.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Check if room is already in use
        existing_session = Session.query.filter_by(room_id=form.room_id.data, is_active=True).first()
        if existing_session:
            flash('This room is already in use!', 'danger')
            return redirect(url_for('sessions'))
        
        session = Session(
            room_id=form.room_id.data,
            session_type=form.session_type.data
        )
        
        if form.session_type.data == 'fixed':
            session.duration_minutes = form.duration_minutes.data
            session.session_price = FIXED_SESSION_PRICES.get(form.duration_minutes.data, 0)
        
        session.total_price = session.session_price
        db.session.add(session)
        db.session.commit()
        flash('Session started successfully!', 'success')
    else:
        flash('Error starting session. Please check your input.', 'danger')
    
    return redirect(url_for('sessions'))

@app.route('/sessions/stop/<int:session_id>')
@login_required
def stop_session(session_id):
    session = Session.query.get_or_404(session_id)
    session.end_time = datetime.utcnow()
    session.is_active = False
    session.update_total_price()
    db.session.commit()
    flash(f'Session stopped. Total: {session.total_price:,.0f} som', 'success')
    return redirect(url_for('sessions'))

@app.route('/sessions/<int:session_id>')
@login_required
def session_detail(session_id):
    session = Session.query.get_or_404(session_id)
    
    # Form for adding products
    form = AddProductToSessionForm()
    form.product_id.choices = [(p.id, f"{p.name} - {p.price:,.0f} som") 
                              for p in Product.query.filter_by(is_active=True).all()]
    form.session_id.data = session_id
    
    return render_template('session_detail.html', session=session, form=form)

@app.route('/sessions/<int:session_id>/add_product', methods=['POST'])
@login_required
def add_product_to_session(session_id):
    session = Session.query.get_or_404(session_id)
    form = AddProductToSessionForm()
    form.product_id.choices = [(p.id, f"{p.name} - {p.price:,.0f} som") 
                              for p in Product.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Check if product already in cart
        existing_item = CartItem.query.filter_by(
            session_id=session_id,
            product_id=form.product_id.data
        ).first()
        
        if existing_item:
            existing_item.quantity += form.quantity.data
        else:
            cart_item = CartItem(
                session_id=session_id,
                product_id=form.product_id.data,
                quantity=form.quantity.data
            )
            db.session.add(cart_item)
        
        session.update_total_price()
        db.session.commit()
        flash('Product added to session!', 'success')
    else:
        flash('Error adding product. Please check your input.', 'danger')
    
    return redirect(url_for('session_detail', session_id=session_id))

@app.route('/sessions/<int:session_id>/remove_product/<int:item_id>')
@login_required
def remove_product_from_session(session_id, item_id):
    session = Session.query.get_or_404(session_id)
    cart_item = CartItem.query.get_or_404(item_id)
    
    db.session.delete(cart_item)
    session.update_total_price()
    db.session.commit()
    flash('Product removed from session!', 'success')
    
    return redirect(url_for('session_detail', session_id=session_id))

@app.route('/analytics')
@login_required
def analytics():
    # Daily analytics
    today = datetime.utcnow().date()
    daily_sessions = Session.query.filter(
        func.date(Session.created_at) == today,
        Session.is_active == False
    ).all()
    daily_revenue = sum(session.total_price for session in daily_sessions)
    
    # Weekly analytics
    week_start = today - timedelta(days=today.weekday())
    weekly_sessions = Session.query.filter(
        Session.created_at >= week_start,
        Session.is_active == False
    ).all()
    weekly_revenue = sum(session.total_price for session in weekly_sessions)
    
    # Monthly analytics
    monthly_sessions = Session.query.filter(
        extract('month', Session.created_at) == today.month,
        extract('year', Session.created_at) == today.year,
        Session.is_active == False
    ).all()
    monthly_revenue = sum(session.total_price for session in monthly_sessions)
    
    # Revenue breakdown
    session_revenue = sum(session.session_price for session in monthly_sessions)
    products_revenue = sum(session.products_total for session in monthly_sessions)
    
    return render_template('analytics.html',
                         daily_revenue=daily_revenue,
                         daily_sessions=len(daily_sessions),
                         weekly_revenue=weekly_revenue,
                         weekly_sessions=len(weekly_sessions),
                         monthly_revenue=monthly_revenue,
                         monthly_sessions=len(monthly_sessions),
                         session_revenue=session_revenue,
                         products_revenue=products_revenue)

@app.route('/api/session_time/<int:session_id>')
@login_required
def get_session_time(session_id):
    session = Session.query.get_or_404(session_id)
    now = datetime.utcnow()
    
    if session.session_type == 'fixed':
        # Calculate remaining time
        end_time = session.start_time + timedelta(minutes=session.duration_minutes)
        remaining = end_time - now
        
        if remaining.total_seconds() <= 0:
            # Session should be auto-stopped
            if session.is_active:
                session.end_time = end_time
                session.is_active = False
                session.update_total_price()
                db.session.commit()
            
            return jsonify({
                'expired': True,
                'remaining_seconds': 0,
                'elapsed_seconds': session.duration_minutes * 60
            })
        
        return jsonify({
            'expired': False,
            'remaining_seconds': int(remaining.total_seconds()),
            'elapsed_seconds': int((now - session.start_time).total_seconds())
        })
    
    else:  # VIP session
        elapsed = now - session.start_time
        return jsonify({
            'expired': False,
            'remaining_seconds': 0,
            'elapsed_seconds': int(elapsed.total_seconds())
        })

@app.route('/register/Muslim', methods=['GET', 'POST'])
def register():
    """Registration route with secret key verification"""
    form = RegisterForm()
    if form.validate_on_submit():
        # Check secret key
        if form.secret_key.data != 'Muslim':
            flash('Noto\'g\'ri maxfiy kalit!', 'danger')
            return render_template('register.html', form=form)
        
        # Check if username already exists
        if AdminUser.query.filter_by(username=form.username.data).first():
            flash('Bu foydalanuvchi nomi allaqachon mavjud!', 'danger')
            return render_template('register.html', form=form)
        
        # Check if email already exists
        if AdminUser.query.filter_by(email=form.email.data).first():
            flash('Bu email allaqachon ro\'yxatga olingan!', 'danger')
            return render_template('register.html', form=form)
        
        # Create new user
        user = AdminUser(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Ro\'yxatdan o\'tish muvaffaqiyatli tugallandi! Endi tizimga kirishingiz mumkin.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

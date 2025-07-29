from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with sessions
    sessions = db.relationship('Session', backref='room', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # drinks, snacks, etc.
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    session_type = db.Column(db.String(20), nullable=False)  # 'fixed' or 'vip'
    duration_minutes = db.Column(db.Integer)  # For fixed sessions
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    session_price = db.Column(db.Float, default=0.0)  # Base session price
    products_total = db.Column(db.Float, default=0.0)  # Total from products
    total_price = db.Column(db.Float, default=0.0)  # session_price + products_total
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with cart items
    cart_items = db.relationship('CartItem', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def calculate_duration_minutes(self):
        """Calculate actual duration for completed sessions"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0
    
    def calculate_vip_price(self, rate_per_minute=500):
        """Calculate VIP session price based on duration"""
        if self.session_type == 'vip' and self.end_time:
            duration = self.calculate_duration_minutes()
            return duration * rate_per_minute
        return self.session_price
    
    def update_total_price(self):
        """Update total price including products"""
        products_total = sum(item.product.price * item.quantity for item in self.cart_items)
        self.products_total = products_total
        
        if self.session_type == 'vip' and self.end_time:
            self.session_price = self.calculate_vip_price()
        
        self.total_price = self.session_price + self.products_total

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='cart_items')

# Fixed session pricing configuration
FIXED_SESSION_PRICES = {
    30: 15000,  # 30 minutes = 15,000 som
    60: 25000,  # 60 minutes = 25,000 som
    90: 35000,  # 90 minutes = 35,000 som
    120: 45000  # 120 minutes = 45,000 som
}

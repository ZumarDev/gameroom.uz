from app import db
from flask_login import UserMixin
from datetime import datetime
import math
from sqlalchemy import func

class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RoomCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price_per_30min = db.Column(db.Float, nullable=False, default=15000)  # Base price for 30 minutes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with rooms
    rooms = db.relationship('Room', backref='category', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('room_category.id'), nullable=False)
    custom_price_per_30min = db.Column(db.Float)  # Optional custom pricing, overrides category default
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with sessions
    sessions = db.relationship('Session', backref='room', lazy=True)
    
    def get_price_per_30min(self):
        """Get the price per 30 minutes for this room"""
        if self.custom_price_per_30min:
            return self.custom_price_per_30min
        else:
            category = RoomCategory.query.get(self.category_id)
            return category.price_per_30min if category else 15000

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # drinks, snacks, etc.
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default='dona')  # Unit of measurement (pieces, liters, etc.)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Stock management removed per user request

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
        """Calculate and update total price based on room pricing and actual duration"""
        # Load room relationship if not already loaded
        if not hasattr(self, '_room') or self._room is None:
            self._room = Room.query.get(self.room_id)
        
        # Get room pricing - use custom price if set, otherwise category price
        if self._room and self._room.custom_price_per_30min:
            price_per_30min = self._room.custom_price_per_30min
        elif self._room and self._room.category:
            price_per_30min = self._room.category.price_per_30min
        else:
            price_per_30min = 15000  # Default fallback
        
        # Calculate session price based on actual time played
        if self.session_type == 'fixed':
            if self.end_time and not self.is_active:
                # Session ended early - calculate actual time played
                actual_duration = self.end_time - self.start_time
                actual_minutes = actual_duration.total_seconds() / 60
            else:
                # Session ongoing or completed - use planned duration
                actual_minutes = self.duration_minutes
            
            # Calculate price based on actual time (round up to nearest 30 min block)
            price_blocks = math.ceil(actual_minutes / 30)
            self.session_price = price_blocks * price_per_30min
            
        else:  # VIP session
            # Calculate based on actual duration
            if self.end_time:
                actual_duration = self.end_time - self.start_time
            else:
                actual_duration = datetime.utcnow() - self.start_time
            
            # Round up to nearest 30 minutes for pricing
            minutes = actual_duration.total_seconds() / 60
            price_blocks = math.ceil(minutes / 30)
            self.session_price = price_blocks * price_per_30min
        
        # Calculate products total
        cart_items = CartItem.query.filter_by(session_id=self.id).all()
        products_total = sum(item.product.price * item.quantity for item in cart_items if item.product)
        self.products_total = products_total
        
        # Update total
        self.total_price = self.session_price + self.products_total

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product')

# Fixed session pricing configuration
FIXED_SESSION_PRICES = {
    30: 15000,  # 30 minutes = 15,000 som
    60: 25000,  # 60 minutes = 25,000 som
    90: 35000,  # 90 minutes = 35,000 som
    120: 45000  # 120 minutes = 45,000 som
}

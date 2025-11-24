from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    address = db.Column(db.Text)

    orders = db.relationship('Order', backref='customer', lazy=True)
    wishlist_items = db.relationship('Wishlist', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(300), nullable=False)
    sku = db.Column(db.String(80), unique=True, nullable=False)
    featured = db.Column(db.Boolean, default=False)

    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def in_stock(self) -> bool:
        return self.stock > 0


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')


class Order(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='processing')
    total = db.Column(db.Float, nullable=False, default=0)
    shipping_address = db.Column(db.Text, nullable=False)
    tracking_code = db.Column(db.String(120), unique=True, nullable=False)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def recalc_total(self) -> None:
        self.total = sum(item.quantity * item.unit_price for item in self.items)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)


class BlogPost(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    headline = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    hero_image = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)


class ContactMessage(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='new')


def generate_tracking_code(prefix: str = 'GG') -> str:
    timestamp = datetime.utcnow().isoformat()
    return f"{prefix}-{sha256(timestamp.encode()).hexdigest()[:10].upper()}"


def sample_upload_path(filename: str) -> str:
    digest = sha256(filename.encode()).hexdigest()[:8]
    return f"uploads/{digest}-{filename}"


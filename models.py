from datetime import datetime
from flask_sqlalchemy import SQLAlchemy  # pyright: ignore[reportMissingImports]
from flask_login import UserMixin  # pyright: ignore[reportMissingImports]
from werkzeug.security import generate_password_hash, check_password_hash  # pyright: ignore[reportMissingImports]

db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    mobile = db.Column(db.String(15), unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    blocked = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), default='customer')  # customer, admin, support
    email_verified = db.Column(db.Boolean, default=False)
    mobile_verified = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    loyalty_points = db.Column(db.Integer, default=0)
    referral_code = db.Column(db.String(20), unique=True, index=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    orders = db.relationship('Order', backref='customer', lazy=True)
    wishlist_items = db.relationship('Wishlist', backref='user', lazy=True, cascade='all, delete-orphan')
    addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy=True)
    recently_viewed = db.relationship('RecentlyViewed', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Address(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(100), default='India')
    is_default = db.Column(db.Boolean, default=False)
    address_type = db.Column(db.String(50), default='home')  # home, work, other


class Product(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    brand = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(120), nullable=False, index=True)
    subcategory = db.Column(db.String(120), index=True)
    description = db.Column(db.Text, nullable=False)
    short_description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False, index=True)
    mrp = db.Column(db.Float)  # Maximum Retail Price
    stock = db.Column(db.Integer, nullable=False, default=0, index=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    image = db.Column(db.String(300))
    featured = db.Column(db.Boolean, default=False, index=True)
    tags = db.Column(db.String(500))  # Comma-separated tags
    weight = db.Column(db.Float)  # in grams
    dimensions = db.Column(db.String(100))  # LxWxH in cm
    rating = db.Column(db.Float, default=0.0, index=True)
    review_count = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    sold_count = db.Column(db.Integer, default=0, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)

    images = db.relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True)
    wishlist_items = db.relationship('Wishlist', backref='product', lazy=True)

    def in_stock(self) -> bool:
        return self.stock > 0

    def update_rating(self):
        reviews = Review.query.filter_by(product_id=self.id, approved=True).all()
        if reviews:
            self.rating = sum(r.rating for r in reviews) / len(reviews)
            self.review_count = len(reviews)
        else:
            self.rating = 0.0
            self.review_count = 0


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # product backref is created by Product.wishlist_items relationship


class RecentlyViewed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product')


class Review(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200))
    comment = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)
    helpful_count = db.Column(db.Integer, default=0)


class Order(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    status = db.Column(db.String(50), default='placed', index=True)  # placed, packed, shipped, delivered, cancelled, returned
    payment_status = db.Column(db.String(50), default='pending', index=True)  # pending, paid, failed, refunded
    payment_method = db.Column(db.String(50), index=True)  # razorpay, stripe, paypal, upi, wallet, cod
    payment_id = db.Column(db.String(200))
    subtotal = db.Column(db.Float, nullable=False, default=0)
    tax = db.Column(db.Float, default=0)
    shipping = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    coupon_code = db.Column(db.String(50), index=True)
    total = db.Column(db.Float, nullable=False, default=0, index=True)
    shipping_address = db.Column(db.Text, nullable=False)
    tracking_code = db.Column(db.String(120), unique=True, index=True)
    shipping_partner = db.Column(db.String(100))
    estimated_delivery = db.Column(db.DateTime, index=True)
    delivered_at = db.Column(db.DateTime, index=True)
    notes = db.Column(db.Text)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def recalc_total(self):
        self.subtotal = sum(item.quantity * item.unit_price for item in self.items)
        self.total = self.subtotal + self.tax + self.shipping - self.discount


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    product_name = db.Column(db.String(200))  # Snapshot of product name at time of order
    product_sku = db.Column(db.String(80))  # Snapshot of SKU


class Coupon(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(500))
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed
    discount_value = db.Column(db.Float, nullable=False)
    min_purchase = db.Column(db.Float, default=0)
    max_discount = db.Column(db.Float)
    usage_limit = db.Column(db.Integer)  # Total usage limit
    used_count = db.Column(db.Integer, default=0)
    user_limit = db.Column(db.Integer, default=1)  # Per user limit
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)


class BlogPost(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    headline = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    hero_image = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120))
    is_published = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    meta_description = db.Column(db.String(300))
    meta_keywords = db.Column(db.String(500))


class ContactMessage(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(15))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='new')  # new, read, replied, closed
    replied_at = db.Column(db.DateTime)
    reply_message = db.Column(db.Text)


class AdminLog(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(50))  # product, order, user, etc.
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(300))
    admin = db.relationship('User')


class Banner(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    image = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(300))
    position = db.Column(db.String(50), default='home')  # home, products, checkout
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)


class Category(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image = db.Column(db.String(300))
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    parent = db.relationship('Category', remote_side=[id], backref='children')

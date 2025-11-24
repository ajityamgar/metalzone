import os
import secrets
import string
import random
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import quote
import tempfile

from flask import (  # pyright: ignore[reportMissingImports]
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory,
    make_response,
)
from flask_login import (  # pyright: ignore[reportMissingImports]
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import CSRFProtect  # pyright: ignore[reportMissingImports]
from flask_wtf.csrf import generate_csrf  # pyright: ignore[reportMissingImports]
from sqlalchemy import func, or_, and_  # pyright: ignore[reportMissingImports]
from sqlalchemy.exc import IntegrityError # type: ignore
from werkzeug.utils import secure_filename  # pyright: ignore[reportMissingImports]
from werkzeug.security import generate_password_hash  # pyright: ignore[reportMissingImports]

from forms import (
    AddressForm,
    BlogForm,
    CheckoutForm,
    ContactForm,
    CouponForm,
    LoginForm,
    ProductForm,
    ProfileForm,
    RegisterForm,
    ReviewForm,
    SearchForm,
)
from models import (
    Address,
    AdminLog,
    Banner,
    BlogPost,
    Category,
    ContactMessage,
    Coupon,
    Order,
    OrderItem,
    Product,
    ProductImage,
    RecentlyViewed,
    Review,
    User,
    Wishlist,
    db,
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Use an instance directory for writable runtime files (database, uploads)
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Database path (absolute) placed in instance/ for runtime writeability
DB_PATH = os.path.join(INSTANCE_DIR, 'database.db')

# Upload folder (writable). Prefer env var, otherwise use system temp dir under 'glidemans_uploads'
DEFAULT_UPLOAD_DIR = os.environ.get('UPLOAD_FOLDER') or os.path.join(tempfile.gettempdir(), 'glidemans_uploads')
UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, 'uploads') if os.access(INSTANCE_DIR, os.W_OK) else DEFAULT_UPLOAD_DIR
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

app = Flask('MetalZone')
# Security: secret key must come from environment in production
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(24)),
    SQLALCHEMY_DATABASE_URI=f'sqlite:///{DB_PATH}',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    ENV=os.environ.get('FLASK_ENV', 'production'),
    DEBUG=False,
)

# Allow overriding database with a managed database URL (e.g. Postgres on Render)
# If `DATABASE_URL` is set in the environment, use it; otherwise fall back to the
# absolute sqlite path in the instance directory.
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # SQLAlchemy expects a database URL; Render provides DATABASE_URL for Postgres
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Rate Limiting
try:
    from flask_limiter import Limiter  # pyright: ignore[reportMissingImports]
    from flask_limiter.util import get_remote_address  # pyright: ignore[reportMissingImports]
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
except ImportError:
    limiter = None

# Helper decorator for rate limiting that handles None limiter
def rate_limit(limit_str):
    if limiter:
        return limiter.limit(limit_str)
    else:
        # If limiter is not available, return a no-op decorator
        def decorator(f):
            return f
        return decorator


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_storage):
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        flash('Unsupported image format. Please use PNG, JPG, JPEG, or WEBP.', 'warning')
        return None
    filename = secure_filename(file_storage.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f"{timestamp}_{filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        file_storage.save(path)
    except Exception:
        app.logger.exception('Failed to save uploaded image')
        return None
    # Return a URL served by our `/uploads/<filename>` endpoint
    try:
        return url_for('uploaded_file', filename=filename)
    except Exception:
        # Fallback to a relative path
        return '/uploads/' + filename


def generate_order_number():
    return f"MZ{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def generate_tracking_code():
    return f"MZ-{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}"


def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def log_admin_action(action, resource_type=None, resource_id=None):
    # Add an admin log entry to the current session without committing.
    # Committing inside this helper caused premature flush/commit of other
    # objects in the session (e.g. Product) and raised IntegrityError before
    # the calling code could handle it. Defer commit to the caller.
    if current_user.is_authenticated and current_user.is_admin:
        log = AdminLog(
            admin_id=current_user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(log)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_globals():
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    brands = [b[0] for b in db.session.query(Product.brand).distinct().all() if b[0]]
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.order).all()
    
    return {
        'cart_count': cart_count,
        'csrf_token': generate_csrf,
        'current_year': datetime.utcnow().year,
        'categories': categories,
        'brands': brands,
        'banners': banners,
        'logged_in_user': current_user if current_user.is_authenticated else None,
    }


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def flash_form_errors(form):
    """Flash WTForms validation errors so the admin sees why a form failed."""
    for field, errors in getattr(form, 'errors', {}).items():
        for error in errors:
            try:
                label = getattr(form, field).label.text
            except Exception:
                label = field
            flash(f"{label}: {error}", 'danger')


def cart_items():
    items = []
    cart = session.get('cart', {})
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product and product.is_active and product.stock > 0:
            qty = min(qty, product.stock)  # Don't allow more than available
            items.append({
                'product': product,
                'quantity': qty,
                'subtotal': qty * product.price
            })
    subtotal = sum(item['subtotal'] for item in items)
    tax = round(subtotal * 0.18, 2)  # 18% GST
    shipping = 0 if subtotal >= 500 else 50  # Free shipping above ₹500
    discount = 0
    coupon_code = session.get('coupon_code')
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if coupon and coupon.valid_from <= datetime.utcnow() <= coupon.valid_until:
            if coupon.discount_type == 'percentage':
                discount = min(subtotal * coupon.discount_value / 100, coupon.max_discount or subtotal)
            else:
                discount = min(coupon.discount_value, subtotal)
    grand_total = subtotal + tax + shipping - discount
    return items, subtotal, tax, shipping, discount, grand_total


@app.template_filter('fix_image')
def fix_image(path):
    """Normalize stored image values to valid URLs for templates.

    Rules:
    - None or empty -> return a small inline SVG placeholder data URI
    - Starts with http:// or https:// -> return as-is
    - Starts with '/static/' -> return as-is
    - Starts with 'static/' -> prepend '/'
    - Looks like a bare filename (no '/') -> assume it's in 'static/uploads/'
    - Otherwise, ensure it starts with '/'
    """
    placeholder = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300'>" \
                  "<rect width='100%' height='100%' fill='%23f3f3f3'/><text x='50%' y='50%' " \
                  "dominant-baseline='middle' text-anchor='middle' fill='%23888' font-size='20'>No Image</text></svg>"
    if not path:
        return placeholder
    p = str(path).strip()
    if not p:
        return placeholder
    if p.startswith('http://') or p.startswith('https://'):
        return p
    if p.startswith('/static/'):
        return p
    if p.startswith('static/'):
        return '/' + p
    if '/' not in p:
        # bare filename -> assume uploads
        try:
            return url_for('static', filename=f'uploads/{p}')
        except Exception:
            return '/uploads/' + p
    # generic fallback: ensure leading slash
    return p if p.startswith('/') else '/' + p


@app.template_filter('rupee')
def rupee(value):
    try:
        return f"₹{float(value):,.2f}"
    except:
        return f"₹{value}"


@app.template_filter('int_rupee')
def int_rupee(value):
    try:
        return f"₹{int(float(value)):,}"
    except:
        return f"₹{value}"


# Error Handlers
@app.errorhandler(404)
def not_found(_):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(_):
    return render_template('errors/500.html'), 500


# Home & Public Pages
@app.route('/')
def home():
    featured = Product.query.filter_by(featured=True, is_active=True).limit(8).all()
    trending = Product.query.filter_by(is_active=True).order_by(Product.sold_count.desc()).limit(6).all()
    blogs = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    return render_template('home.html', featured=featured, trending=trending, blogs=blogs)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            mobile=form.mobile.data,
            subject=form.subject.data,
            message=form.message.data
        )
        db.session.add(message)
        db.session.commit()
        flash('Your message has been sent successfully! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html', form=form)


# Products
@app.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    brand = request.args.get('brand', '')
    search = request.args.get('search', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort = request.args.get('sort', 'latest')
    
    query = Product.query.filter_by(is_active=True)
    
    if category:
        query = query.filter_by(category=category)
    if brand:
        query = query.filter_by(brand=brand)
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%'),
                Product.brand.ilike(f'%{search}%'),
                Product.tags.ilike(f'%{search}%')
            )
        )
    if min_price is not None and min_price >= 0:
        query = query.filter(Product.price >= min_price)
    if max_price is not None and max_price > 0:
        if min_price is not None and max_price < min_price:
            flash('Maximum price must be greater than minimum price.', 'warning')
        else:
            query = query.filter(Product.price <= max_price)
    
    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'rating':
        query = query.order_by(Product.rating.desc())
    elif sort == 'popular':
        query = query.order_by(Product.sold_count.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    
    filters = {
        'category': category,
        'brand': brand,
        'search': search,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort
    }
    
    return render_template('products.html', pagination=pagination, filters=filters)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_active and not (current_user.is_authenticated and current_user.is_admin):
        flash('Product not found.', 'danger')
        return redirect(url_for('products'))
    
    # Track view
    product.views += 1
    db.session.commit()
    
    # Track recently viewed for logged-in users
    if current_user.is_authenticated:
        existing = RecentlyViewed.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        if existing:
            existing.viewed_at = datetime.utcnow()
        else:
            db.session.add(RecentlyViewed(user_id=current_user.id, product_id=product_id))
        db.session.commit()
    
    images = product.images or []
    if not images and product.image:
        images = [{'url': product.image}]
    
    related = Product.query.filter(
        and_(
            Product.category == product.category,
            Product.id != product.id,
            Product.is_active == True
        )
    ).limit(4).all()
    
    reviews = Review.query.filter_by(product_id=product_id, approved=True).order_by(Review.created_at.desc()).limit(10).all()
    
    wished = False
    if current_user.is_authenticated:
        wished = Wishlist.query.filter_by(user_id=current_user.id, product_id=product.id).first() is not None
    
    return render_template('product_detail.html', product=product, related=related, images=images, reviews=reviews, wished=wished)


# Search
@app.route('/search')
def search():
    term = request.args.get('q', '')
    if not term:
        return jsonify([])
    
    results = Product.query.filter(
        and_(
            Product.is_active == True,
            or_(
                Product.name.ilike(f'%{term}%'),
                Product.description.ilike(f'%{term}%'),
                Product.brand.ilike(f'%{term}%')
            )
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': p.price,
        'image': p.image,
        'url': url_for('product_detail', product_id=p.id)
    } for p in results])


# Cart
@app.route('/cart')
def cart():
    items, subtotal, tax, shipping, discount, total = cart_items()
    coupon_code = session.get('coupon_code', '')
    return render_template('cart.html', items=items, subtotal=subtotal, tax=tax, shipping=shipping, discount=discount, total=total, coupon_code=coupon_code)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_active or product.stock <= 0:
        flash('Product is not available.', 'warning')
        return redirect(request.referrer or url_for('products'))
    
    qty = max(1, int(request.form.get('quantity', 1)))
    cart = session.get('cart', {})
    current_qty = cart.get(str(product_id), 0)
    new_qty = current_qty + qty
    
    if new_qty > product.stock:
        flash(f'Only {product.stock} items available in stock.', 'warning')
        new_qty = product.stock
    
    cart[str(product_id)] = new_qty
    session['cart'] = cart
    flash(f'{product.name} added to cart!', 'success')
    return redirect(request.referrer or url_for('products'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    cart = {}
    for key, value in request.form.items():
        if key.startswith('qty_'):
            pid = key.replace('qty_', '')
            qty = max(1, int(value))
            product = Product.query.get(int(pid))
            if product and product.is_active:
                qty = min(qty, product.stock)
                cart[pid] = qty
    session['cart'] = cart
    flash('Cart updated successfully.', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def cart_remove(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))


@app.route('/cart/coupon', methods=['POST'])
def cart_coupon():
    code = request.form.get('coupon_code', '').strip().upper()
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    
    if not coupon:
        flash('Invalid coupon code.', 'danger')
        return redirect(url_for('cart'))
    
    if coupon.valid_from > datetime.utcnow() or coupon.valid_until < datetime.utcnow():
        flash('Coupon has expired.', 'danger')
        return redirect(url_for('cart'))
    
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        flash('Coupon usage limit reached.', 'danger')
        return redirect(url_for('cart'))
    
    items, subtotal, _, _, _, _ = cart_items()
    if subtotal < coupon.min_purchase:
        flash(f'Minimum purchase of ₹{coupon.min_purchase:,.2f} required for this coupon.', 'warning')
        return redirect(url_for('cart'))
    
    session['coupon_code'] = code
    flash('Coupon applied successfully!', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/coupon/remove', methods=['POST'])
def cart_coupon_remove():
    session.pop('coupon_code', None)
    flash('Coupon removed.', 'info')
    return redirect(url_for('cart'))


# Wishlist
@app.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    return render_template('wishlist.html', items=items)


@app.route('/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def wishlist_add(product_id):
    if not Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first():
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        flash('Added to wishlist!', 'success')
    else:
        flash('Already in wishlist.', 'info')
    return redirect(request.referrer or url_for('product_detail', product_id=product_id))


@app.route('/wishlist/remove/<int:product_id>', methods=['POST'])
@login_required
def wishlist_remove(product_id):
    Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
    db.session.commit()
    flash('Removed from wishlist.', 'info')
    return redirect(request.referrer or url_for('wishlist'))


# Checkout & Orders
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items, subtotal, tax, shipping, discount, total = cart_items()
    if not items:
        flash('Your cart is empty. Add items before checkout.', 'warning')
        return redirect(url_for('products'))
    
    form = CheckoutForm()
    addresses = Address.query.filter_by(user_id=current_user.id).order_by(Address.is_default.desc()).all()
    form.address_id.choices = [(0, 'Add New Address')] + [(a.id, f"{a.name}, {a.city}") for a in addresses]
    
    if form.validate_on_submit():
        # Get or create address
        address_id = form.address_id.data
        if address_id and address_id > 0:
            address = Address.query.get(address_id)
            if address and address.user_id == current_user.id:
                shipping_address = f"{address.name}, {address.mobile}\n{address.address_line1}"
                if address.address_line2:
                    shipping_address += f"\n{address.address_line2}"
                shipping_address += f"\n{address.city}, {address.state} {address.pincode}\n{address.country}"
            else:
                flash('Invalid address selected.', 'danger')
                return redirect(url_for('checkout'))
        else:
            # Use default address or create from profile
            if current_user.addresses:
                address = next((a for a in current_user.addresses if a.is_default), current_user.addresses[0])
                shipping_address = f"{address.name}, {address.mobile}\n{address.address_line1}"
                if address.address_line2:
                    shipping_address += f"\n{address.address_line2}"
                shipping_address += f"\n{address.city}, {address.state} {address.pincode}\n{address.country}"
            else:
                # No addresses saved - require user to add one
                flash('Please add a shipping address before checkout. You will be redirected to add an address.', 'warning')
                return redirect(url_for('addresses'))
        
        # Create order
        order = Order(
            user_id=current_user.id,
            order_number=generate_order_number(),
            shipping_address=shipping_address,
            payment_method=form.payment_method.data,
            payment_status='pending' if form.payment_method.data == 'cod' else 'pending',
            status='placed',
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            discount=discount,
            coupon_code=session.get('coupon_code'),
            total=total,
            tracking_code=generate_tracking_code(),
            estimated_delivery=datetime.utcnow() + timedelta(days=5),
            notes=form.notes.data
        )
        db.session.add(order)
        db.session.flush()
        
        # Add order items and update stock
        for item in items:
            product = item['product']
            product.stock = max(0, product.stock - item['quantity'])
            product.sold_count += item['quantity']
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item['quantity'],
                unit_price=product.price,
                product_name=product.name,
                product_sku=product.sku
            ))
        
        # Update coupon usage
        coupon_code = session.get('coupon_code')
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code).first()
            if coupon:
                coupon.used_count += 1
        
        db.session.commit()
        session['cart'] = {}
        session.pop('coupon_code', None)
        
        flash(f'Order placed successfully! Order Number: {order.order_number}', 'success')
        return redirect(url_for('order_detail', order_id=order.id))
    
    return render_template('checkout.html', form=form, items=items, subtotal=subtotal, tax=tax, shipping=shipping, discount=discount, total=total, addresses=addresses)


@app.route('/orders')
@login_required
def orders():
    orders_list = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders_list)


@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to view this order.', 'danger')
        return redirect(url_for('orders'))
    return render_template('order_detail.html', order=order)


@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def order_cancel(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to cancel this order.', 'danger')
        return redirect(url_for('orders'))
    
    if order.status not in ['placed', 'packed']:
        flash('This order cannot be cancelled.', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    order.status = 'cancelled'
    order.payment_status = 'refunded' if order.payment_status == 'paid' else 'cancelled'
    
    # Restore stock
    for item in order.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity
    
    db.session.commit()
    flash('Order cancelled successfully.', 'success')
    return redirect(url_for('order_detail', order_id=order_id))


# Profile & Account
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(10).all()
    wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
    recently_viewed = RecentlyViewed.query.filter_by(user_id=current_user.id).order_by(RecentlyViewed.viewed_at.desc()).limit(10).all()
    
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        if form.mobile.data:
            current_user.mobile = form.mobile.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form, orders=orders, wishlist_count=wishlist_count, recently_viewed=recently_viewed)


@app.route('/profile/addresses', methods=['GET', 'POST'])
@login_required
def addresses():
    form = AddressForm()
    addresses_list = Address.query.filter_by(user_id=current_user.id).order_by(Address.is_default.desc()).all()
    
    if form.validate_on_submit():
        address_id = form.address_id.data
        if address_id:
            address = Address.query.get(address_id)
            if address and address.user_id == current_user.id:
                form.populate_obj(address)
            else:
                flash('Invalid address.', 'danger')
                return redirect(url_for('addresses'))
        else:
            address = Address(user_id=current_user.id)
            form.populate_obj(address)
            db.session.add(address)
        
        # Set as default if requested
        if form.is_default.data:
            Address.query.filter_by(user_id=current_user.id).update({'is_default': False})
            address.is_default = True
        
        db.session.commit()
        flash('Address saved successfully!', 'success')
        return redirect(url_for('addresses'))
    
    return render_template('addresses.html', form=form, addresses=addresses_list)


@app.route('/profile/addresses/<int:address_id>/delete', methods=['POST'])
@login_required
def address_delete(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('addresses'))
    db.session.delete(address)
    db.session.commit()
    flash('Address deleted.', 'info')
    return redirect(url_for('addresses'))


# Reviews
@app.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    product = Product.query.get_or_404(product_id)
    form = ReviewForm()
    
    if form.validate_on_submit():
        # Check if user already reviewed
        existing = Review.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if existing:
            flash('You have already reviewed this product.', 'warning')
            return redirect(url_for('product_detail', product_id=product_id))
        
        review = Review(
            user_id=current_user.id,
            product_id=product_id,
            rating=form.rating.data,
            title=form.title.data,
            comment=form.comment.data,
            approved=False  # Admin approval required
        )
        db.session.add(review)
        db.session.commit()
        
        product.update_rating()
        db.session.commit()
        
        flash('Review submitted! It will be published after admin approval.', 'success')
    
    return redirect(url_for('product_detail', product_id=product_id))


# Authentication
@app.route('/login', methods=['GET', 'POST'])
@rate_limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard' if current_user.is_admin else 'home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.email.data.lower().strip()
        user = User.query.filter(
            or_(User.email == identifier, User.mobile == identifier)
        ).first()
        
        if user and user.check_password(form.password.data):
            if user.blocked:
                flash('Your account has been blocked. Please contact support.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or (url_for('admin_dashboard') if user.is_admin else url_for('home')))
        
        flash('Invalid email/mobile or password.', 'danger')
    
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
@rate_limit("3 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Email already registered. Please login instead.', 'warning')
            return redirect(url_for('login'))
        
        if form.mobile.data and User.query.filter_by(mobile=form.mobile.data).first():
            flash('Mobile number already registered.', 'warning')
            return redirect(url_for('register'))
        
        user = User(
            name=form.name.data,
            email=form.email.data.lower(),
            mobile=form.mobile.data if form.mobile.data else None
        )
        user.set_password(form.password.data)
        user.referral_code = generate_referral_code()
        
        # Handle referral
        if form.referral_code.data:
            referrer = User.query.filter_by(referral_code=form.referral_code.data.upper()).first()
            if referrer:
                user.referred_by = referrer.id
                referrer.loyalty_points += 100
                user.loyalty_points += 50
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Account created successfully! Welcome to Metal Zone!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('cart', None)
    session.pop('coupon_code', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))


# Blog
@app.route('/blog')
def blog_listing():
    page = request.args.get('page', 1, type=int)
    pagination = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=9, error_out=False)
    return render_template('blog_listing.html', pagination=pagination)


@app.route('/blog/<slug>')
def blog_detail(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    post.views += 1
    db.session.commit()
    return render_template('blog_detail.html', post=post)


# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = {
        'products': Product.query.count(),
        'active_products': Product.query.filter_by(is_active=True).count(),
        'users': User.query.count(),
        'orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='placed').count(),
        'total_sales': db.session.query(func.sum(Order.total)).filter_by(payment_status='paid').scalar() or 0,
        'today_sales': db.session.query(func.sum(Order.total)).filter(
            and_(
                func.date(Order.created_at) == datetime.utcnow().date(),
                Order.payment_status == 'paid'
            )
        ).scalar() or 0,
        'low_stock': Product.query.filter(Product.stock < 10, Product.is_active == True).count(),
    }
    
    monthly_sales = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.sum(Order.total).label('total')
    ).filter(Order.payment_status == 'paid').group_by('month').order_by('month').limit(12).all()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    low_stock_products = Product.query.filter(Product.stock < 10, Product.is_active == True).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, monthly_sales=monthly_sales, recent_orders=recent_orders, low_stock_products=low_stock_products)


@app.route('/admin/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    form = ProductForm()
    if form.validate_on_submit():
        product_id = form.product_id.data

        # Early SKU uniqueness check (attach error to field instead of redirect)
        sku_val = (form.sku.data or '').strip()
        if sku_val:
            existing_sku = Product.query.filter_by(sku=sku_val).first()
            if existing_sku and (not product_id or int(product_id) != existing_sku.id):
                form.sku.errors.append(f"SKU '{sku_val}' is already in use by another product.")

        # If any validation errors are present, re-render the page showing them
        if form.errors:
            # Do not proceed to save; the template will display `form.errors`
            pass
        else:
            if product_id:
                try:
                    pid = int(product_id)
                except Exception:
                    form.product_id.errors.append('Invalid product id.')
                    pid = None

                if pid:
                    product = Product.query.get(pid)
                    if not product:
                        form.product_id.errors.append('Product not found.')
                    else:
                        form.populate_obj(product)
                        log_admin_action(f'Updated product: {product.name}', 'product', product.id)
            else:
                product = Product()
                form.populate_obj(product)
                db.session.add(product)
                log_admin_action(f'Created product: {product.name}', 'product', None)

            # If populate_obj didn't add any form-level errors, commit the change
            if not form.errors:
                try:
                    db.session.commit()
                    flash('Product saved successfully!', 'success')
                    return redirect(url_for('admin_products'))
                except IntegrityError:
                    db.session.rollback()
                    flash('Database error while saving product. Possible duplicate SKU or constraint error.', 'danger')
                    app.logger.exception('IntegrityError saving product')
    else:
        # If the form was posted but didn't validate, surface errors
        if request.method == 'POST':
            flash_form_errors(form)
    
    page = request.args.get('page', 1, type=int)
    pagination = Product.query.order_by(Product.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/products.html', form=form, pagination=pagination)


@app.route('/admin/products/<int:product_id>/edit', methods=['GET'])
@admin_required
def admin_product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    form.product_id.data = product_id
    page = request.args.get('page', 1, type=int)
    pagination = Product.query.order_by(Product.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/products.html', form=form, pagination=pagination, editing=product)


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    log_admin_action(f'Deleted product: {name}', 'product', product_id)
    flash('Product deleted successfully.', 'info')
    return redirect(url_for('admin_products'))


@app.route('/admin/orders', methods=['GET', 'POST'])
@admin_required
def admin_orders():
    if request.method == 'POST':
        order = Order.query.get_or_404(int(request.form['order_id']))
        old_status = order.status
        order.status = request.form['status']
        
        if request.form['status'] == 'shipped' and not order.tracking_code:
            order.tracking_code = generate_tracking_code()
        
        if request.form['status'] == 'delivered':
            order.delivered_at = datetime.utcnow()
            order.payment_status = 'paid'
        
        db.session.commit()
        log_admin_action(f'Updated order {order.order_number} status: {old_status} → {order.status}', 'order', order.id)
        flash('Order updated successfully!', 'success')
        return redirect(url_for('admin_orders'))
    
    status_filter = request.args.get('status', '')
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)


@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    if request.method == 'POST':
        action = request.form['action']
        user = User.query.get_or_404(int(request.form['user_id']))
        
        if action == 'toggle_admin':
            user.is_admin = not user.is_admin
            log_admin_action(f'{"Granted" if user.is_admin else "Revoked"} admin access for {user.email}', 'user', user.id)
        elif action == 'toggle_block':
            user.blocked = not user.blocked
            log_admin_action(f'{"Blocked" if user.blocked else "Unblocked"} user {user.email}', 'user', user.id)
        elif action == 'delete' and user.email != 'admin@metalzone.com':
            name = user.email
            db.session.delete(user)
            log_admin_action(f'Deleted user: {name}', 'user', user.id)
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    status_filter = request.args.get('status', 'all')
    query = Review.query
    if status_filter == 'pending':
        query = query.filter_by(approved=False)
    elif status_filter == 'approved':
        query = query.filter_by(approved=True)
    
    reviews = query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews, status_filter=status_filter)


@app.route('/admin/reviews/<int:review_id>/approve', methods=['POST'])
@admin_required
def admin_review_approve(review_id):
    review = Review.query.get_or_404(review_id)
    review.approved = True
    db.session.commit()
    review.product.update_rating()
    db.session.commit()
    log_admin_action(f'Approved review for product {review.product.name}', 'review', review_id)
    flash('Review approved!', 'success')
    return redirect(url_for('admin_reviews'))


@app.route('/admin/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def admin_review_delete(review_id):
    review = Review.query.get_or_404(review_id)
    product = review.product
    db.session.delete(review)
    db.session.commit()
    product.update_rating()
    db.session.commit()
    log_admin_action(f'Deleted review for product {product.name}', 'review', review_id)
    flash('Review deleted.', 'info')
    return redirect(url_for('admin_reviews'))


@app.route('/admin/blog', methods=['GET', 'POST'])
@admin_required
def admin_blog():
    form = BlogForm()
    if form.validate_on_submit():
        post_id = form.post_id.data
        if post_id:
            post = BlogPost.query.get(post_id)
            if not post:
                flash('Post not found.', 'danger')
                return redirect(url_for('admin_blog'))
            form.populate_obj(post)
            log_admin_action(f'Updated blog: {post.title}', 'blog', post.id)
        else:
            post = BlogPost()
            form.populate_obj(post)
            db.session.add(post)
            log_admin_action(f'Created blog: {post.title}', 'blog', None)

        try:
            db.session.commit()
            flash('Blog post saved successfully!', 'success')
            return redirect(url_for('admin_blog'))
        except IntegrityError:
            db.session.rollback()
            flash('Database error while saving blog post. Possible duplicate slug or constraint error.', 'danger')
            app.logger.exception('IntegrityError saving blog post')
    else:
        if request.method == 'POST':
            flash_form_errors(form)
    
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', form=form, posts=posts)


@app.route('/admin/blog/<int:post_id>/edit')
@admin_required
def admin_blog_edit(post_id):
    post = BlogPost.query.get_or_404(post_id)
    form = BlogForm(obj=post)
    form.post_id.data = post_id
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', form=form, posts=posts, editing=post)


@app.route('/admin/blog/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_blog_delete(post_id):
    post = BlogPost.query.get_or_404(post_id)
    title = post.title
    db.session.delete(post)
    db.session.commit()
    log_admin_action(f'Deleted blog: {title}', 'blog', post_id)
    flash('Blog post deleted.', 'info')
    return redirect(url_for('admin_blog'))


@app.route('/admin/coupons', methods=['GET', 'POST'])
@admin_required
def admin_coupons():
    form = CouponForm()
    if form.validate_on_submit():
        coupon_id = form.coupon_id.data
        if coupon_id:
            coupon = Coupon.query.get(coupon_id)
            if not coupon:
                flash('Coupon not found.', 'danger')
                return redirect(url_for('admin_coupons'))
            form.populate_obj(coupon)
            log_admin_action(f'Updated coupon: {coupon.code}', 'coupon', coupon.id)
        else:
            coupon = Coupon()
            form.populate_obj(coupon)
            db.session.add(coupon)
            log_admin_action(f'Created coupon: {coupon.code}', 'coupon', None)

        try:
            db.session.commit()
            flash('Coupon saved successfully!', 'success')
            return redirect(url_for('admin_coupons'))
        except IntegrityError:
            db.session.rollback()
            flash('Database error while saving coupon. Possible duplicate code or constraint error.', 'danger')
            app.logger.exception('IntegrityError saving coupon')
    else:
        if request.method == 'POST':
            flash_form_errors(form)
    
    coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons.html', form=form, coupons=coupons)


@app.route('/admin/coupons/<int:coupon_id>/delete', methods=['POST'])
@admin_required
def admin_coupon_delete(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    code = coupon.code
    db.session.delete(coupon)
    db.session.commit()
    log_admin_action(f'Deleted coupon: {code}', 'coupon', coupon_id)
    flash('Coupon deleted.', 'info')
    return redirect(url_for('admin_coupons'))


@app.route('/admin/messages')
@admin_required
def admin_messages():
    status_filter = request.args.get('status', 'all')
    query = ContactMessage.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    messages = query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages, status_filter=status_filter)


@app.route('/admin/messages/<int:message_id>/update', methods=['POST'])
@admin_required
def admin_message_update(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    message.status = request.form.get('status', 'read')
    if message.status == 'replied':
        message.replied_at = datetime.utcnow()
        message.reply_message = request.form.get('reply_message', '')
    db.session.commit()
    log_admin_action(f'Updated message status: {message.status}', 'message', message_id)
    flash('Message updated!', 'success')
    return redirect(url_for('admin_messages'))


@app.route('/admin/reports')
@admin_required
def admin_reports():
    period = request.args.get('period', 'month')  # day, week, month, year
    start_date = datetime.utcnow()
    
    if period == 'day':
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0)
    elif period == 'week':
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)
    elif period == 'year':
        start_date = datetime.utcnow() - timedelta(days=365)
    
    orders = Order.query.filter(Order.created_at >= start_date, Order.payment_status == 'paid').all()
    
    stats = {
        'total_orders': len(orders),
        'total_revenue': sum(o.total for o in orders),
        'total_items_sold': sum(sum(item.quantity for item in o.items) for o in orders),
        'average_order_value': sum(o.total for o in orders) / len(orders) if orders else 0,
    }
    
    # Top products
    product_sales = {}
    for order in orders:
        for item in order.items:
            if item.product_id not in product_sales:
                product_sales[item.product_id] = {'name': item.product_name, 'quantity': 0, 'revenue': 0}
            product_sales[item.product_id]['quantity'] += item.quantity
            product_sales[item.product_id]['revenue'] += item.quantity * item.unit_price
    
    top_products = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)[:10]
    
    return render_template('admin/reports.html', stats=stats, top_products=top_products, period=period)


# Static files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Serve uploaded files from the runtime upload folder
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Invoice Generation
@app.route('/orders/<int:order_id>/invoice')
@login_required
def order_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to view this invoice.', 'danger')
        return redirect(url_for('orders'))
    return render_template('invoice.html', order=order)


# SEO: Sitemap
@app.route('/sitemap.xml')
def sitemap():
    from xml.etree.ElementTree import Element, SubElement, tostring
    
    urlset = Element('urlset')
    urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    
    base_url = request.url_root.rstrip('/')
    
    # Homepage
    url = SubElement(urlset, 'url')
    SubElement(url, 'loc').text = base_url
    SubElement(url, 'changefreq').text = 'daily'
    SubElement(url, 'priority').text = '1.0'
    
    # Products
    products = Product.query.filter_by(is_active=True).all()
    for product in products:
        url = SubElement(urlset, 'url')
        SubElement(url, 'loc').text = base_url + url_for('product_detail', product_id=product.id)
        SubElement(url, 'changefreq').text = 'weekly'
        SubElement(url, 'priority').text = '0.8'
    
    # Blog posts
    posts = BlogPost.query.filter_by(is_published=True).all()
    for post in posts:
        url = SubElement(urlset, 'url')
        SubElement(url, 'loc').text = base_url + url_for('blog_detail', slug=post.slug)
        SubElement(url, 'changefreq').text = 'monthly'
        SubElement(url, 'priority').text = '0.6'
    
    # Products page
    url = SubElement(urlset, 'url')
    SubElement(url, 'loc').text = base_url + url_for('products')
    SubElement(url, 'changefreq').text = 'daily'
    SubElement(url, 'priority').text = '0.9'
    
    # Blog listing
    url = SubElement(urlset, 'url')
    SubElement(url, 'loc').text = base_url + url_for('blog_listing')
    SubElement(url, 'changefreq').text = 'weekly'
    SubElement(url, 'priority').text = '0.7'
    
    response = make_response(tostring(urlset, encoding='utf-8'))
    response.headers['Content-Type'] = 'application/xml'
    return response


# SEO: Robots.txt
@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')


# Admin: Image Upload
@app.route('/admin/products/upload', methods=['POST'])
@admin_required
def admin_product_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        image_url = save_image(file)
        if image_url:
            log_admin_action(f'Uploaded product image: {file.filename}', 'product', None)
            return jsonify({'url': image_url}), 200
    
    return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WEBP, GIF'}), 400


# Payment Gateway Callbacks (Structure - to be implemented with actual gateways)
@app.route('/payment/razorpay/callback', methods=['POST'])
@login_required
def razorpay_callback():
    """Razorpay payment callback - to be implemented with Razorpay SDK"""
    # TODO: Implement Razorpay webhook verification
    data = request.get_json()
    order_id = data.get('order_id')
    payment_id = data.get('payment_id')
    status = data.get('status')
    
    if status == 'success':
        order = Order.query.filter_by(order_number=order_id).first()
        if order:
            order.payment_status = 'paid'
            order.payment_id = payment_id
            db.session.commit()
            return jsonify({'status': 'success'}), 200
    
    return jsonify({'status': 'failed'}), 400


@app.route('/payment/stripe/callback', methods=['POST'])
@login_required
def stripe_callback():
    """Stripe payment callback - to be implemented with Stripe SDK"""
    # TODO: Implement Stripe webhook verification
    pass


@app.route('/payment/paypal/callback', methods=['POST', 'GET'])
@login_required
def paypal_callback():
    """PayPal payment callback - to be implemented with PayPal SDK"""
    # TODO: Implement PayPal IPN verification
    pass

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Development server: debug disabled by default. Use Gunicorn in production (Render).
    app.logger.info(f'Database path: {DB_PATH}')
    app.logger.info(f'Uploads path: {app.config.get("UPLOAD_FOLDER")}')
    app.run(debug=False, host='0.0.0.0', port=5000)

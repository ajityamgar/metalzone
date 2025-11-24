from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    BooleanField,
    DecimalField,
    IntegerField,
    SelectField,
    HiddenField,
    DateTimeField,
    DateField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, URL, ValidationError
from datetime import datetime


class LoginForm(FlaskForm):
    email = StringField('Email or Mobile', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mobile = StringField('Mobile Number', validators=[Optional(), Length(max=15)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long'),
    ])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    referral_code = StringField('Referral Code (Optional)', validators=[Optional()])
    submit = SubmitField('Create Account')
    
    def validate_password(self, field):
        password = field.data
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in password):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in password):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in password):
            raise ValidationError('Password must contain at least one number')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mobile = StringField('Mobile Number', validators=[Optional(), Length(max=15)])
    submit = SubmitField('Save Profile')


class AddressForm(FlaskForm):
    address_id = HiddenField()
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    mobile = StringField('Mobile Number', validators=[DataRequired(), Length(max=15)])
    address_line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=200)])
    address_line2 = StringField('Address Line 2 (Optional)', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    state = StringField('State', validators=[DataRequired(), Length(max=100)])
    pincode = StringField('Pincode', validators=[DataRequired(), Length(min=6, max=10)])
    country = StringField('Country', default='India')
    address_type = SelectField('Address Type', choices=[
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other')
    ], default='home')
    is_default = BooleanField('Set as default address')
    submit = SubmitField('Save Address')


class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mobile = StringField('Mobile Number', validators=[Optional(), Length(max=15)])
    subject = StringField('Subject', validators=[Optional(), Length(max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')


class CheckoutForm(FlaskForm):
    address_id = SelectField('Select Address', coerce=int, validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=[
        ('cod', 'Cash on Delivery (COD)'),
        ('razorpay', 'Razorpay (Cards, UPI, Net Banking)'),
        ('stripe', 'Stripe (International Cards)'),
        ('paypal', 'PayPal'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet')
    ], validators=[DataRequired()])
    coupon_code = StringField('Coupon Code (Optional)', validators=[Optional()])
    notes = TextAreaField('Order Notes (Optional)', validators=[Optional()])
    submit = SubmitField('Place Order')


class ProductForm(FlaskForm):
    product_id = HiddenField()
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    brand = StringField('Brand', validators=[DataRequired(), Length(max=120)])
    category = SelectField('Category', choices=[
        ('RC Cars', 'RC Cars'),
        ('Metal Cars', 'Metal Cars'),
        ('Hot Wheels', 'Hot Wheels'),
        ('Accessories', 'Accessories'),
    ], validators=[DataRequired()])
    subcategory = StringField('Subcategory', validators=[Optional(), Length(max=120)])
    description = TextAreaField('Description', validators=[DataRequired()])
    short_description = StringField('Short Description', validators=[Optional(), Length(max=500)])
    price = DecimalField('Price (₹)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    mrp = DecimalField('MRP (₹)', places=2, validators=[Optional(), NumberRange(min=0)])
    stock = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])
    sku = StringField('SKU', validators=[DataRequired(), Length(max=80)])
    image = StringField('Main Image URL', validators=[Optional()])
    tags = StringField('Tags (comma-separated)', validators=[Optional()])
    weight = DecimalField('Weight (grams)', places=2, validators=[Optional(), NumberRange(min=0)])
    dimensions = StringField('Dimensions (LxWxH in cm)', validators=[Optional()])
    featured = BooleanField('Featured Product')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Product')

    def validate_image(self, field):
        v = (field.data or '').strip()
        if not v:
            return
        # Accept absolute URLs or application-relative paths like '/static/uploads/...'
        if not (v.startswith('/') or v.startswith('http://') or v.startswith('https://')):
            raise ValidationError('Image must be a full URL or a path starting with "/"')

    def validate_sku(self, field):
        """Ensure SKU is unique across products. Uses a runtime import to avoid circular imports."""
        sku_val = (field.data or '').strip()
        if not sku_val:
            return
        try:
            from models import Product
        except Exception:
            # If models cannot be imported (e.g., during certain test phases), skip validation
            return

        product_id = None
        try:
            product_id = int(self.product_id.data) if getattr(self, 'product_id', None) and self.product_id.data else None
        except Exception:
            product_id = None

        existing = Product.query.filter_by(sku=sku_val).first()
        if existing and (not product_id or existing.id != product_id):
            raise ValidationError('SKU already in use by another product')


class ReviewForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    title = StringField('Review Title', validators=[Optional(), Length(max=200)])
    comment = TextAreaField('Your Review', validators=[Optional()])
    submit = SubmitField('Submit Review')


class BlogForm(FlaskForm):
    post_id = HiddenField()
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    headline = StringField('Headline', validators=[DataRequired(), Length(max=220)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=220)])
    hero_image = StringField('Hero Image URL', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    author = StringField('Author', validators=[Optional(), Length(max=120)])
    meta_description = StringField('Meta Description', validators=[Optional(), Length(max=300)])
    meta_keywords = StringField('Meta Keywords', validators=[Optional(), Length(max=500)])
    is_published = BooleanField('Publish', default=False)
    submit = SubmitField('Save Post')

    def validate_hero_image(self, field):
        v = (field.data or '').strip()
        if not v:
            raise ValidationError('Hero image is required')
        # Accept absolute URLs or application-relative paths like '/static/uploads/...'
        if not (v.startswith('/') or v.startswith('http://') or v.startswith('https://')):
            raise ValidationError('Hero image must be a full URL or a path starting with "/"')


class CouponForm(FlaskForm):
    coupon_id = HiddenField()
    code = StringField('Coupon Code', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional()])
    discount_type = SelectField('Discount Type', choices=[
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], validators=[DataRequired()])
    discount_value = DecimalField('Discount Value', places=2, validators=[DataRequired(), NumberRange(min=0)])
    min_purchase = DecimalField('Minimum Purchase (₹)', places=2, validators=[Optional(), NumberRange(min=0)])
    max_discount = DecimalField('Maximum Discount (₹)', places=2, validators=[Optional(), NumberRange(min=0)])
    usage_limit = IntegerField('Total Usage Limit', validators=[Optional(), NumberRange(min=0)])
    user_limit = IntegerField('Per User Limit', validators=[Optional(), NumberRange(min=1)], default=1)
    # Use the HTML5 datetime-local format so WTForms can parse inputs from
    # `<input type="datetime-local">`. The format below matches that input.
    valid_from = DateTimeField('Valid From', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], default=datetime.utcnow)
    valid_until = DateTimeField('Valid Until', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Coupon')


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[Optional()])
    category = SelectField('Category', validators=[Optional()])
    brand = SelectField('Brand', validators=[Optional()])
    min_price = DecimalField('Min Price', validators=[Optional(), NumberRange(min=0)])
    max_price = DecimalField('Max Price', validators=[Optional(), NumberRange(min=0)])
    sort = SelectField('Sort By', choices=[
        ('latest', 'Latest First'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
        ('rating', 'Highest Rated'),
        ('popular', 'Most Popular')
    ], default='latest')
    submit = SubmitField('Search')

# Metal Zone - Premium RC Cars, Metal Cars & Hot Wheels E-Commerce Platform

A fully functional, production-ready e-commerce website for Metal Zone, specializing in RC Cars, Metal Cars, and Hot Wheels collectibles.

## Features

### Customer Features
- **Product Browsing**: Browse products with advanced filters (category, brand, price range, sorting)
- **Product Details**: Detailed product pages with images, descriptions, ratings, and reviews
- **Shopping Cart**: Add, update, and remove items from cart
- **Wishlist**: Save favorite products for later
- **User Accounts**: Registration, login, and profile management
- **Address Management**: Multiple shipping addresses
- **Order Management**: Place orders, track status, view order history
- **Reviews & Ratings**: Submit and view product reviews (admin-moderated)
- **Search**: Real-time product search
- **Coupons**: Apply discount coupons at checkout
- **Blog**: Read blog posts and guides

### Admin Features
- **Dashboard**: Comprehensive admin dashboard with statistics
- **Product Management**: Add, edit, delete products with image uploads
- **Order Management**: View and update order statuses
- **User Management**: Manage users, grant admin access, block users
- **Blog Management**: Create and manage blog posts
- **Coupon Management**: Create and manage discount coupons
- **Review Moderation**: Approve or delete product reviews
- **Contact Messages**: View and respond to customer messages
- **Reports**: Sales reports and analytics
- **Low Stock Alerts**: Automatic alerts for products running low

### Security Features
- CSRF protection
- Password hashing (Werkzeug)
- SQL injection protection (SQLAlchemy ORM)
- XSS protection (Jinja2 auto-escaping)
- Admin activity logging
- Session-based authentication

### Payment Integration
- Cash on Delivery (COD)
- Razorpay (Cards, UPI, Net Banking)
- Stripe (International Cards)
- PayPal
- UPI
- Wallet

*Note: Payment gateway integrations require API keys to be configured in production.*

## Technology Stack

- **Backend**: Python 3.10+, Flask
- **Database**: SQLite (can be easily migrated to PostgreSQL)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF, WTForms
- **ORM**: SQLAlchemy

## Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run the application**:
```bash
python app.py
```

5. **Access the application**:
   - Customer site: http://localhost:5000
   - Admin login: 
     - Email: `admin@metalzone.com`
     - Password: `Admin@123`

## What's New in v2.0.0

✅ All critical bugs fixed  
✅ Security improvements (rate limiting, session security)  
✅ SEO features (sitemap, robots.txt, meta tags)  
✅ Invoice generation  
✅ Image file upload for admin  
✅ Recently viewed products  
✅ Product tags display  
✅ Enhanced accessibility  
✅ Database optimization  
✅ Performance improvements  

See [CHANGELOG.md](CHANGELOG.md) for complete list of changes.

## Default Accounts

### Admin Account
- Email: `admin@metalzone.com`
- Password: `Admin@123`

### Test User Accounts
- Email: `rahul@example.com`
- Password: `User@123`
- Email: `priya@example.com`
- Password: `User@123`

## Project Structure

```
MetalZone/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── forms.py               # WTForms form definitions
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── metal_zone.db         # SQLite database (created on first run)
├── static/
│   ├── css/
│   │   └── style.css     # Main stylesheet with brand colors
│   ├── js/
│   │   └── app.js        # JavaScript for interactivity
│   └── uploads/          # Product images (created automatically)
└── templates/
    ├── base.html         # Base template
    ├── home.html         # Homepage
    ├── products.html     # Product listing
    ├── product_detail.html
    ├── cart.html
    ├── checkout.html
    ├── profile.html
    ├── orders.html
    ├── order_detail.html
    ├── wishlist.html
    ├── addresses.html
    ├── login.html
    ├── register.html
    ├── about.html
    ├── contact.html
    ├── blog_listing.html
    ├── blog_detail.html
    └── admin/
        ├── dashboard.html
        ├── products.html
        ├── orders.html
        ├── users.html
        ├── blog.html
        ├── coupons.html
        ├── reviews.html
        ├── messages.html
        └── reports.html
```

## Brand Colors

- **Header Background**: #df2e7e
- **Product Page Background**: #662a0d
- **Product Card Background**: #852f12
- **Add to Cart Button**: #ea580c
- **Product MRP Price**: #fcd34d
- **Footer Background**: #de6f08

## Database

The application uses SQLite by default. The database file (`metal_zone.db`) is created automatically on first run with sample data including:
- Admin user
- Test users
- Sample products (RC Cars, Metal Cars, Hot Wheels)
- Sample blog posts
- Sample coupons

## Production Deployment

For production deployment:

1. **Change the secret key** in `app.py`:
```python
app.config['SECRET_KEY'] = 'your-secret-key-here'
```

2. **Use PostgreSQL** instead of SQLite:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/metalzone'
```

3. **Set up environment variables** for sensitive data

4. **Configure payment gateway API keys**

5. **Set up HTTPS** (required for production)

6. **Configure email/SMS services** for order confirmations

7. **Set up regular database backups**

## Features Implemented

✅ User authentication and authorization
✅ Product catalog with filters and search
✅ Shopping cart and checkout
✅ Order management
✅ Wishlist
✅ Reviews and ratings
✅ Admin panel
✅ Blog system
✅ Coupon system
✅ Address management
✅ Responsive design
✅ Security features (CSRF, XSS protection, password hashing)
✅ Admin activity logging
✅ Low stock alerts
✅ Sales reports

## License

This project is proprietary software for Metal Zone.

## Support

For support, email support@metalzone.com or contact +91 98765 43210.

---

**Metal Zone** - Your Premier Destination for Premium RC Cars, Metal Cars & Hot Wheels


"""
Normalization script for existing Product.image values.

Run this once from the project root to normalize entries in the database.

Usage (PowerShell):
    C:/Users/verif/AppData/Local/Programs/Python/Python310/GlideMans/.venv/Scripts/python.exe scripts/normalize_images.py

This script will:
 - Trim whitespace
 - Convert bare filenames into '/static/uploads/<filename>'
 - Convert bare filenames into '/uploads/<filename>'
 - Prepend leading slash for 'static/...' entries
 - Leave http(s) URLs untouched
 - Set empty values to NULL
"""
from app import app, db
from models import Product
from flask import url_for

def normalize_value(p):
    if not p:
        return None
    s = str(p).strip()
    if not s:
        return None
    if s.startswith('http://') or s.startswith('https://'):
        return s
    if s.startswith('/static/'):
        return s
    if s.startswith('static/'):
        return '/' + s
    if '/' not in s:
        return '/uploads/' + s
    return s if s.startswith('/') else '/' + s

def main():
    with app.app_context():
        products = Product.query.all()
        changed = 0
        for p in products:
            new = normalize_value(p.image)
            if new != p.image:
                p.image = new
                db.session.add(p)
                changed += 1
        if changed:
            db.session.commit()
            print(f"Normalized {changed} product image(s)")
        else:
            print("No product images needed normalization.")

if __name__ == '__main__':
    main()

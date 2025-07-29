#!/usr/bin/env python3
"""
Script to create an admin user for the Gaming Center application.
Run this script to create the initial admin user.
"""

import sys
import os
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AdminUser

def create_admin():
    with app.app_context():
        # Check if admin already exists
        existing_admin = AdminUser.query.first()
        if existing_admin:
            print(f"Admin user already exists: {existing_admin.username}")
            return

        # Create admin user
        username = input("Enter admin username: ").strip()
        if not username:
            print("Username cannot be empty!")
            return

        email = input("Enter admin email: ").strip()
        if not email:
            print("Email cannot be empty!")
            return

        password = input("Enter admin password: ").strip()
        if not password:
            print("Password cannot be empty!")
            return

        # Create the admin user
        admin = AdminUser()
        admin.username = username
        admin.email = email
        admin.password_hash = generate_password_hash(password)

        try:
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user '{username}' created successfully!")
            print("You can now login to the Gaming Center admin panel.")
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.session.rollback()

if __name__ == "__main__":
    print("Gaming Center - Admin User Creation")
    print("=" * 40)
    create_admin()

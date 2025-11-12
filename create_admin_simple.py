#!/usr/bin/env python3
"""
Simple Admin Account Creation Script

Run this from the project root:
    python create_admin_simple.py
"""

import os
import sys

# Change to web directory
web_dir = os.path.join(os.path.dirname(__file__), "web")
os.chdir(web_dir)
sys.path.insert(0, web_dir)

# Now import
from datetime import datetime, timedelta
from app import app
from database import db, User


def main():
    print("=" * 80)
    print("QUNEX TRADE - Admin Account Creation")
    print("=" * 80)

    admin_email = "admin@qunextrade.com"
    admin_username = "admin"
    admin_password = "qunex2025!Admin"

    with app.app_context():
        try:
            # Check if admin exists
            existing = User.query.filter_by(email=admin_email).first()

            if existing:
                print(f"\nAdmin already exists: {existing.email}")
                print("Updating admin account...")

                existing.set_password(admin_password)
                existing.subscription_tier = "developer"
                existing.subscription_status = "active"
                existing.subscription_start = datetime.utcnow()
                existing.subscription_end = datetime.utcnow() + timedelta(days=3650)
                existing.email_verified = True

                db.session.commit()
                print("\nAdmin account updated!")

            else:
                print("\nCreating new admin account...")

                admin = User(
                    email=admin_email,
                    username=admin_username,
                    subscription_tier="developer",
                    subscription_status="active",
                    subscription_start=datetime.utcnow(),
                    subscription_end=datetime.utcnow() + timedelta(days=3650),
                    email_verified=True,
                )
                admin.set_password(admin_password)

                db.session.add(admin)
                db.session.commit()

                print("\nAdmin account created!")

            print("\n" + "=" * 80)
            print("ADMIN CREDENTIALS")
            print("=" * 80)
            print(f"Email:    {admin_email}")
            print(f"Username: {admin_username}")
            print(f"Password: {admin_password}")
            print(f"Tier:     developer")
            print("=" * 80)
            print("\nWARNING: Change password after first login!")
            print("=" * 80)

        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()
            return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

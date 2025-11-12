#!/usr/bin/env python3
"""
Create Admin Account for Qunex Trade

This script creates a developer-tier admin account with full access.
Run this after migrating to Supabase to restore admin access.
"""

import os
import sys
from datetime import datetime, timedelta

# Set console encoding to UTF-8 for emoji support
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Import Flask app first to ensure proper initialization
from web.app import app
from web.database import db, User


def create_admin():
    """Create admin account with developer-tier access"""

    print("=" * 80)
    print("QUNEX TRADE - Admin Account Creation")
    print("=" * 80)

    # Admin credentials
    admin_email = "admin@qunextrade.com"
    admin_username = "admin"
    admin_password = "qunex2025!Admin"  # Change this after first login!

    try:
        with app.app_context():
            # Check if admin already exists
            existing_admin = User.query.filter_by(email=admin_email).first()

            if existing_admin:
                print(f"❌ Admin account already exists: {admin_email}")
                print(f"   Username: {existing_admin.username}")
                print(f"   Tier: {existing_admin.subscription_tier}")
                print(f"   Status: {existing_admin.subscription_status}")

                # Update existing admin
                response = input("\nUpdate existing admin account? (y/n): ")
                if response.lower() != "y":
                    print("Aborted.")
                    return

                # Update password and tier
                existing_admin.set_password(admin_password)
                existing_admin.subscription_tier = "developer"
                existing_admin.subscription_status = "active"
                existing_admin.subscription_start = datetime.utcnow()
                existing_admin.subscription_end = datetime.utcnow() + timedelta(
                    days=365 * 10
                )  # 10 years
                existing_admin.email_verified = True

                db.session.commit()

                print(f"\n✓ Admin account updated successfully!")
                print(f"  Email: {admin_email}")
                print(f"  Username: {existing_admin.username}")
                print(f"  Password: {admin_password}")
                print(f"  Tier: developer")
                print(f"  Status: active")

            else:
                # Create new admin
                admin_user = User(
                    email=admin_email,
                    username=admin_username,
                    subscription_tier="developer",
                    subscription_status="active",
                    subscription_start=datetime.utcnow(),
                    subscription_end=datetime.utcnow() + timedelta(days=365 * 10),  # 10 years
                    email_verified=True,
                    created_at=datetime.utcnow(),
                )

                admin_user.set_password(admin_password)

                db.session.add(admin_user)
                db.session.commit()

                print(f"\n✓ Admin account created successfully!")
                print(f"  Email: {admin_email}")
                print(f"  Username: {admin_username}")
                print(f"  Password: {admin_password}")
                print(f"  Tier: developer")
                print(f"  Status: active")

            print("\n⚠️  IMPORTANT: Change the default password after first login!")
            print("=" * 80)

            return True

    except Exception as e:
        print(f"\n❌ Error creating admin account: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_admin()
    sys.exit(0 if success else 1)

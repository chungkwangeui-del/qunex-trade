"""
Initialize database and create admin account
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from database import User

def init_database():
    """Initialize database and create admin account"""
    with app.app_context():
        # Drop all tables and recreate (fresh start)
        print("Dropping existing tables...")
        db.drop_all()

        print("Creating new tables...")
        db.create_all()

        # Check if admin exists
        admin = db.session.execute(
            db.select(User).filter_by(email='admin@qunextrade.com')
        ).scalar_one_or_none()

        if not admin:
            print("\nCreating admin account...")
            admin = User(
                email='admin@qunextrade.com',
                username='admin',
                subscription_tier='developer',
                subscription_status='active'
            )
            admin.set_password('admin123')  # Change this password!

            db.session.add(admin)
            db.session.commit()

            print("✓ Admin account created!")
            print("  Email: admin@qunextrade.com")
            print("  Password: admin123")
            print("  Tier: Developer")
            print("\n⚠️  Please change the password after first login!")
        else:
            print("Admin account already exists")

        # Create a test user
        test_user = db.session.execute(
            db.select(User).filter_by(email='test@qunextrade.com')
        ).scalar_one_or_none()
        if not test_user:
            print("\nCreating test user...")
            test_user = User(
                email='test@qunextrade.com',
                username='testuser',
                subscription_tier='free',
                subscription_status='active'
            )
            test_user.set_password('test123')

            db.session.add(test_user)
            db.session.commit()

            print("✓ Test user created!")
            print("  Email: test@qunextrade.com")
            print("  Password: test123")
            print("  Tier: Free")

        print("\n" + "="*50)
        print("Database initialized successfully!")
        print("="*50)

        # Show all users
        users = db.session.execute(db.select(User)).scalars().all()
        print(f"\nTotal users: {len(users)}")
        for user in users:
            print(f"  - {user.email} ({user.username}) - {user.subscription_tier}")

if __name__ == '__main__':
    init_database()

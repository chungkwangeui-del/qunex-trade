"""
Simple database creation script
"""

from flask import Flask
from database import db, User
import os

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'

# Database configuration - Use PostgreSQL in production, SQLite in development
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Render provides DATABASE_URL starting with postgres://, but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print("Using PostgreSQL database")
else:
    # Local development - use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qunextrade.db'
    print("Using SQLite database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    # Create tables if they don't exist (won't drop existing data)
    print("Creating/updating database tables...")
    db.create_all()

    # Check if admin account exists
    admin = db.session.execute(
        db.select(User).filter_by(email='admin@qunextrade.com')
    ).scalar_one_or_none()

    if not admin:
        # Create admin account only if it doesn't exist
        print("\nCreating admin account...")
        admin = User(
            email='admin@qunextrade.com',
            username='admin',
            email_verified=True,
            subscription_tier='developer',
            subscription_status='active'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    # Check if test user exists
    test_user = db.session.execute(
        db.select(User).filter_by(email='test@test.com')
    ).scalar_one_or_none()

    if not test_user:
        # Create test user only if it doesn't exist
        print("Creating test user...")
        test_user = User(
            email='test@test.com',
            username='testuser',
            email_verified=True,
            subscription_tier='free',
            subscription_status='active'
        )
        test_user.set_password('test123')
        db.session.add(test_user)

    # Commit
    db.session.commit()

    print("\n" + "="*60)
    print("Database created successfully!")
    print("="*60)
    print("\nAdmin Account:")
    print("  Email: admin@qunextrade.com")
    print("  Password: admin123")
    print("  Tier: Developer")
    print("\nTest Account:")
    print("  Email: test@test.com")
    print("  Password: test123")
    print("  Tier: Free")
    print("\nWARNING: Change the admin password after first login!")
    print("="*60)

    # Show all users
    users = db.session.execute(db.select(User)).scalars().all()
    print(f"\nTotal users in database: {len(users)}")
    for user in users:
        print(f"  - {user.email} | {user.username} | {user.subscription_tier}")

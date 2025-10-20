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
    # Render provides DATABASE_URL starting with postgres://, convert to postgresql+psycopg:// for psycopg3
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print("Using PostgreSQL database with psycopg3")
else:
    # Local development - use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qunextrade.db'
    print("Using SQLite database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    # Check if we need to recreate tables (schema changed)
    # Only do this ONCE when deploying new schema changes
    RECREATE_TABLES = os.getenv('RECREATE_DB_TABLES', 'false').lower() == 'true'

    if RECREATE_TABLES:
        print("⚠️  RECREATING ALL TABLES (RECREATE_DB_TABLES=true)")
        print("⚠️  This will DELETE all existing data!")
        db.drop_all()
        db.create_all()
        print("✅ Tables recreated")
    else:
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

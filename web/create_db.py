"""
Simple database creation script
"""

from flask import Flask
from database import db, User

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qunextrade.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    # Drop and recreate all tables
    print("Dropping existing tables...")
    db.drop_all()

    print("Creating tables...")
    db.create_all()

    # Create admin account
    print("\nCreating admin account...")
    admin = User(
        email='admin@qunextrade.com',
        username='admin',
        subscription_tier='developer',
        subscription_status='active'
    )
    admin.set_password('admin123')

    db.session.add(admin)

    # Create test user
    print("Creating test user...")
    test_user = User(
        email='test@test.com',
        username='testuser',
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

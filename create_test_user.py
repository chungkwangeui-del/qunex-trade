from dotenv import load_dotenv
import os

# Force load .env
load_dotenv()
print(f"Loaded DATABASE_URL: {os.getenv('DATABASE_URL')}")

from web.app import create_app
from web.database import db, User
from datetime import datetime, timezone, timedelta

app = create_app()

with app.app_context():
    # Check if user exists
    user = User.query.filter_by(email="test@qunextrade.com").first()
    if not user:
        user = User(
            email="test@qunextrade.com",
            username="testuser",
            subscription_tier="premium",
            subscription_status="active",
            subscription_start=datetime.now(timezone.utc),
            subscription_end=datetime.now(timezone.utc) + timedelta(days=365),
            email_verified=True
        )
        user.set_password("testpassword123")
        db.session.add(user)
        db.session.commit()
        print("Test user created successfully.")
    else:
        print("Test user already exists.")
        
    # Verify
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    import os
    print(f"CWD: {os.getcwd()}")
    verified_user = User.query.filter_by(email="test@qunextrade.com").first()
    if verified_user:
        print(f"Verified user in DB: {verified_user.email}, ID: {verified_user.id}")
        print(f"Password hash: {verified_user.password_hash}")
    else:
        print("CRITICAL: User NOT found after commit!")

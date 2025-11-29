from web.app import create_app
from web.database import db, User

app = create_app()

with app.app_context():
    # Check if user exists
    user = db.session.execute(db.select(User).filter_by(email="test@example.com")).scalar_one_or_none()
    
    if user:
        print(f"Updating existing user {user.username}...")
        user.email_verified = True
        user.subscription_tier = "developer"
        user.set_password("password")
    else:
        print("Creating new test user...")
        user = User(
            username="testuser",
            email="test@example.com",
            email_verified=True,
            subscription_tier="developer",
            subscription_status="active"
        )
        user.set_password("password")
        db.session.add(user)
    
    db.session.commit()
    print("User 'test@example.com' with password 'password' is ready and verified.")

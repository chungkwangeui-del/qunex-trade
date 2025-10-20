"""
Upgrade user to Premium tier (Developer account)
"""
from database import db, User
from app import app

def upgrade_user_to_premium(email):
    """Upgrade user to premium tier"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()

        if not user:
            print(f"❌ User not found: {email}")
            return False

        print(f"Found user: {user.username} ({user.email})")
        print(f"Current tier: {user.subscription_tier}")
        print(f"Current status: {user.subscription_status}")

        # Upgrade to premium
        user.subscription_tier = 'premium'
        user.subscription_status = 'active'

        db.session.commit()

        print(f"\n✅ User upgraded to Premium!")
        print(f"New tier: {user.subscription_tier}")
        print(f"New status: {user.subscription_status}")

        return True

if __name__ == '__main__':
    # Upgrade the developer account
    email = 'kwangui2@illinois.edu'
    upgrade_user_to_premium(email)

"""
Upgrade user to Premium tier directly via SQL
Run this on Render via SSH or add as a management command
"""
import sqlite3
import os

# Database path
db_path = 'qunextrade.db'

def upgrade_user_to_premium(email):
    """Upgrade user to premium tier"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print("This script should be run on the Render server where the database exists.")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT id, username, email, subscription_tier, subscription_status FROM user WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        print(f"❌ User not found: {email}")
        conn.close()
        return False

    user_id, username, user_email, current_tier, current_status = user
    print(f"Found user: {username} ({user_email})")
    print(f"Current tier: {current_tier}")
    print(f"Current status: {current_status}")

    # Upgrade to premium
    cursor.execute("""
        UPDATE user
        SET subscription_tier = 'premium',
            subscription_status = 'active'
        WHERE email = ?
    """, (email,))

    conn.commit()

    # Verify update
    cursor.execute("SELECT subscription_tier, subscription_status FROM user WHERE email = ?", (email,))
    new_tier, new_status = cursor.fetchone()

    print(f"\n✅ User upgraded to Premium!")
    print(f"New tier: {new_tier}")
    print(f"New status: {new_status}")

    conn.close()
    return True

if __name__ == '__main__':
    # Upgrade the developer account
    email = 'kwangui2@illinois.edu'
    upgrade_user_to_premium(email)

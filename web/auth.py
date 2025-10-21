"""
Authentication routes and utilities
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
import os
import random
import secrets
import requests

try:
    from database import db, User
except ImportError:
    from web.database import db, User

auth = Blueprint('auth', __name__)

# Initialize OAuth
oauth = OAuth()

# reCAPTCHA Secret Key (from environment variable)
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')

def verify_recaptcha(token):
    """Verify reCAPTCHA v3 token - TEMPORARILY DISABLED"""
    # DISABLED: reCAPTCHA v3 causing infinite loading issue on frontend
    # TODO: Fix recaptcha.js form submission infinite loop before re-enabling
    print("[INFO] reCAPTCHA verification temporarily disabled")
    return True

# Google OAuth configuration (only if credentials are set)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    GOOGLE_OAUTH_ENABLED = True
else:
    google = None
    GOOGLE_OAUTH_ENABLED = False


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Verify reCAPTCHA
        recaptcha_token = request.form.get('recaptcha_token')
        if not verify_recaptcha(recaptcha_token):
            flash('Security verification failed. Please try again.', 'error')
            return redirect(url_for('auth.login'))

        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        print(f"[DEBUG] Login attempt for email: {email}")

        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()

        if not user:
            print(f"[DEBUG] User not found: {email}")
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))

        print(f"[DEBUG] User found: {user.username}, checking password...")

        if not user.check_password(password):
            print(f"[DEBUG] Password check failed for {email}")
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))

        print(f"[DEBUG] Login successful for {email}")
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('index'))

    return render_template('login.html', google_oauth_enabled=GOOGLE_OAUTH_ENABLED)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Verify reCAPTCHA
        recaptcha_token = request.form.get('recaptcha_token')
        if not verify_recaptcha(recaptcha_token):
            flash('Security verification failed. Please try again.', 'error')
            return redirect(url_for('auth.signup'))

        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        print(f"[DEBUG] Signup attempt - Email: {email}, Username: {username}")

        # Check if email was verified
        if not session.get('email_verified') or session.get('verified_email') != email:
            flash('Please verify your email first', 'error')
            return redirect(url_for('auth.signup'))

        # Check if user exists
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if user:
            print(f"[DEBUG] Email already exists: {email}")
            flash('Email already exists', 'error')
            return redirect(url_for('auth.signup'))

        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user:
            print(f"[DEBUG] Username already taken: {username}")
            flash('Username already taken', 'error')
            return redirect(url_for('auth.signup'))

        # Create new user
        new_user = User(
            email=email,
            username=username,
            email_verified=True,
            subscription_tier='free',
            subscription_status='active'
        )
        new_user.set_password(password)

        print(f"[DEBUG] Creating new user: {username}")

        db.session.add(new_user)
        db.session.commit()

        print(f"[DEBUG] User created successfully: {new_user.id}")

        # Clear verification session data
        session.pop('email_verified', None)
        session.pop('verified_email', None)
        session.pop('verification_code', None)
        session.pop('verification_email', None)
        session.pop('verification_expiry', None)

        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('signup.html')


@auth.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('index'))


@auth.route('/account')
@login_required
def account():
    """User account page"""
    return render_template('account.html', user=current_user)


@auth.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard - only accessible to developer tier users"""
    # Check if user is developer tier (admin)
    if current_user.subscription_tier != 'developer':
        flash('Unauthorized access - Admin only', 'error')
        return redirect(url_for('index'))

    # Get all users
    all_users = db.session.execute(
        db.select(User).order_by(User.created_at.desc())
    ).scalars().all()

    # Calculate statistics
    total_users = len(all_users)
    free_users = len([u for u in all_users if u.subscription_tier == 'free'])
    pro_users = len([u for u in all_users if u.subscription_tier == 'pro'])
    premium_users = len([u for u in all_users if u.subscription_tier == 'premium'])
    developer_users = len([u for u in all_users if u.subscription_tier == 'developer'])

    # Calculate monthly revenue (developer tier is free/internal)
    monthly_revenue = (pro_users * 19.99) + (premium_users * 49.99)

    stats = {
        'total_users': total_users,
        'free_users': free_users,
        'pro_users': pro_users,
        'premium_users': premium_users,
        'developer_users': developer_users,
        'monthly_revenue': monthly_revenue
    }

    return render_template('admin_dashboard.html', users=all_users, stats=stats)


@auth.route('/admin/upgrade-user/<email>/<tier>')
def admin_upgrade_user(email, tier):
    """Admin endpoint to upgrade users (use with caution!)"""
    # Simple security: require admin password in query param
    import os
    admin_password = os.getenv('ADMIN_PASSWORD', 'change-me-in-production')

    if request.args.get('password') != admin_password:
        return jsonify({'error': 'Unauthorized'}), 403

    if tier not in ['free', 'pro', 'premium', 'developer']:
        return jsonify({'error': 'Invalid tier'}), 400

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    old_tier = user.subscription_tier
    user.subscription_tier = tier
    user.subscription_status = 'active'
    db.session.commit()

    return jsonify({
        'success': True,
        'email': email,
        'username': user.username,
        'old_tier': old_tier,
        'new_tier': tier,
        'status': 'active'
    })


@auth.route('/google/login')
def google_login():
    """Initiate Google OAuth login"""
    if not GOOGLE_OAUTH_ENABLED:
        flash('Google login is not configured. Please use email/password login.', 'error')
        return redirect(url_for('auth.login'))

    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_OAUTH_ENABLED:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Get token from Google
        token = google.authorize_access_token()

        # Get user info from Google
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user information from Google', 'error')
            return redirect(url_for('auth.login'))

        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name', '').split()[0]  # First name
        picture = user_info.get('picture')

        # Check if user exists by Google ID
        user = db.session.execute(
            db.select(User).filter_by(google_id=google_id)
        ).scalar_one_or_none()

        if not user:
            # Check if email already exists
            user = db.session.execute(
                db.select(User).filter_by(email=email)
            ).scalar_one_or_none()

            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.oauth_provider = 'google'
                user.profile_picture = picture
                db.session.commit()
                flash('Google account linked successfully!', 'success')
            else:
                # Create new user
                # Generate unique username
                base_username = name.lower().replace(' ', '')
                username = base_username
                counter = 1

                while db.session.execute(
                    db.select(User).filter_by(username=username)
                ).scalar_one_or_none():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User(
                    email=email,
                    username=username,
                    google_id=google_id,
                    oauth_provider='google',
                    profile_picture=picture,
                    subscription_tier='free',
                    subscription_status='active'
                )
                # No password needed for OAuth users
                db.session.add(user)
                db.session.commit()
                flash('Account created successfully with Google!', 'success')

        # Log in the user
        login_user(user, remember=True)
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Google login failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    # OAuth users don't have passwords
    if not current_user.password_hash:
        flash('OAuth users cannot change password. Please use your Google account.', 'error')
        return redirect(url_for('auth.account'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # Validate current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.account'))

    # Validate new password
    if len(new_password) < 6:
        flash('New password must be at least 6 characters', 'error')
        return redirect(url_for('auth.account'))

    # Validate password match
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('auth.account'))

    # Update password
    current_user.set_password(new_password)
    db.session.commit()

    flash('Password updated successfully!', 'success')
    return redirect(url_for('auth.account'))


@auth.route('/send-verification-code', methods=['POST'])
def send_verification_code():
    """Send 6-digit verification code to email"""
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    # Generate 6-digit code
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # Store code in session temporarily (expires in 10 minutes)
    session['verification_code'] = code
    session['verification_email'] = email
    session['verification_expiry'] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    # Send email
    try:
        from app import mail

        msg = Message(
            'Email Verification Code - Qunex Trade',
            recipients=[email]
        )
        msg.body = f'''Welcome to Qunex Trade!

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
Qunex Trade Team
'''
        msg.html = f'''
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2 style="color: #00f5ff;">Welcome to Qunex Trade!</h2>
    <p>Your verification code is:</p>
    <h1 style="background: linear-gradient(135deg, #00f5ff 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-size: 48px; letter-spacing: 10px; text-align: center;">{code}</h1>
    <p style="color: #999; font-size: 0.9em;">This code will expire in 10 minutes.</p>
    <p style="margin-top: 30px; color: #999; font-size: 0.85em;">If you didn't request this code, please ignore this email.</p>
    <p style="margin-top: 20px;">Best regards,<br><strong>Qunex Trade Team</strong></p>
</body>
</html>
'''
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Verification code sent!'})
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({'success': False, 'message': 'Failed to send email. Please try again.'}), 500


@auth.route('/verify-code', methods=['POST'])
def verify_code():
    """Verify the 6-digit code"""
    data = request.get_json()
    code = data.get('code')

    if not code:
        return jsonify({'success': False, 'message': 'Code is required'}), 400

    # Check if code matches and hasn't expired
    stored_code = session.get('verification_code')
    stored_email = session.get('verification_email')
    expiry_str = session.get('verification_expiry')

    if not stored_code or not expiry_str:
        return jsonify({'success': False, 'message': 'No verification code found. Please request a new one.'}), 400

    expiry = datetime.fromisoformat(expiry_str)
    if datetime.utcnow() > expiry:
        return jsonify({'success': False, 'message': 'Verification code expired. Please request a new one.'}), 400

    if code != stored_code:
        return jsonify({'success': False, 'message': 'Invalid verification code'}), 400

    # Code is valid
    session['email_verified'] = True
    session['verified_email'] = stored_email

    return jsonify({'success': True, 'message': 'Email verified successfully!'})


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page - send reset email"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Verify reCAPTCHA
        recaptcha_token = request.form.get('recaptcha_token')
        if not verify_recaptcha(recaptcha_token):
            flash('Security verification failed. Please try again.', 'error')
            return redirect(url_for('auth.forgot_password'))

        email = request.form.get('email')

        user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

        # Always show success message (security: don't reveal if email exists)
        flash('If an account with that email exists, a password reset link has been sent.', 'info')

        if user and user.password_hash:  # Only send if user exists and has password (not OAuth)
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
            db.session.commit()

            # Send reset email
            try:
                from app import mail

                reset_url = url_for('auth.reset_password', token=token, _external=True)

                msg = Message(
                    'Password Reset Request - Qunex Trade',
                    recipients=[user.email]
                )
                msg.body = f'''Hello {user.username},

You requested a password reset for your Qunex Trade account.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you didn't request this, please ignore this email. Your password will remain unchanged.

Best regards,
Qunex Trade Team
'''
                msg.html = f'''
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #00f5ff 0%, #7c3aed 100%); padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0;">Password Reset</h1>
    </div>
    <div style="padding: 40px 30px;">
        <p style="font-size: 16px;">Hello <strong>{user.username}</strong>,</p>
        <p style="font-size: 16px;">You requested a password reset for your Qunex Trade account.</p>
        <p style="font-size: 16px;">Click the button below to reset your password (valid for 1 hour):</p>
        <div style="text-align: center; margin: 40px 0;">
            <a href="{reset_url}" style="background: linear-gradient(135deg, #00f5ff 0%, #7c3aed 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 10px; display: inline-block; font-weight: bold; font-size: 16px;">Reset Password</a>
        </div>
        <p style="font-size: 14px; color: #666;">Or copy and paste this link into your browser:</p>
        <p style="font-size: 14px; color: #00f5ff; word-break: break-all;">{reset_url}</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">If you didn't request this, please ignore this email. Your password will remain unchanged.</p>
        <p style="font-size: 14px; margin-top: 20px;">Best regards,<br><strong>Qunex Trade Team</strong></p>
    </div>
</body>
</html>
'''
                mail.send(msg)
            except Exception as e:
                print(f"Error sending email: {e}")

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Find user with this token
    user = db.session.execute(
        db.select(User).filter_by(reset_token=token)
    ).scalar_one_or_none()

    # Check if token is valid and not expired
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validate password
        if len(new_password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('reset_password.html', token=token)

        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)

        # Update password and clear reset token
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)

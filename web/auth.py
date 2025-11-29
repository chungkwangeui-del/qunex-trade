"""
Authentication routes and utilities
"""

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    session,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from flask_wtf.csrf import generate_csrf
from datetime import datetime, timedelta, timezone
from authlib.integrations.flask_client import OAuth
from typing import Dict, Any, Optional, Tuple, Union
import os
import random
import secrets
import requests
import logging

try:
    from database import db, User
except ImportError:
    from web.database import db, User

auth = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

# Initialize OAuth
oauth = OAuth()

# reCAPTCHA Secret Key (from environment variable)
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")


def verify_recaptcha(token: Optional[str]) -> bool:
    """
    Verify reCAPTCHA v3 token - TEMPORARILY DISABLED.

    Args:
        token: reCAPTCHA token from client

    Returns:
        True (always, as verification is disabled)

    Note:
        reCAPTCHA v3 is currently disabled due to infinite loading issue.
        TODO: Fix recaptcha.js form submission before re-enabling
    """
    logger.info("reCAPTCHA verification temporarily disabled")
    return True


# Google OAuth configuration (only if credentials are set)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    GOOGLE_OAUTH_ENABLED = True
else:
    google = None
    GOOGLE_OAUTH_ENABLED = False


@auth.route("/login", methods=["GET", "POST"])
def login() -> Union[str, Any]:
    """
    Login page handler.

    Returns:
        Rendered login template or redirect response
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # DEBUG: Print DB info
    import os
    logger.info(f"DEBUG: DB URI: {current_app.config['SQLALCHEMY_DATABASE_URI']}")
    logger.info(f"DEBUG: CWD: {os.getcwd()}")
    logger.info(f"DEBUG: DB File Exists (root): {os.path.exists('qunextrade.db')}")
    logger.info(f"DEBUG: DB File Exists (instance): {os.path.exists('instance/qunextrade.db')}")
    try:
        all_users = db.session.execute(db.select(User)).scalars().all()
        logger.info(f"DEBUG: All users in DB: {[u.email for u in all_users]}")
    except Exception as e:
        logger.error(f"DEBUG: Error querying users: {e}")

    if request.method == "POST":
        recaptcha_token = request.form.get("recaptcha_token")
        if not verify_recaptcha(recaptcha_token):
            flash("Security verification failed. Please try again.", "error")
            return redirect(url_for("auth.login"))

        email = request.form.get("email")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False

        print(f"DEBUG: Login attempt for {email}")
        
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        
        if user:
            print(f"DEBUG: User found: {user.username}, ID: {user.id}")
            print(f"DEBUG: Hash in DB: {user.password_hash}")
            is_valid = user.check_password(password)
            print(f"DEBUG: Password valid? {is_valid}")
        else:
            print("DEBUG: User NOT found")

        if not user or not user.check_password(password):
            flash("Invalid email or password", "error")
            return redirect(url_for("auth.login"))

        print(f"DEBUG: User logged in: {user.username}")
        login_user(user, remember=remember)
        next_page = request.args.get("next")
        return redirect(next_page) if next_page else redirect(url_for("main.index"))

    return render_template("login.html", google_oauth_enabled=GOOGLE_OAUTH_ENABLED, csrf_token=generate_csrf())


@auth.route("/signup", methods=["GET", "POST"])
def signup() -> Union[str, Any]:
    """
    Signup page handler.

    Returns:
        Rendered signup template or redirect response
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        recaptcha_token = request.form.get("recaptcha_token")
        if not verify_recaptcha(recaptcha_token):
            flash("Security verification failed. Please try again.", "error")
            return redirect(url_for("auth.signup"))

        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        logger.info(f"Signup attempt - Email: {email}, Username: {username}")

        # Email verification disabled by user request
        # if not session.get("email_verified") or session.get("verified_email") != email:
        #     flash("Please verify your email first", "error")
        #     return redirect(url_for("auth.signup"))

        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if user:
            logger.warning(f"Email already exists: {email}")
            flash("Email already exists", "error")
            return redirect(url_for("auth.signup"))

        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user:
            logger.warning(f"Username already taken: {username}")
            flash("Username already taken", "error")
            return redirect(url_for("auth.signup"))

        new_user = User(
            email=email,
            username=username,
            email_verified=True,
            subscription_tier="free",
            subscription_status="active",
        )
        new_user.set_password(password)

        logger.info(f"Creating new user: {username}")

        db.session.add(new_user)
        db.session.commit()

        logger.info(f"User created successfully: {new_user.id}")

        session.pop("email_verified", None)
        session.pop("verified_email", None)
        session.pop("verification_code", None)
        session.pop("verification_email", None)
        session.pop("verification_expiry", None)

        login_user(new_user)
        flash("Account created successfully!", "success")
        return redirect(url_for("main.index"))

    return render_template("signup.html", csrf_token=generate_csrf())


@auth.route("/logout")
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for("main.index"))





@auth.route("/admin/dashboard")
@login_required
def admin_dashboard():
    """Admin dashboard - only accessible to developer tier users"""
    # Check if user is developer tier (admin)
    if current_user.subscription_tier != "developer":
        flash("Unauthorized access - Admin only", "error")
        return redirect(url_for("main.index"))

    # Get all users
    all_users = db.session.execute(db.select(User).order_by(User.created_at.desc())).scalars().all()

    # Calculate statistics
    total_users = len(all_users)
    free_users = len([u for u in all_users if u.subscription_tier == "free"])
    pro_users = len([u for u in all_users if u.subscription_tier == "pro"])
    premium_users = len([u for u in all_users if u.subscription_tier == "premium"])
    developer_users = len([u for u in all_users if u.subscription_tier == "developer"])

    # Calculate monthly revenue (developer tier is free/internal)
    monthly_revenue = (pro_users * 19.99) + (premium_users * 49.99)

    stats = {
        "total_users": total_users,
        "free_users": free_users,
        "pro_users": pro_users,
        "premium_users": premium_users,
        "developer_users": developer_users,
        "monthly_revenue": monthly_revenue,
    }

    return render_template("admin_dashboard.html", users=all_users, stats=stats)


@auth.route("/admin/upgrade-user/<email>/<tier>", methods=["POST"])
@login_required
def admin_upgrade_user(email, tier):
    """Admin endpoint to upgrade users (use with caution!)"""
    # Security: Require admin password in POST body, NOT query string
    # Query strings are logged in server logs, browser history, and proxy logs
    import os

    # Security: Verify that current user is a developer/admin
    if current_user.subscription_tier != "developer":
        logger.warning(
            f"Unauthorized admin upgrade attempt by user {current_user.email} (tier: {current_user.subscription_tier})"
        )
        return jsonify({"error": "Unauthorized - developer tier required"}), 403

    admin_password = os.getenv("ADMIN_PASSWORD", "change-me-in-production")

    # Get password from POST body (JSON or form data)
    data = request.get_json() or {}
    provided_password = data.get("password") or request.form.get("password")

    # Security: Use constant-time comparison to prevent timing attacks
    if not provided_password or not secrets.compare_digest(
        str(provided_password), str(admin_password)
    ):
        return jsonify({"error": "Unauthorized - admin password required"}), 403

    if tier not in ["free", "pro", "premium", "beta", "developer"]:
        return jsonify({"error": "Invalid tier"}), 400

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if not user:
        return jsonify({"error": "User not found"}), 404

    old_tier = user.subscription_tier
    user.subscription_tier = tier
    user.subscription_status = "active"
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "email": email,
            "username": user.username,
            "old_tier": old_tier,
            "new_tier": tier,
            "status": "active",
        }
    )


@auth.route("/admin/announcement", methods=["GET"])
@login_required
def get_announcements():
    """Get all announcements (admin only)"""
    if current_user.subscription_tier != "developer":
        return jsonify({"error": "Unauthorized"}), 403

    from web.database import Announcement
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return jsonify({"announcements": [a.to_dict() for a in announcements]})


@auth.route("/admin/announcement", methods=["POST"])
@login_required
def create_announcement():
    """Create a new announcement (admin only)"""
    if current_user.subscription_tier != "developer":
        return jsonify({"error": "Unauthorized"}), 403

    from web.database import Announcement

    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message is required"}), 400

    # Deactivate all existing announcements first
    Announcement.query.update({Announcement.is_active: False})

    # Create new announcement
    announcement = Announcement(
        message=message,
        link_text=data.get("link_text"),
        link_url=data.get("link_url"),
        banner_type=data.get("banner_type", "info"),
        is_active=True,
        created_by=current_user.id
    )
    db.session.add(announcement)
    db.session.commit()

    return jsonify({"success": True, "announcement": announcement.to_dict()})


@auth.route("/admin/announcement/<int:id>", methods=["DELETE"])
@login_required
def delete_announcement(id):
    """Delete an announcement (admin only)"""
    if current_user.subscription_tier != "developer":
        return jsonify({"error": "Unauthorized"}), 403

    from web.database import Announcement

    announcement = Announcement.query.get(id)
    if not announcement:
        return jsonify({"error": "Announcement not found"}), 404

    db.session.delete(announcement)
    db.session.commit()

    return jsonify({"success": True})


@auth.route("/admin/announcement/<int:id>/toggle", methods=["POST"])
@login_required
def toggle_announcement(id):
    """Toggle announcement active status (admin only)"""
    if current_user.subscription_tier != "developer":
        return jsonify({"error": "Unauthorized"}), 403

    from web.database import Announcement

    announcement = Announcement.query.get(id)
    if not announcement:
        return jsonify({"error": "Announcement not found"}), 404

    # If activating, deactivate all others first
    if not announcement.is_active:
        Announcement.query.update({Announcement.is_active: False})

    announcement.is_active = not announcement.is_active
    db.session.commit()

    return jsonify({"success": True, "is_active": announcement.is_active})


@auth.route("/api/announcement/active")
def get_active_announcement():
    """Get the currently active announcement (public endpoint)"""
    from web.database import Announcement

    announcement = Announcement.query.filter_by(is_active=True).first()
    if announcement:
        return jsonify(announcement.to_dict())
    return jsonify(None)


@auth.route("/google/login")
def google_login():
    """Initiate Google OAuth login"""
    if not GOOGLE_OAUTH_ENABLED:
        flash("Google login is not configured. Please use email/password login.", "error")
        return redirect(url_for("auth.login"))

    redirect_uri = url_for("auth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@auth.route("/google/callback")
def google_callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_OAUTH_ENABLED:
        flash("Google login is not configured.", "error")
        return redirect(url_for("auth.login"))

    try:
        # Get token from Google
        token = google.authorize_access_token()

        # Get user info from Google
        user_info = token.get("userinfo")

        if not user_info:
            flash("Failed to get user information from Google", "error")
            return redirect(url_for("auth.login"))

        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", "").split()[0]  # First name
        picture = user_info.get("picture")

        # Check if user exists by Google ID
        user = db.session.execute(
            db.select(User).filter_by(google_id=google_id)
        ).scalar_one_or_none()

        if not user:
            # Check if email already exists
            user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()

            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.oauth_provider = "google"
                user.profile_picture = picture
                db.session.commit()
                flash("Google account linked successfully!", "success")
            else:
                # Create new user
                # Generate unique username
                base_username = name.lower().replace(" ", "")
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
                    oauth_provider="google",
                    profile_picture=picture,
                    subscription_tier="free",
                    subscription_status="active",
                )
                # No password needed for OAuth users
                db.session.add(user)
                db.session.commit()
                flash("Account created successfully with Google!", "success")

        # Log in the user
        login_user(user, remember=True)
        return redirect(url_for("main.index"))

    except Exception as e:
        flash(f"Google login failed: {str(e)}", "error")
        return redirect(url_for("auth.login"))


@auth.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """Change user password"""
    # OAuth users don't have passwords
    if not current_user.password_hash:
        flash("OAuth users cannot change password. Please use your Google account.", "error")
        return redirect(url_for("auth.account"))

    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    # Validate current password
    if not current_user.check_password(current_password):
        flash("Current password is incorrect", "error")
        return redirect(url_for("auth.account"))

    # Validate new password
    if len(new_password) < 6:
        flash("New password must be at least 6 characters", "error")
        return redirect(url_for("auth.account"))

    # Validate password match
    if new_password != confirm_password:
        flash("New passwords do not match", "error")
        return redirect(url_for("auth.account"))

    # Update password
    current_user.set_password(new_password)
    db.session.commit()

    flash("Password updated successfully!", "success")
    return redirect(url_for("auth.account"))


@auth.route("/send-verification-code", methods=["POST"])
def send_verification_code():
    """Send 6-digit verification code to email"""
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    # Generate 6-digit code using cryptographically secure random
    # Security: Use secrets module instead of random for security-sensitive tokens
    code = "".join([str(secrets.randbelow(10)) for _ in range(6)])

    # Store code in session temporarily (expires in 10 minutes)
    session["verification_code"] = code
    session["verification_email"] = email
    session["verification_expiry"] = (
        datetime.now(timezone.utc) + timedelta(minutes=10)
    ).isoformat()

    # Send email
    try:
        from web.extensions import mail

        msg = Message("Email Verification Code - Qunex Trade", recipients=[email])
        msg.body = f"""Welcome to Qunex Trade!

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
Qunex Trade Team
"""
        msg.html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background: #f5f7fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f7fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <!-- Main Container -->
                <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); overflow: hidden;">
                    <!-- Header with Gradient -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #00d9ff 0%, #7c3aed 100%); padding: 40px 40px 30px 40px; text-align: center;">
                            <div style="background: rgba(255,255,255,0.2); width: 60px; height: 60px; border-radius: 12px; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 32px; font-weight: 700; color: white;">Q</span>
                            </div>
                            <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Welcome to Qunex Trade</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">Your AI-Powered Trading Platform</p>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px;">
                            <p style="margin: 0 0 24px 0; color: #1a202c; font-size: 16px; line-height: 1.6;">
                                Thank you for joining Qunex Trade! To complete your registration, please use the verification code below:
                            </p>

                            <!-- Code Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center" style="background: linear-gradient(135deg, #f0f9ff 0%, #f3f0ff 100%); border: 2px solid #00d9ff; border-radius: 12px; padding: 24px;">
                                        <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Your Verification Code</p>
                                        <div style="font-size: 42px; font-weight: 700; letter-spacing: 8px; color: #1a202c; font-family: 'Courier New', monospace;">{code}</div>
                                    </td>
                                </tr>
                            </table>

                            <!-- Info Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0; background: #fff8e6; border-left: 4px solid #ffc107; border-radius: 8px; padding: 16px 20px;">
                                <tr>
                                    <td>
                                        <p style="margin: 0; color: #856404; font-size: 14px; line-height: 1.6;">
                                            ⏱️ <strong>Expires in 10 minutes</strong><br/>
                                            This code is valid for a single use only.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 24px 0 0 0; color: #4a5568; font-size: 14px; line-height: 1.6;">
                                If you didn't request this code, you can safely ignore this email. Someone may have entered your email address by mistake.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background: #f8f9fa; padding: 30px 40px; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0 0 12px 0; color: #1a202c; font-size: 14px; font-weight: 600;">
                                Best regards,<br/>
                                <span style="background: linear-gradient(135deg, #00d9ff 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-size: 16px; font-weight: 700;">Qunex Trade Team</span>
                            </p>
                            <p style="margin: 16px 0 0 0; color: #718096; font-size: 12px; line-height: 1.5;">
                                This is an automated message, please do not reply to this email.<br/>
                                © 2025 Qunex Trade. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>

                <!-- Footer Links -->
                <table width="600" cellpadding="0" cellspacing="0" style="margin-top: 20px;">
                    <tr>
                        <td align="center">
                            <p style="margin: 0; color: #718096; font-size: 12px;">
                                <a href="https://qunextrade.com" style="color: #00d9ff; text-decoration: none; margin: 0 8px;">Website</a> •
                                <a href="https://qunextrade.com/about" style="color: #00d9ff; text-decoration: none; margin: 0 8px;">About</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        mail.send(msg)
        return jsonify({"success": True, "message": "Verification code sent!"})
    except Exception as e:
        logger.error(f"Error sending email: {type(e).__name__}: {e}", exc_info=True)

        # Security: NEVER return verification codes in API responses
        # Fail closed - require email service to be working for verification
        # Alternative: Use SMS or other backup delivery method
        logger.critical(f"Email sending failed for {email}. Verification cannot proceed.")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Email service is temporarily unavailable. Please try again later or contact support.",
                    "message": "We're unable to send the verification code at this time.",
                }
            ),
            503,
        )  # Service Unavailable


@auth.route("/verify-code", methods=["POST"])
def verify_code():
    """Verify the 6-digit code"""
    data = request.get_json()
    code = data.get("code")

    if not code:
        return jsonify({"success": False, "message": "Code is required"}), 400

    # Check if code matches and hasn't expired
    stored_code = session.get("verification_code")
    stored_email = session.get("verification_email")
    expiry_str = session.get("verification_expiry")

    if not stored_code or not expiry_str:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No verification code found. Please request a new one.",
                }
            ),
            400,
        )

    expiry = datetime.fromisoformat(expiry_str)
    if datetime.now(timezone.utc) > expiry:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Verification code expired. Please request a new one.",
                }
            ),
            400,
        )

    if code != stored_code:
        return jsonify({"success": False, "message": "Invalid verification code"}), 400

    # Code is valid
    session["email_verified"] = True
    session["verified_email"] = stored_email

    return jsonify({"success": True, "message": "Email verified successfully!"})


@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password page - send reset email"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        # Verify reCAPTCHA
        recaptcha_token = request.form.get("recaptcha_token")
        if not verify_recaptcha(recaptcha_token):
            flash("Security verification failed. Please try again.", "error")
            return redirect(url_for("auth.forgot_password"))

        email = request.form.get("email")

        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()

        # Always show success message (security: don't reveal if email exists)
        flash("If an account with that email exists, a password reset link has been sent.", "info")

        if user and user.password_hash:  # Only send if user exists and has password (not OAuth)
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(
                hours=1
            )  # 1 hour expiry
            db.session.commit()

            # Send reset email
            try:
                from web.extensions import mail

                reset_url = url_for("auth.reset_password", token=token, _external=True)

                msg = Message("Password Reset Request - Qunex Trade", recipients=[user.email])
                msg.body = f"""Hello {user.username},

You requested a password reset for your Qunex Trade account.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you didn't request this, please ignore this email. Your password will remain unchanged.

Best regards,
Qunex Trade Team
"""
                msg.html = f"""
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
"""
                mail.send(msg)
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}", exc_info=True)

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html", csrf_token=generate_csrf())


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # Find user with this token
    user = db.session.execute(db.select(User).filter_by(reset_token=token)).scalar_one_or_none()

    # Check if token is valid and not expired
    if (
        not user
        or not user.reset_token_expiry
        or user.reset_token_expiry < datetime.now(timezone.utc)
    ):
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validate password
        if len(new_password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template("reset_password.html", token=token, csrf_token=generate_csrf())

        if new_password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("reset_password.html", token=token, csrf_token=generate_csrf())

        # Update password and clear reset token
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash("Password reset successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token, csrf_token=generate_csrf())

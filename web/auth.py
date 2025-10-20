"""
Authentication routes and utilities
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

try:
    from database import db, User
except ImportError:
    from web.database import db, User

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
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

    return render_template('login.html')


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        print(f"[DEBUG] Signup attempt - Email: {email}, Username: {username}")

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
            subscription_tier='free',
            subscription_status='active'
        )
        new_user.set_password(password)

        print(f"[DEBUG] Creating new user: {username}")

        db.session.add(new_user)
        db.session.commit()

        print(f"[DEBUG] User created successfully: {new_user.id}")

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
    """Admin dashboard - only accessible to admin users"""
    import os

    # Check if user is admin (you can add is_admin field to User model later)
    # For now, check if email is the admin email
    admin_email = os.getenv('ADMIN_EMAIL', 'kwangui2@illinois.edu')

    if current_user.email != admin_email:
        flash('Unauthorized access', 'error')
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

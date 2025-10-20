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

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))

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

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', 'error')
            return redirect(url_for('auth.signup'))

        user = User.query.filter_by(username=username).first()
        if user:
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

        db.session.add(new_user)
        db.session.commit()

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


@auth.route('/admin/upgrade-user/<email>/<tier>')
def admin_upgrade_user(email, tier):
    """Admin endpoint to upgrade users (use with caution!)"""
    # Simple security: require admin password in query param
    import os
    admin_password = os.getenv('ADMIN_PASSWORD', 'change-me-in-production')

    if request.args.get('password') != admin_password:
        return jsonify({'error': 'Unauthorized'}), 403

    if tier not in ['free', 'pro', 'premium']:
        return jsonify({'error': 'Invalid tier'}), 400

    user = User.query.filter_by(email=email).first()
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

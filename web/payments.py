"""
Payment processing with Stripe
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
import os

try:
    from database import db, Payment
except ImportError:
    from web.database import db, Payment

payments = Blueprint("payments", __name__)

# Stripe configuration (will be set via environment variables)
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_YOUR_KEY_HERE")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_YOUR_KEY_HERE")

# Pricing
PRICING = {
    "pro": {
        "name": "Pro",
        "price": 19.99,
        "monthly_price": 1999,  # in cents
        "features": [
            "Unlimited signals",
            "30-day history",
            "Email alerts",
            "CSV downloads",
            "Priority support",
        ],
    },
    "premium": {
        "name": "Premium",
        "price": 49.99,
        "monthly_price": 4999,  # in cents
        "features": [
            "All Pro features",
            "API access",
            "Telegram bot",
            "Real-time alerts",
            "Custom thresholds",
            "Dedicated support",
        ],
    },
}





@payments.route("/subscribe/<tier>")
@login_required
def subscribe(tier):
    """Subscribe to a tier"""
    if tier not in ["pro", "premium"]:
        flash("Invalid subscription tier", "error")
        return redirect(url_for("payments.pricing"))

    # Check if already subscribed
    if current_user.is_pro() or current_user.is_premium():
        flash("You already have an active subscription", "info")
        return redirect(url_for("auth.account"))

    return render_template(
        "checkout.html", tier=tier, pricing=PRICING[tier], stripe_public_key=STRIPE_PUBLIC_KEY
    )


@payments.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    """Create Stripe checkout session"""
    tier = request.form.get("tier")

    if tier not in ["pro", "premium"]:
        return jsonify({"error": "Invalid tier"}), 400

    try:
        # In production, use Stripe API to create checkout session
        # For now, simulate successful subscription

        # Update user subscription
        current_user.subscription_tier = tier
        current_user.subscription_status = "active"
        current_user.subscription_start = datetime.now(timezone.utc)
        current_user.subscription_end = datetime.now(timezone.utc) + timedelta(days=30)

        db.session.commit()

        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            amount=PRICING[tier]["price"],
            currency="USD",
            status="succeeded",
        )
        db.session.add(payment)
        db.session.commit()

        return jsonify({"success": True, "redirect": url_for("auth.account")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payments.route("/cancel-subscription", methods=["POST"])
@login_required
def cancel_subscription():
    """Cancel subscription"""
    if not current_user.is_pro() and not current_user.is_premium():
        flash("No active subscription to cancel", "error")
        return redirect(url_for("auth.account"))

    try:
        # In production, cancel via Stripe API
        current_user.subscription_status = "cancelled"
        db.session.commit()

        flash("Subscription cancelled successfully", "success")
        return redirect(url_for("auth.account"))

    except Exception as e:
        flash(f"Error cancelling subscription: {str(e)}", "error")
        return redirect(url_for("auth.account"))


@payments.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhooks"""
    # In production, verify webhook signature and process events
    # For now, just return success
    return jsonify({"status": "success"})

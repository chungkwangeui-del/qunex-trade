#!/usr/bin/env python3
"""
Render Cron Job: Check Price Alerts

This script checks if stock prices have hit user-defined alert thresholds.
Runs every 5 minutes to monitor watchlist stocks and trigger notifications.

Features:
- Fetches current prices from Polygon API
- Compares against user alert thresholds
- Sends email notifications when alerts trigger
- Updates alert status in database
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from datetime import timezone

# Add parent directory and web directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_price_alerts():
    """
    Check if any stock prices have hit user alert thresholds.

    Fetches current prices for all stocks with active alerts,
    compares against thresholds, and sends notifications when triggered.

    Returns:
        bool: True if check succeeded, False otherwise

    Side Effects:
        - Updates PriceAlert records in database
        - Sends email notifications via Flask-Mail
        - Logs all alert checks and triggers
    """
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        from flask_mail import Mail, Message

        logger.info("Starting price alert check...")

        # CRITICAL: Validate required API keys
        polygon_key = os.getenv("POLYGON_API_KEY")
        if not polygon_key or polygon_key.strip() == "":
            logger.critical("CRITICAL ERROR: POLYGON_API_KEY is missing. Cannot fetch prices.")
            return False

        # Get DATABASE_URL and fix driver
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.critical("CRITICAL ERROR: DATABASE_URL is missing.")
            return False

        # Fix psycopg2 driver issue
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://")

        # Create minimal Flask app
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Mail configuration
        app.config["MAIL_SERVER"] = "smtp.gmail.com"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_USE_TLS"] = True
        app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
        app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
        app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

        db = SQLAlchemy(app)
        mail = Mail(app)

        # Import models and services after db is created
        from database import PriceAlert, User
        from polygon_service import PolygonService

        polygon = PolygonService()

        with app.app_context():
            # Get all active price alerts
            active_alerts = PriceAlert.query.filter_by(is_triggered=False).all()

            if not active_alerts:
                logger.info("No active alerts to check")
                return True

            logger.info(f"Checking {len(active_alerts)} active alerts")

            # Group alerts by ticker to minimize API calls
            ticker_alerts = {}
            for alert in active_alerts:
                if alert.ticker not in ticker_alerts:
                    ticker_alerts[alert.ticker] = []
                ticker_alerts[alert.ticker].append(alert)

            triggered_count = 0

            # Check each ticker (with rate limiting)
            for ticker, alerts in ticker_alerts.items():
                try:
                    # Fetch current price from Polygon
                    logger.debug(f"Fetching price for {ticker}")
                    ticker_data = polygon.get_ticker_details(ticker)

                    if not ticker_data or "results" not in ticker_data:
                        logger.warning(f"No price data for {ticker}")
                        continue

                    # Get previous close as current price proxy
                    current_price = ticker_data["results"].get("prevClose")
                    if not current_price:
                        logger.warning(f"No price found for {ticker}")
                        continue

                    current_price = Decimal(str(current_price))
                    logger.debug(f"{ticker} current price: ${current_price}")

                    # Check each alert for this ticker
                    for alert in alerts:
                        triggered = False

                        # Check threshold based on condition
                        if alert.condition == "above" and current_price >= alert.threshold:
                            triggered = True
                        elif alert.condition == "below" and current_price <= alert.threshold:
                            triggered = True

                        if triggered:
                            logger.info(
                                f"ALERT TRIGGERED: {ticker} {alert.condition} "
                                f"${alert.threshold} (current: ${current_price})"
                            )

                            # Update alert status
                            alert.is_triggered = True
                            alert.triggered_at = datetime.now(timezone.utc)
                            alert.triggered_price = float(current_price)

                            # Send email notification
                            try:
                                user = User.query.get(alert.user_id)
                                if user and user.email:
                                    msg = Message(
                                        subject=f"Price Alert: {ticker}",
                                        recipients=[user.email],
                                        body=f"""
Your price alert for {ticker} has been triggered!

Alert Condition: {alert.condition.upper()} ${alert.threshold}
Current Price: ${current_price}
Triggered At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

View your watchlist: https://qunextrade.com/dashboard

---
QUNEX Trade - Smart Trading Platform
                                        """.strip(),
                                    )
                                    mail.send(msg)
                                    logger.info(f"Email sent to {user.email}")
                            except Exception as e:
                                logger.error(f"Failed to send email: {e}")

                            triggered_count += 1

                    # Rate limiting: 5 requests per second max
                    time.sleep(0.2)

                except Exception as e:
                    logger.error(f"Error checking {ticker}: {e}")
                    continue

            # Commit all changes
            db.session.commit()
            logger.info(f"Alert check complete. Triggered: {triggered_count}")
            return True

    except Exception as e:
        logger.critical(f"CRITICAL ERROR in price alert check: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = check_price_alerts()
    sys.exit(0 if success else 1)

"""
Watchlist API endpoints
Manage user stock watchlists with real-time data
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.database import db, Watchlist
from web.polygon_service import get_polygon_service
from web.extensions import csrf
from werkzeug.exceptions import BadRequest
from datetime import datetime
from typing import Dict, Any, Tuple
import logging
import re

logger = logging.getLogger(__name__)

api_watchlist = Blueprint("api_watchlist", __name__)

# Exempt API routes from CSRF for JavaScript fetch calls
csrf.exempt(api_watchlist)


@api_watchlist.route("/api/watchlist", methods=["GET"])
@login_required
def get_watchlist() -> Tuple[Any, int]:
    """
    Get user's watchlist with real-time quotes.

    Returns:
        JSON array of watchlist items with real-time data
    """
    try:
        watchlist_items = (
            Watchlist.query.filter_by(user_id=current_user.id)
            .order_by(Watchlist.added_at.desc())
            .all()
        )

        if not watchlist_items:
            return jsonify([])

        polygon = get_polygon_service()
        results = []

        # Get all tickers for bulk snapshot
        tickers = [item.ticker for item in watchlist_items]
        bulk_snapshots = polygon.get_market_snapshot(tickers)

        for item in watchlist_items:
            stock_data = {
                "id": item.id,
                "ticker": item.ticker,
                "company_name": item.company_name,
                "notes": item.notes,
                "added_at": item.added_at.isoformat(),
                "alert_price_above": item.alert_price_above,
                "alert_price_below": item.alert_price_below,
            }

            # Use bulk snapshot data (more accurate change data)
            snapshot = bulk_snapshots.get(item.ticker)

            # Check if snapshot has actual data (not just empty dict)
            if snapshot and (snapshot.get("price") or snapshot.get("prev_close")):
                # Use prev_close as fallback when market is closed
                price = (
                    snapshot.get("price") or
                    snapshot.get("day_close") or
                    snapshot.get("prev_close") or
                    0
                )
                stock_data.update(
                    {
                        "price": price,
                        "change": snapshot.get("change", 0) or 0,
                        "change_percent": snapshot.get("change_percent", 0) or 0,
                        "volume": snapshot.get("day_volume") or snapshot.get("prev_volume") or 0,
                        "high": snapshot.get("day_high") or snapshot.get("prev_high"),
                        "low": snapshot.get("day_low") or snapshot.get("prev_low"),
                        "open": snapshot.get("day_open") or snapshot.get("prev_open"),
                        "prev_close": snapshot.get("prev_close"),
                    }
                )
            else:
                # Fallback to individual API calls if not in bulk snapshot
                snapshot_single = polygon.get_snapshot(item.ticker)
                if snapshot_single and (snapshot_single.get("price") or snapshot_single.get("prevDay", {}).get("c")):
                    prev_close = snapshot_single.get("prevDay", {}).get("c", 0)
                    price = snapshot_single.get("price") or prev_close or 0
                    stock_data.update(
                        {
                            "price": price,
                            "change": snapshot_single.get("todaysChange", 0) or 0,
                            "change_percent": snapshot_single.get("todaysChangePerc", 0) or 0,
                            "volume": snapshot_single.get("day", {}).get("v") or snapshot_single.get("prevDay", {}).get("v", 0),
                            "high": snapshot_single.get("day", {}).get("h") or snapshot_single.get("prevDay", {}).get("h"),
                            "low": snapshot_single.get("day", {}).get("l") or snapshot_single.get("prevDay", {}).get("l"),
                            "open": snapshot_single.get("day", {}).get("o") or snapshot_single.get("prevDay", {}).get("o"),
                            "prev_close": prev_close,
                        }
                    )
                else:
                    # Last resort fallback
                    prev_data = polygon.get_previous_close(item.ticker)
                    if prev_data:
                        stock_data.update(
                            {
                                "price": prev_data.get("close", 0),
                                "change": 0,
                                "change_percent": 0,
                                "volume": prev_data.get("volume", 0),
                                "high": prev_data.get("high"),
                                "low": prev_data.get("low"),
                                "open": prev_data.get("open"),
                                "prev_close": prev_data.get("close"),
                            }
                        )
                    else:
                        stock_data.update(
                            {
                                "price": 0,
                                "change": 0,
                                "change_percent": 0,
                                "volume": 0,
                                "error": "Quote data unavailable",
                            }
                        )

            results.append(stock_data)

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_watchlist.route("/api/watchlist", methods=["POST"])
@login_required
def add_to_watchlist():
    """Add a stock to watchlist"""
    try:
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify({"error": "Invalid JSON data"}), 400

        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400
        ticker = data.get("ticker", "").upper().strip()

        if not ticker:
            return jsonify({"error": "Ticker is required"}), 400

        # Validate ticker format: 1-5 uppercase letters only
        # Security: Prevent SQL injection and XSS through ticker input
        if not re.match(r"^[A-Z]{1,5}$", ticker):
            return (
                jsonify(
                    {
                        "error": "Invalid ticker format. Ticker must be 1-5 uppercase letters only.",
                        "example": "Valid tickers: AAPL, TSLA, GOOGL",
                    }
                ),
                400,
            )

        # Check if already in watchlist
        existing = Watchlist.query.filter_by(user_id=current_user.id, ticker=ticker).first()
        if existing:
            return jsonify({"error": "Stock already in watchlist"}), 400

        # Get company name (use ticker as fallback)
        company_name = data.get("company_name", ticker)

        # Create watchlist entry
        watchlist_item = Watchlist(
            user_id=current_user.id,
            ticker=ticker,
            company_name=company_name,
            notes=data.get("notes", ""),
            alert_price_above=data.get("alert_price_above"),
            alert_price_below=data.get("alert_price_below"),
        )

        db.session.add(watchlist_item)
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"{ticker} added to watchlist",
                    "id": watchlist_item.id,
                    "ticker": ticker,
                    "company_name": company_name,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding to watchlist: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_watchlist.route("/api/watchlist/<int:item_id>", methods=["DELETE"])
@login_required
def remove_from_watchlist(item_id):
    """Remove a stock from watchlist"""
    try:
        item = Watchlist.query.filter_by(id=item_id, user_id=current_user.id).first()

        if not item:
            return jsonify({"error": "Watchlist item not found"}), 404

        ticker = item.ticker
        db.session.delete(item)
        db.session.commit()

        return jsonify({"success": True, "message": f"{ticker} removed from watchlist"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing from watchlist: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_watchlist.route("/api/watchlist/<int:item_id>", methods=["PUT"])
@login_required
def update_watchlist_item(item_id):
    """Update watchlist item (notes, alerts)"""
    try:
        item = Watchlist.query.filter_by(id=item_id, user_id=current_user.id).first()

        if not item:
            return jsonify({"error": "Watchlist item not found"}), 404

        data = request.get_json()

        # Update allowed fields
        if "notes" in data:
            item.notes = data["notes"]
        if "alert_price_above" in data:
            item.alert_price_above = data["alert_price_above"]
        if "alert_price_below" in data:
            item.alert_price_below = data["alert_price_below"]

        db.session.commit()

        return jsonify(
            {"success": True, "message": "Watchlist item updated", "ticker": item.ticker}
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating watchlist item: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_watchlist.route("/api/watchlist/stats", methods=["GET"])
@login_required
def get_watchlist_stats():
    """Get watchlist statistics (total P/L, best/worst performers)"""
    try:
        watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()

        if not watchlist_items:
            return jsonify(
                {
                    "total_stocks": 0,
                    "gainers": 0,
                    "losers": 0,
                    "best_performer": None,
                    "worst_performer": None,
                }
            )

        polygon = get_polygon_service()

        # Get all tickers for bulk snapshot
        tickers = [item.ticker for item in watchlist_items]
        bulk_snapshots = polygon.get_market_snapshot(tickers)

        gainers = 0
        losers = 0
        best_performer = None
        worst_performer = None
        best_change = float("-inf")
        worst_change = float("inf")

        for item in watchlist_items:
            snapshot = bulk_snapshots.get(item.ticker, {})

            if snapshot:
                current_price = snapshot.get("price") or snapshot.get("day_close") or 0
                change_pct = snapshot.get("change_percent", 0) or 0

                if change_pct > 0:
                    gainers += 1
                elif change_pct < 0:
                    losers += 1

                if change_pct > best_change:
                    best_change = change_pct
                    best_performer = {
                        "ticker": item.ticker,
                        "change_percent": round(change_pct, 2),
                        "price": current_price,
                    }

                if change_pct < worst_change:
                    worst_change = change_pct
                    worst_performer = {
                        "ticker": item.ticker,
                        "change_percent": round(change_pct, 2),
                        "price": current_price,
                    }

        return jsonify(
            {
                "total_stocks": len(watchlist_items),
                "gainers": gainers,
                "losers": losers,
                "neutral": len(watchlist_items) - gainers - losers,
                "best_performer": best_performer,
                "worst_performer": worst_performer,
            }
        )

    except Exception as e:
        logger.error(f"Error getting watchlist stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

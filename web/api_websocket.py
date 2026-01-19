"""
WebSocket API for Real-Time Price Streaming

Features:
- Real-time stock price updates
- WebSocket-like polling fallback for serverless environments
- Price change notifications
- Watchlist live updates
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.extensions import csrf, cache
from web.database import db, Watchlist
from web.polygon_service import get_polygon_service
import os
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List
import threading
import time

logger = logging.getLogger(__name__)

api_websocket = Blueprint("api_websocket", __name__)
csrf.exempt(api_websocket)


class PriceStreamManager:
    """Manages real-time price streaming with polling fallback"""

    def __init__(self):
        self.polygon = get_polygon_service()
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 5  # 5 seconds cache

    def get_live_prices(self, tickers: List[str]) -> Dict:
        """Get live prices for multiple tickers with caching"""
        if not tickers:
            return {}

        now = time.time()
        results = {}
        tickers_to_fetch = []

        # Check cache first
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker in self._cache and (now - self._cache_time.get(ticker, 0)) < self._cache_ttl:
                results[ticker] = self._cache[ticker]
            else:
                tickers_to_fetch.append(ticker)

        # Fetch missing tickers
        if tickers_to_fetch:
            try:
                snapshots = self.polygon.get_market_snapshot(tickers_to_fetch)
                
                for ticker in tickers_to_fetch:
                    data = snapshots.get(ticker, {})
                    if data:
                        price_data = {
                            "ticker": ticker,
                            "price": data.get("price"),
                            "change": data.get("change"),
                            "change_percent": data.get("change_percent"),
                            "volume": data.get("volume"),
                            "high": data.get("high"),
                            "low": data.get("low"),
                            "open": data.get("open"),
                            "prev_close": data.get("prev_close"),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Update cache
                        self._cache[ticker] = price_data
                        self._cache_time[ticker] = now
                        results[ticker] = price_data
                    else:
                        results[ticker] = {"ticker": ticker, "error": "No data"}
                        
            except Exception as e:
                logger.error(f"Price fetch error: {e}")
                for ticker in tickers_to_fetch:
                    results[ticker] = {"ticker": ticker, "error": str(e)}

        return results

    def get_price_changes(self, tickers: List[str], last_prices: Dict) -> List[Dict]:
        """Compare current prices with last known prices and return changes"""
        current_prices = self.get_live_prices(tickers)
        changes = []

        for ticker, current in current_prices.items():
            if current.get("error"):
                continue
                
            last = last_prices.get(ticker, {})
            last_price = last.get("price")
            current_price = current.get("price")

            if last_price and current_price and last_price != current_price:
                price_change = current_price - last_price
                change_pct = (price_change / last_price) * 100

                changes.append({
                    "ticker": ticker,
                    "old_price": last_price,
                    "new_price": current_price,
                    "change": price_change,
                    "change_pct": round(change_pct, 4),
                    "direction": "up" if price_change > 0 else "down",
                    "timestamp": current.get("timestamp")
                })

        return changes


# Initialize manager
price_manager = PriceStreamManager()


@api_websocket.route("/api/realtime/prices", methods=["POST"])
def get_realtime_prices():
    """
    Get real-time prices for multiple tickers
    
    Request body:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "last_prices": {"AAPL": {"price": 150.00}, ...}  // Optional for change detection
    }
    """
    data = request.get_json()
    
    if not data or not data.get("tickers"):
        return jsonify({"error": "Tickers required"}), 400

    tickers = data.get("tickers", [])
    if len(tickers) > 50:
        tickers = tickers[:50]  # Limit to 50 tickers

    # Clean tickers
    tickers = [t.upper().strip() for t in tickers if t and len(t) <= 10]

    prices = price_manager.get_live_prices(tickers)
    
    # Check for changes if last_prices provided
    changes = []
    if data.get("last_prices"):
        changes = price_manager.get_price_changes(tickers, data["last_prices"])

    return jsonify({
        "success": True,
        "prices": prices,
        "changes": changes,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@api_websocket.route("/api/realtime/watchlist")
@login_required
def get_watchlist_realtime():
    """Get real-time prices for user's watchlist"""
    watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    if not watchlist:
        return jsonify({
            "success": True,
            "prices": {},
            "tickers": [],
            "message": "Watchlist is empty"
        })

    tickers = [w.ticker for w in watchlist]
    prices = price_manager.get_live_prices(tickers)

    return jsonify({
        "success": True,
        "prices": prices,
        "tickers": tickers,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@api_websocket.route("/api/realtime/stream/<ticker>")
def stream_ticker(ticker: str):
    """
    Get streaming data for a single ticker
    Includes price, volume, and technical indicators
    """
    ticker = ticker.upper().strip()
    
    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker"}), 400

    prices = price_manager.get_live_prices([ticker])
    price_data = prices.get(ticker, {})

    if price_data.get("error"):
        return jsonify({"error": price_data.get("error")}), 404

    # Add additional stream data
    polygon = get_polygon_service()
    
    # Get intraday data for mini chart
    try:
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        aggs = polygon.get_aggregates(
            ticker, 5, "minute",
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            limit=78  # ~6.5 hours of 5-min bars
        )

        # Extract mini chart data
        mini_chart = []
        if aggs:
            for bar in aggs[-30:]:  # Last 30 bars
                mini_chart.append({
                    "t": bar.get("t"),
                    "c": bar.get("c"),
                    "v": bar.get("v")
                })

        price_data["mini_chart"] = mini_chart
        
    except Exception as e:
        logger.warning(f"Mini chart error for {ticker}: {e}")
        price_data["mini_chart"] = []

    return jsonify({
        "success": True,
        "data": price_data
    })


@api_websocket.route("/api/realtime/market-pulse")
@cache.cached(timeout=15)
def market_pulse():
    """
    Get overall market pulse - indices and key metrics
    Used for header/sidebar market status display
    """
    # Key market indices
    indices = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
    prices = price_manager.get_live_prices(indices)

    # Determine market status
    now = datetime.now()
    # Simple market hours check (9:30 AM - 4:00 PM ET)
    # Note: This doesn't account for holidays
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    if weekday >= 5:  # Weekend
        market_status = "closed"
        status_message = "Market Closed (Weekend)"
    elif hour < 9 or (hour == 9 and minute < 30):
        market_status = "pre-market"
        status_message = "Pre-Market"
    elif hour >= 16:
        market_status = "after-hours"
        status_message = "After Hours"
    else:
        market_status = "open"
        status_message = "Market Open"

    # Calculate market sentiment based on SPY
    spy_data = prices.get("SPY", {})
    spy_change = spy_data.get("change_percent", 0) or 0
    
    if spy_change > 1:
        sentiment = "bullish"
    elif spy_change > 0:
        sentiment = "slightly_bullish"
    elif spy_change > -1:
        sentiment = "slightly_bearish"
    else:
        sentiment = "bearish"

    return jsonify({
        "success": True,
        "market_status": market_status,
        "status_message": status_message,
        "sentiment": sentiment,
        "indices": prices,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@api_websocket.route("/api/realtime/subscribe", methods=["POST"])
@login_required
def subscribe_to_tickers():
    """
    Subscribe to price updates for specific tickers
    Returns subscription ID for polling
    """
    data = request.get_json()
    tickers = data.get("tickers", [])

    if not tickers:
        return jsonify({"error": "Tickers required"}), 400

    # Clean and validate tickers
    tickers = [t.upper().strip() for t in tickers if t and len(t) <= 10][:20]

    # Generate subscription ID
    import hashlib
    sub_id = hashlib.md5(f"{current_user.id}:{','.join(sorted(tickers))}:{time.time()}".encode()).hexdigest()[:16]

    return jsonify({
        "success": True,
        "subscription_id": sub_id,
        "tickers": tickers,
        "poll_interval_ms": 5000,  # Recommend 5 second polling
        "message": "Use /api/realtime/prices with POST to get updates"
    })


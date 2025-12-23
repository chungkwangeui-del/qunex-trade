"""
Chart Pattern Recognition API

Detects and returns chart patterns for stocks.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from datetime import datetime, timedelta
import logging

try:
    from web.polygon_service import get_polygon_service
    from web.pattern_recognition import detect_all_patterns, get_pattern_summary
    from web.extensions import cache
except ImportError:
    from polygon_service import get_polygon_service
    from pattern_recognition import detect_all_patterns, get_pattern_summary
    from extensions import cache

logger = logging.getLogger(__name__)

api_patterns = Blueprint("api_patterns", __name__)


@api_patterns.route("/api/patterns/<ticker>")
@login_required
def get_patterns(ticker):
    """
    Detect chart patterns for a stock.
    
    Query params:
        timeframe: str - 'D' (daily), '4H', '1H' (default: 'D')
        days: int - Number of days to analyze (default: 60)
    """
    ticker = ticker.upper()
    timeframe = request.args.get("timeframe", "D")
    days = min(int(request.args.get("days", 60)), 365)
    
    polygon = get_polygon_service()
    
    # Map timeframe to Polygon parameters
    timeframe_map = {
        "D": ("day", 1),
        "4H": ("hour", 4),
        "1H": ("hour", 1),
    }
    
    if timeframe not in timeframe_map:
        return jsonify({"error": "Invalid timeframe. Use 'D', '4H', or '1H'"}), 400
    
    timespan, multiplier = timeframe_map[timeframe]
    
    # Get historical data
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
    
    bars = polygon.get_aggregates(
        ticker,
        multiplier=multiplier,
        timespan=timespan,
        from_date=from_date,
        to_date=to_date,
        limit=500
    )
    
    if not bars or len(bars) < 20:
        return jsonify({
            "ticker": ticker,
            "timeframe": timeframe,
            "patterns": [],
            "message": "Insufficient data for pattern detection",
        })
    
    # Convert to expected format
    candles = []
    for bar in bars:
        candles.append({
            "o": bar.get("open"),
            "h": bar.get("high"),
            "l": bar.get("low"),
            "c": bar.get("close"),
            "v": bar.get("volume"),
            "t": bar.get("timestamp"),
        })
    
    # Detect patterns
    patterns = detect_all_patterns(candles)
    summary = get_pattern_summary(patterns)
    
    # Get current price for context
    quote = polygon.get_stock_quote(ticker)
    current_price = quote.get("price") if quote else None
    
    return jsonify({
        "ticker": ticker,
        "timeframe": timeframe,
        "current_price": current_price,
        "bars_analyzed": len(candles),
        "patterns": patterns,
        "summary": summary,
        "timestamp": datetime.now().isoformat(),
    })


@api_patterns.route("/api/patterns/scan")
@login_required
@cache.cached(timeout=600, key_prefix="pattern_scan")
def scan_patterns():
    """
    Scan multiple stocks for chart patterns.
    
    Query params:
        tickers: str - Comma-separated tickers (optional, defaults to popular stocks)
        timeframe: str - 'D', '4H', '1H' (default: 'D')
    """
    tickers_str = request.args.get("tickers", "")
    timeframe = request.args.get("timeframe", "D")
    
    if tickers_str:
        tickers = [t.strip().upper() for t in tickers_str.split(",")][:20]  # Max 20
    else:
        # Default watchlist
        tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "AMD", "NFLX", "BA", "DIS", "JPM", "V", "MA", "CRM"
        ]
    
    polygon = get_polygon_service()
    
    timeframe_map = {
        "D": ("day", 1, 60),
        "4H": ("hour", 4, 30),
        "1H": ("hour", 1, 14),
    }
    
    if timeframe not in timeframe_map:
        timeframe = "D"
    
    timespan, multiplier, days = timeframe_map[timeframe]
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
    
    results = []
    
    for ticker in tickers:
        try:
            bars = polygon.get_aggregates(
                ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_date=from_date,
                to_date=to_date,
                limit=200
            )
            
            if not bars or len(bars) < 20:
                continue
            
            candles = [{"o": b.get("open"), "h": b.get("high"), 
                       "l": b.get("low"), "c": b.get("close")} for b in bars]
            
            patterns = detect_all_patterns(candles)
            
            if patterns:
                quote = polygon.get_stock_quote(ticker)
                
                results.append({
                    "ticker": ticker,
                    "current_price": quote.get("price") if quote else None,
                    "patterns": patterns,
                    "pattern_count": len(patterns),
                    "highest_confidence": max(p.get("confidence", 0) for p in patterns),
                    "primary_pattern": patterns[0] if patterns else None,
                })
                
        except Exception as e:
            logger.debug(f"Error scanning {ticker}: {e}")
            continue
    
    # Sort by highest confidence pattern
    results.sort(key=lambda x: x["highest_confidence"], reverse=True)
    
    # Summary
    bullish = sum(1 for r in results if r["primary_pattern"] and r["primary_pattern"].get("direction") == "bullish")
    bearish = sum(1 for r in results if r["primary_pattern"] and r["primary_pattern"].get("direction") == "bearish")
    
    return jsonify({
        "timeframe": timeframe,
        "stocks_scanned": len(tickers),
        "patterns_found": len(results),
        "bullish_patterns": bullish,
        "bearish_patterns": bearish,
        "results": results,
        "timestamp": datetime.now().isoformat(),
    })


@api_patterns.route("/api/patterns/alerts")
@login_required
def get_pattern_alerts():
    """
    Get pattern alerts for user's watchlist stocks.
    
    Checks for recently confirmed patterns.
    """
    try:
        from web.database import Watchlist
    except ImportError:
        return jsonify({"error": "Database not available"}), 500
    
    from flask_login import current_user
    
    # Get user's watchlist
    watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    if not watchlist:
        return jsonify({
            "message": "No stocks in watchlist",
            "alerts": [],
        })
    
    tickers = [w.ticker for w in watchlist][:20]  # Max 20
    
    polygon = get_polygon_service()
    alerts = []
    
    from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
    
    for ticker in tickers:
        try:
            bars = polygon.get_aggregates(
                ticker,
                multiplier=1,
                timespan="day",
                from_date=from_date,
                to_date=to_date,
                limit=100
            )
            
            if not bars or len(bars) < 20:
                continue
            
            candles = [{"o": b.get("open"), "h": b.get("high"),
                       "l": b.get("low"), "c": b.get("close")} for b in bars]
            
            patterns = detect_all_patterns(candles)
            
            # Filter for high-confidence or confirmed patterns
            for pattern in patterns:
                if pattern.get("confidence", 0) >= 65 or pattern.get("status") == "triggered":
                    quote = polygon.get_stock_quote(ticker)
                    
                    alerts.append({
                        "ticker": ticker,
                        "current_price": quote.get("price") if quote else None,
                        "pattern": pattern,
                        "priority": "high" if pattern.get("status") == "triggered" else "medium",
                    })
                    
        except Exception as e:
            logger.debug(f"Error checking {ticker}: {e}")
            continue
    
    # Sort by priority and confidence
    alerts.sort(key=lambda x: (
        x["priority"] == "high",
        x["pattern"].get("confidence", 0)
    ), reverse=True)
    
    return jsonify({
        "watchlist_count": len(tickers),
        "alerts": alerts[:10],  # Top 10 alerts
        "timestamp": datetime.now().isoformat(),
    })


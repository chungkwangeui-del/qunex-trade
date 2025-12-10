"""
ICT/SMC Swing Trading API
Professional swing trading signals using Inner Circle Trader methodology

Key Concepts:
- Market Structure (BOS, CHoCH)
- Liquidity (BSL, SSL, Sweeps)
- Order Blocks & Breaker Blocks
- Fair Value Gaps (FVG)
- Premium/Discount & OTE Zones
- Kill Zones

Supported Markets:
- US Stocks via Polygon.io API
- Crypto via Binance API
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import re
from web.polygon_service import PolygonService
from web.swing_service import generate_swing_signal

logger = logging.getLogger(__name__)

api_swing = Blueprint("api_swing", __name__)


# =============================================================================
# CRYPTO DETECTION
# =============================================================================

def is_crypto_ticker(ticker: str) -> bool:
    """Check if ticker is a cryptocurrency pair"""
    crypto_patterns = [
        r'^[A-Z]{2,10}USDT$',  # BTCUSDT, ETHUSDT
        r'^[A-Z]{2,10}USD$',   # BTCUSD
        r'^[A-Z]{2,10}BUSD$',  # BTCBUSD
        r'^[A-Z]{2,10}BTC$',   # ETHBTC
        r'^[A-Z]{2,10}ETH$',   # LINKETH
    ]
    ticker_upper = ticker.upper()
    return any(re.match(pattern, ticker_upper) for pattern in crypto_patterns)


# =============================================================================
# DATA FETCHING
# =============================================================================

def fetch_binance_candles(symbol: str, interval: str = "4h", limit: int = 100) -> List[Dict]:
    """
    Fetch candle data from Binance API for crypto.

    Intervals: 1h, 4h, 1d, 1w
    """
    interval_map = {
        "1H": "1h",
        "4H": "4h",
        "1D": "1d",
        "1W": "1w",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
        "1w": "1w",
    }

    binance_interval = interval_map.get(interval, "4h")

    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": binance_interval,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        candles = []
        for kline in data:
            candles.append({
                "t": int(kline[0]),
                "o": float(kline[1]),
                "h": float(kline[2]),
                "l": float(kline[3]),
                "c": float(kline[4]),
                "v": float(kline[5]),
            })

        return candles
    except Exception as e:
        logger.error(f"Binance API error for {symbol}: {e}")
        return []


def fetch_polygon_candles(ticker: str, timeframe: str = "4H", limit: int = 100) -> List[Dict]:
    """
    Fetch candle data from Polygon.io for stocks.

    Timeframes: 1H, 4H, 1D
    """
    polygon = PolygonService()

    # Map timeframe to Polygon parameters
    timeframe_map = {
        "1H": {"multiplier": 1, "timespan": "hour"},
        "4H": {"multiplier": 4, "timespan": "hour"},
        "1D": {"multiplier": 1, "timespan": "day"},
        "1W": {"multiplier": 1, "timespan": "week"},
    }

    tf_config = timeframe_map.get(timeframe, {"multiplier": 4, "timespan": "hour"})

    # Calculate date range
    end_date = datetime.now()
    if timeframe in ["1D", "1W"]:
        start_date = end_date - timedelta(days=limit * 7)
    else:
        start_date = end_date - timedelta(days=limit)

    try:
        bars = polygon.get_aggregates(
            ticker=ticker.upper(),
            multiplier=tf_config["multiplier"],
            timespan=tf_config["timespan"],
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=limit
        )

        if not bars:
            return []

        candles = []
        for bar in bars:
            candles.append({
                "t": bar.get("timestamp"),
                "o": bar.get("open"),
                "h": bar.get("high"),
                "l": bar.get("low"),
                "c": bar.get("close"),
                "v": bar.get("volume"),
            })

        return candles
    except Exception as e:
        logger.error(f"Polygon API error for {ticker}: {e}")
        return []


# =============================================================================
# API ENDPOINTS
# =============================================================================

@api_swing.route("/api/swing/analyze/<ticker>", methods=["GET"])
@login_required
def analyze_swing(ticker: str):
    """
    Analyze a ticker for ICT/SMC swing trading signals.

    Query params:
    - timeframe: 1H, 4H (default), 1D, 1W
    """
    timeframe = request.args.get("timeframe", "4H").upper()

    if timeframe not in ["1H", "4H", "1D", "1W"]:
        timeframe = "4H"

    try:
        # Fetch candle data
        if is_crypto_ticker(ticker):
            candles = fetch_binance_candles(ticker, timeframe, limit=100)
            market_type = "crypto"
        else:
            candles = fetch_polygon_candles(ticker, timeframe, limit=100)
            market_type = "stock"

        if not candles or len(candles) < 50:
            return jsonify({
                "success": False,
                "error": f"Insufficient data for {ticker}. Need at least 50 candles.",
                "ticker": ticker,
                "timeframe": timeframe,
            }), 400

        # Generate ICT/SMC signal
        signal = generate_swing_signal(candles, timeframe=timeframe)

        if not signal:
            return jsonify({
                "success": False,
                "error": "Could not generate signal",
                "ticker": ticker,
                "timeframe": timeframe,
            }), 500

        # Get current price
        current_price = candles[-1]["c"] if candles else None

        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "market_type": market_type,
            "timeframe": timeframe,
            "price": current_price,
            "signal": signal,
        })

    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "ticker": ticker,
        }), 500


@api_swing.route("/api/swing/signal", methods=["POST"])
@login_required
def get_swing_signal():
    """
    Get ICT/SMC swing signal for a ticker.

    POST body:
    {
        "ticker": "AAPL",
        "timeframe": "4H"
    }
    """
    data = request.get_json() or {}
    ticker = data.get("ticker", "").strip().upper()
    timeframe = data.get("timeframe", "4H").upper()

    if not ticker:
        return jsonify({
            "success": False,
            "error": "Ticker is required"
        }), 400

    if timeframe not in ["1H", "4H", "1D", "1W"]:
        timeframe = "4H"

    try:
        # Fetch candle data
        if is_crypto_ticker(ticker):
            candles = fetch_binance_candles(ticker, timeframe, limit=100)
        else:
            candles = fetch_polygon_candles(ticker, timeframe, limit=100)

        if not candles or len(candles) < 50:
            return jsonify({
                "success": False,
                "signal": "WAIT",
                "reason": ["Insufficient data - need 50+ candles"],
                "ticker": ticker,
            })

        # Generate signal
        signal = generate_swing_signal(candles, timeframe=timeframe)

        if not signal:
            return jsonify({
                "success": False,
                "signal": "WAIT",
                "reason": ["Signal generation failed"],
                "ticker": ticker,
            })

        return jsonify({
            "success": True,
            "ticker": ticker,
            "timeframe": timeframe,
            **signal
        })

    except Exception as e:
        logger.error(f"Error getting signal for {ticker}: {e}")
        return jsonify({
            "success": False,
            "signal": "WAIT",
            "reason": [f"Error: {str(e)}"],
            "ticker": ticker,
        })


@api_swing.route("/api/swing/kill-zones", methods=["GET"])
@login_required
def get_kill_zones():
    """Get current Kill Zone status"""
    from web.swing_service import _check_kill_zone

    kill_zone = _check_kill_zone()

    return jsonify({
        "success": True,
        **kill_zone
    })


@api_swing.route("/api/swing/multi-timeframe/<ticker>", methods=["GET"])
@login_required
def multi_timeframe_analysis(ticker: str):
    """
    Multi-timeframe ICT analysis.

    Analyzes Daily (bias) → 4H (structure) → 1H (entry)
    """
    try:
        results = {}

        for tf in ["1D", "4H", "1H"]:
            if is_crypto_ticker(ticker):
                candles = fetch_binance_candles(ticker, tf, limit=100)
            else:
                candles = fetch_polygon_candles(ticker, tf, limit=100)

            if candles and len(candles) >= 50:
                signal = generate_swing_signal(candles, timeframe=tf)
                results[tf] = signal
            else:
                results[tf] = {"signal": "WAIT", "reason": ["Insufficient data"]}

        # Determine overall bias
        daily_trend = results.get("1D", {}).get("market_structure", {}).get("trend", "neutral")
        h4_trend = results.get("4H", {}).get("market_structure", {}).get("trend", "neutral")
        h1_signal = results.get("1H", {}).get("signal", "WAIT")

        # Alignment check
        aligned = False
        recommendation = "WAIT"

        if daily_trend == "bullish" and h4_trend == "bullish":
            if h1_signal == "LONG":
                aligned = True
                recommendation = "LONG"
        elif daily_trend == "bearish" and h4_trend == "bearish":
            if h1_signal == "SHORT":
                aligned = True
                recommendation = "SHORT"

        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "timeframes": results,
            "alignment": {
                "daily_bias": daily_trend,
                "h4_structure": h4_trend,
                "h1_entry": h1_signal,
                "aligned": aligned,
                "recommendation": recommendation,
            }
        })

    except Exception as e:
        logger.error(f"Multi-TF analysis error for {ticker}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "ticker": ticker,
        }), 500

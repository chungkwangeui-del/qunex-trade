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
from typing import Dict, List, Optional, Tuple
import requests
import re
import pytz
from web.polygon_service import PolygonService
from web.finnhub_service import get_finnhub_service
from web.swing_service import generate_swing_signal

logger = logging.getLogger(__name__)

api_swing = Blueprint("api_swing", __name__)


# =============================================================================
# MARKET HOURS CHECK
# =============================================================================

def get_market_status() -> Tuple[bool, str]:
    """
    Check if US stock market is open.
    Returns (is_open, status_message)
    """
    try:
        est = pytz.timezone('US/Eastern')
        now = datetime.now(est)

        # Check weekend
        if now.weekday() >= 5:
            return False, "Market closed (Weekend)"

        # Market hours: 9:30 AM - 4:00 PM EST
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        if now < market_open:
            return False, f"Market closed (Pre-market). Opens at 9:30 AM EST"
        elif now > market_close:
            return False, f"Market closed (After-hours). Opens tomorrow 9:30 AM EST"
        else:
            return True, "Market open"
    except Exception:
        return True, "Unknown"  # Assume open if check fails


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
    Uses multiple endpoints with fallback for geo-restrictions.

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

    # Multiple Binance endpoints for geo-restriction fallback
    endpoints = [
        "https://api.binance.com/api/v3/klines",
        "https://api1.binance.com/api/v3/klines",
        "https://api2.binance.com/api/v3/klines",
        "https://api3.binance.com/api/v3/klines",
        "https://api4.binance.com/api/v3/klines",
        "https://data-api.binance.vision/api/v3/klines",
    ]

    params = {
        "symbol": symbol.upper(),
        "interval": binance_interval,
        "limit": limit
    }

    for url in endpoints:
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

            if candles:
                logger.info(f"Binance: Fetched {len(candles)} candles for {symbol} via {url.split('/')[2]}")
                return candles

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 451:
                # Geo-restricted, try next endpoint
                continue
            logger.warning(f"Binance HTTP error for {symbol} at {url}: {e}")
        except Exception as e:
            logger.warning(f"Binance error for {symbol} at {url}: {e}")
            continue

    logger.error(f"All Binance endpoints failed for {symbol}")
    return []


def fetch_finnhub_candles(ticker: str, timeframe: str = "4H", limit: int = 100) -> List[Dict]:
    """
    Fetch candle data from Finnhub for stocks (primary).

    Timeframes: 1H, 4H, 1D, 1W
    """
    try:
        finnhub = get_finnhub_service()
        candles = finnhub.get_candles_for_swing(ticker, timeframe, limit)

        if candles:
            logger.info(f"Finnhub: Fetched {len(candles)} candles for {ticker} ({timeframe})")
            return candles

        logger.warning(f"No Finnhub data for {ticker}")
        return []
    except Exception as e:
        logger.error(f"Finnhub API error for {ticker}: {e}")
        return []


def fetch_polygon_candles(ticker: str, timeframe: str = "4H", limit: int = 100) -> List[Dict]:
    """
    Fetch candle data from Polygon.io for stocks (fallback).

    Timeframes: 1H, 4H, 1D
    """
    polygon = PolygonService()

    # Check if API key is available
    if not polygon.api_key:
        logger.error("Polygon API key not configured")
        return []

    # Map timeframe to Polygon parameters
    timeframe_map = {
        "1H": {"multiplier": 1, "timespan": "hour"},
        "4H": {"multiplier": 4, "timespan": "hour"},
        "1D": {"multiplier": 1, "timespan": "day"},
        "1W": {"multiplier": 1, "timespan": "week"},
    }

    tf_config = timeframe_map.get(timeframe, {"multiplier": 4, "timespan": "hour"})

    # Calculate date range - need more days for hourly timeframes
    end_date = datetime.now()
    if timeframe == "1W":
        start_date = end_date - timedelta(days=limit * 14)
    elif timeframe == "1D":
        start_date = end_date - timedelta(days=limit * 2)
    elif timeframe == "4H":
        start_date = end_date - timedelta(days=limit)  # 100 days for ~600 4H candles
    else:  # 1H
        start_date = end_date - timedelta(days=limit // 2)  # 50 days for ~400 1H candles

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
            logger.warning(f"No bars returned from Polygon for {ticker}")
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

        logger.info(f"Polygon: Fetched {len(candles)} candles for {ticker} ({timeframe})")
        return candles
    except Exception as e:
        logger.error(f"Polygon API error for {ticker}: {e}", exc_info=True)
        return []


def fetch_stock_candles(ticker: str, timeframe: str = "4H", limit: int = 100) -> List[Dict]:
    """
    Fetch stock candles from Polygon.
    (Finnhub free tier doesn't support historical candles)
    """
    return fetch_polygon_candles(ticker, timeframe, limit)


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
        # Check market status for stocks
        market_open, market_status = get_market_status()

        # Fetch candle data (retry with larger history if needed)
        if is_crypto_ticker(ticker):
            candles = fetch_binance_candles(ticker, timeframe, limit=200)
            market_type = "crypto"
        else:
            candles = fetch_stock_candles(ticker, timeframe, limit=200)
            market_type = "stock"

        if not candles or len(candles) < 30:
            # Better error message for stocks when market is closed
            if market_type == "stock" and not market_open:
                error_msg = f"{market_status}. Stock data unavailable. Try crypto (e.g., BTCUSDT) or wait for market to open."
            else:
                error_msg = f"Insufficient data for {ticker}. Need at least 30 candles."

            return jsonify({
                "success": False,
                "error": error_msg,
                "ticker": ticker,
                "timeframe": timeframe,
                "market_status": market_status if market_type == "stock" else "24/7",
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
            candles = fetch_binance_candles(ticker, timeframe, limit=200)
        else:
            candles = fetch_stock_candles(ticker, timeframe, limit=200)

        if not candles or len(candles) < 30:
            return jsonify({
                "success": False,
                "signal": "WAIT",
                "reason": ["Insufficient data - need 30+ candles"],
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
                candles = fetch_stock_candles(ticker, tf, limit=100)

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

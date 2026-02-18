"""
Scalp Trading Analysis API
Professional candlestick + volume based scalping signals

Strategy Based on Research + Korean Trader "쉽알" Methods:
- Order Blocks: Engulfing patterns create S/R zones
- FVG (Fair Value Gap): Price gaps that tend to get filled
- Confluence Scoring: Minimum 2 reasons required for entry
- Fakeout/Trap Detection: False breakouts for counter-trend entries
- Volume Spike = Exit Signal (not just confirmation)

Key Principles (7 Video Analysis):
1. Order Block = 장악형 캔들 (Engulfing) creates S/R
2. Double Engulfing (이중 장악형) = VERY STRONG signal
3. FVG = 캔들 사이 갭, price returns to fill
4. Multi-timeframe Confluence = Higher weight
5. Fakeout at channel = Entry opportunity
6. Volume spike = Consider taking profits
7. Minimum 2 confluences required for entry

Supported Markets:
- US Stocks via Polygon.io API
- Crypto via Binance API (BTCUSDT, ETHUSDT, etc.)
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
import os
import logging
from datetime import datetime, timedelta, timezone
import re
from web.polygon_service import PolygonService
from web.scalp_service import generate_scalp_signal
from src.services.scalp_engine import ScalpAnalyzer

logger = logging.getLogger(__name__)

api_scalp = Blueprint("api_scalp", __name__)

# Initialize analyzer
analyzer = ScalpAnalyzer()

@api_scalp.route("/api/scalp/analyze/<ticker>")
@login_required
def analyze_ticker(ticker: str):
    """Analyze a ticker for scalp trading opportunities"""
    ticker = ticker.upper().strip()
    interval = request.args.get("interval", "5")

    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    result = analyzer.analyze(ticker, interval)

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)

@api_scalp.route("/api/scalp/quick/<ticker>")
def quick_analysis(ticker: str):
    """Quick analysis without login (limited info)"""
    ticker = ticker.upper().strip()
    interval = request.args.get("interval", "5")

    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    result = analyzer.analyze(ticker, interval)

    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "ticker": result.get("ticker"),
        "price": result.get("price"),
        "signal": result.get("signal"),
        "confidence": result.get("confidence"),
        "primary_pattern": result.get("candlestick", {}).get("primary_pattern", {}).get("name") if result.get("candlestick", {}).get("primary_pattern") else None,
        "message": "Login for full analysis with entry/exit levels and reasoning",
    })

@api_scalp.route("/api/scalp/signal", methods=["POST"])
def scalp_signal():
    """
    Lightweight scalp signal: entry/stop/tp1 with clear reasons.
    Uses Polygon aggregates and rule-based signal (EMA/RSI/volume breakout).
    """
    data = request.get_json() or {}
    ticker = (data.get("ticker") or "").upper().strip()
    timeframe = data.get("timeframe", "15m")
    risk_reward = float(data.get("risk_reward", 2.0))

    if not ticker or len(ticker) > 12 or not re.match(r"^[A-Z0-9]+$", ticker):
        return jsonify({"error": "Invalid ticker"}), 400
    if timeframe not in ["1m", "5m", "15m", "30m", "1h"]:
        return jsonify({"error": "Invalid timeframe"}), 400

    # Map timeframe to Polygon params
    tf_map = {
        "1m": (1, "minute"),
        "5m": (5, "minute"),
        "15m": (15, "minute"),
        "30m": (30, "minute"),
        "1h": (1, "hour"),
    }
    multiplier, span = tf_map[timeframe]

    polygon = PolygonService()
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    agg = polygon.get_aggregates(ticker, multiplier, span, start_date, end_date, limit=500)
    if not agg:
        return jsonify({"error": "No data"}), 404

    signal = generate_scalp_signal(agg, risk_reward=risk_reward)
    if not signal:
        return jsonify({"error": "No signal"}), 404

    signal["ticker"] = ticker
    signal["timeframe"] = timeframe

    return jsonify(signal)

@api_scalp.route("/api/scalp/full/<ticker>")
@login_required
def full_analysis(ticker: str):
    """
    FULL Day Trading Analysis with Advanced S/R

    Combines:
    - Basic Scalping Analysis (candlesticks, volume, patterns)
    - Multi-Timeframe S/R Confluence
    - Volume Profile / VPOC
    - ML-based Bounce Predictions
    - Alert Creation

    This is the MOST COMPREHENSIVE analysis for day trading.
    """
    ticker = ticker.upper().strip()
    interval = request.args.get("interval", "5")
    timeframes_param = request.args.get("timeframes", "5,15,60")

    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    # Parse timeframes
    timeframes = [t.strip() for t in timeframes_param.split(",")]
    valid_tfs = ["1", "5", "15", "60", "240"]
    timeframes = [t for t in timeframes if t in valid_tfs] or ["5", "15", "60"]

    # 1. Basic Scalping Analysis
    scalp_result = analyzer.analyze(ticker, interval)

    if "error" in scalp_result:
        return jsonify(scalp_result), 400

    # 2. Advanced S/R Analysis
    try:
        from web.advanced_sr_analysis import get_advanced_sr_analyzer

        advanced_analyzer = get_advanced_sr_analyzer()
        advanced_sr = advanced_analyzer.full_analysis(ticker, timeframes, create_alerts=True)

        # Combine results
        combined = {
            **scalp_result,
            "advanced_sr": {
                "mtf_analysis": advanced_sr.get("mtf_analysis"),
                "volume_profile": advanced_sr.get("volume_profile"),
                "bounce_predictions": advanced_sr.get("bounce_predictions"),
                "alerts": advanced_sr.get("alerts"),
                "recommendation": advanced_sr.get("recommendation"),
                "enhanced_supports": advanced_sr.get("supports", [])[:5],
                "enhanced_resistances": advanced_sr.get("resistances", [])[:5],
            },
        }

        # Enhance the trade setup with advanced S/R levels
        best_support = advanced_sr.get("bounce_predictions", {}).get("best_support")
        best_resistance = advanced_sr.get("bounce_predictions", {}).get("best_resistance")

        if best_support and scalp_result.get("signal") == "LONG":
            support_info = best_support.get("level_info", {})
            combined["enhanced_trade_setup"] = {
                "entry_zone": {
                    "price": support_info.get("price"),
                    "type": "Multi-Timeframe Support",
                    "bounce_probability": best_support.get("probability"),
                    "confluence_count": support_info.get("confluence_count", 1),
                },
                "stop_loss": support_info.get("price", 0) * 0.99 if support_info.get("price") else None,
                "reasoning": best_support.get("factors", []),
            }

        if best_resistance and scalp_result.get("signal") == "SHORT":
            resistance_info = best_resistance.get("level_info", {})
            combined["enhanced_trade_setup"] = {
                "entry_zone": {
                    "price": resistance_info.get("price"),
                    "type": "Multi-Timeframe Resistance",
                    "rejection_probability": best_resistance.get("probability"),
                    "confluence_count": resistance_info.get("confluence_count", 1),
                },
                "stop_loss": resistance_info.get("price", 0) * 1.01 if resistance_info.get("price") else None,
                "reasoning": best_resistance.get("factors", []),
            }

        return jsonify(combined)

    except Exception as e:
        logger.warning(f"Advanced S/R analysis failed: {e}")
        # Return basic analysis if advanced fails
        scalp_result["advanced_sr"] = {"error": str(e)}
        return jsonify(scalp_result)

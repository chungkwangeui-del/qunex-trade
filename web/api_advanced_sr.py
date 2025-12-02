"""
Advanced S/R Analysis API Endpoints

Features:
1. Multi-Timeframe S/R Analysis
2. Volume Profile / VPOC
3. ML-based Bounce Prediction
4. Real-time Alert System

Routes:
- GET /api/sr/analyze/<ticker> - Full advanced S/R analysis
- GET /api/sr/mtf/<ticker> - Multi-timeframe S/R only
- GET /api/sr/volume-profile/<ticker> - Volume profile analysis
- GET /api/sr/bounce-probability/<ticker> - Bounce predictions
- POST /api/sr/alerts - Create/manage alerts
- GET /api/sr/alerts - Get active alerts
- DELETE /api/sr/alerts - Clear alerts
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
import logging

from web.advanced_sr_analysis import (
    get_advanced_sr_analyzer,
    MultiTimeframeSR,
    VolumeProfileAnalyzer,
    SRBouncePredictor,
    PriceAlertManager,
)

logger = logging.getLogger(__name__)

api_advanced_sr = Blueprint("api_advanced_sr", __name__)


@api_advanced_sr.route("/api/sr/analyze/<ticker>")
@login_required
def full_sr_analysis(ticker: str):
    """
    Full Advanced S/R Analysis

    Combines:
    - Multi-Timeframe Confluence
    - Volume Profile
    - ML Bounce Predictions
    - Alert Creation

    Query Params:
    - timeframes: Comma-separated (default: 5,15,60)
    - alerts: true/false - Create alerts (default: true)

    Returns comprehensive S/R analysis with trading recommendations
    """
    ticker = ticker.upper().strip()

    if not ticker or len(ticker) > 12:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    # Parse timeframes
    tf_param = request.args.get("timeframes", "5,15,60")
    timeframes = [t.strip() for t in tf_param.split(",")]

    # Validate timeframes
    valid_tfs = ["1", "5", "15", "60", "240"]
    timeframes = [t for t in timeframes if t in valid_tfs]

    if not timeframes:
        timeframes = ["5", "15", "60"]

    # Parse alerts option
    create_alerts = request.args.get("alerts", "true").lower() == "true"

    # Perform analysis
    analyzer = get_advanced_sr_analyzer()
    result = analyzer.full_analysis(ticker, timeframes, create_alerts)

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


@api_advanced_sr.route("/api/sr/mtf/<ticker>")
def mtf_analysis(ticker: str):
    """
    Multi-Timeframe S/R Analysis Only

    Finds S/R levels across multiple timeframes and calculates confluence

    Query Params:
    - timeframes: Comma-separated (default: 5,15,60)
    """
    ticker = ticker.upper().strip()

    if not ticker or len(ticker) > 12:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    tf_param = request.args.get("timeframes", "5,15,60")
    timeframes = [t.strip() for t in tf_param.split(",")]

    valid_tfs = ["1", "5", "15", "60", "240"]
    timeframes = [t for t in timeframes if t in valid_tfs] or ["5", "15", "60"]

    mtf_analyzer = MultiTimeframeSR()
    result = mtf_analyzer.analyze_multi_timeframe(ticker, timeframes)

    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        **result,
    })


@api_advanced_sr.route("/api/sr/volume-profile/<ticker>")
def volume_profile_analysis(ticker: str):
    """
    Volume Profile Analysis

    Returns:
    - VPOC (Volume Point of Control)
    - Value Area (High/Low)
    - High Volume Nodes (HVN)
    - Low Volume Nodes (LVN)
    - S/R levels derived from volume

    Query Params:
    - interval: Timeframe (default: 5)
    - limit: Number of bars (default: 100)
    """
    ticker = ticker.upper().strip()

    if not ticker or len(ticker) > 12:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    interval = request.args.get("interval", "5")
    limit = int(request.args.get("limit", 100))

    # Fetch bars
    mtf_analyzer = MultiTimeframeSR()
    bars = mtf_analyzer._fetch_bars(ticker, interval, limit)

    if not bars:
        return jsonify({"error": "Failed to fetch price data"}), 400

    # Calculate volume profile
    vp_analyzer = VolumeProfileAnalyzer()
    profile = vp_analyzer.calculate_volume_profile(bars)

    if "error" in profile:
        return jsonify(profile), 400

    # Get S/R from volume profile
    sr_levels = vp_analyzer.get_sr_from_volume_profile(bars)

    return jsonify({
        "ticker": ticker,
        "interval": interval,
        "bars_analyzed": len(bars),
        "timestamp": datetime.now().isoformat(),
        "vpoc": profile.get("vpoc"),
        "value_area": profile.get("value_area"),
        "high_volume_nodes": profile.get("high_volume_nodes", []),
        "low_volume_nodes": profile.get("low_volume_nodes", []),
        "supports": sr_levels.get("supports", []),
        "resistances": sr_levels.get("resistances", []),
        "current_price": profile.get("current_price"),
    })


@api_advanced_sr.route("/api/sr/bounce-probability/<ticker>")
def bounce_probability(ticker: str):
    """
    ML-based Bounce Probability Analysis

    Predicts probability of price bouncing at S/R levels

    Query Params:
    - timeframes: For MTF S/R (default: 5,15,60)
    """
    ticker = ticker.upper().strip()

    if not ticker or len(ticker) > 12:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    tf_param = request.args.get("timeframes", "5,15,60")
    timeframes = [t.strip() for t in tf_param.split(",")]

    valid_tfs = ["1", "5", "15", "60", "240"]
    timeframes = [t for t in timeframes if t in valid_tfs] or ["5", "15", "60"]

    # Get MTF analysis
    mtf_analyzer = MultiTimeframeSR()
    mtf_result = mtf_analyzer.analyze_multi_timeframe(ticker, timeframes)

    if "error" in mtf_result:
        return jsonify(mtf_result), 400

    # Get bars for volume profile
    lowest_tf = min(timeframes, key=lambda x: int(x))
    bars = mtf_analyzer._fetch_bars(ticker, lowest_tf, limit=100)

    # Get volume profile
    vp_analyzer = VolumeProfileAnalyzer()
    volume_profile = vp_analyzer.calculate_volume_profile(bars) if bars else None

    # Calculate bounce probabilities
    predictor = SRBouncePredictor()
    bounce_analysis = predictor.analyze_all_levels(
        mtf_result.get("confluence_supports", []),
        mtf_result.get("confluence_resistances", []),
        bars,
        volume_profile
    )

    return jsonify({
        "ticker": ticker,
        "current_price": mtf_result.get("current_price"),
        "timestamp": datetime.now().isoformat(),
        "best_support": bounce_analysis.get("best_support"),
        "best_resistance": bounce_analysis.get("best_resistance"),
        "support_predictions": bounce_analysis.get("supports", []),
        "resistance_predictions": bounce_analysis.get("resistances", []),
    })


# Alert Management Endpoints

@api_advanced_sr.route("/api/sr/alerts", methods=["GET"])
@login_required
def get_alerts():
    """
    Get Active Alerts

    Query Params:
    - ticker: Filter by ticker (optional)
    """
    ticker = request.args.get("ticker")

    analyzer = get_advanced_sr_analyzer()
    alerts = analyzer.alert_manager.get_active_alerts(ticker)

    return jsonify({
        "status": "success",
        **alerts,
    })


@api_advanced_sr.route("/api/sr/alerts", methods=["POST"])
@login_required
def create_alerts():
    """
    Create S/R Alerts for a Ticker

    JSON Body:
    {
        "ticker": "AAPL",
        "timeframes": ["5", "15", "60"]  // optional
    }
    """
    data = request.get_json()

    if not data or "ticker" not in data:
        return jsonify({"error": "ticker is required"}), 400

    ticker = data["ticker"].upper().strip()
    timeframes = data.get("timeframes", ["5", "15", "60"])

    # Get S/R levels
    mtf_analyzer = MultiTimeframeSR()
    mtf_result = mtf_analyzer.analyze_multi_timeframe(ticker, timeframes)

    if "error" in mtf_result:
        return jsonify(mtf_result), 400

    # Create alerts
    analyzer = get_advanced_sr_analyzer()
    alerts = analyzer.alert_manager.create_sr_alerts(
        ticker,
        mtf_result.get("confluence_supports", []),
        mtf_result.get("confluence_resistances", []),
        mtf_result.get("current_price", 0)
    )

    return jsonify({
        "status": "success",
        "ticker": ticker,
        "alerts_created": len(alerts),
        "alerts": alerts[:10],  # First 10
    })


@api_advanced_sr.route("/api/sr/alerts", methods=["DELETE"])
@login_required
def clear_alerts():
    """
    Clear Alerts

    Query Params:
    - ticker: Clear for specific ticker (optional, clears all if not specified)
    """
    ticker = request.args.get("ticker")

    analyzer = get_advanced_sr_analyzer()
    result = analyzer.alert_manager.clear_alerts(ticker)

    return jsonify({
        "status": "success",
        **result,
    })


@api_advanced_sr.route("/api/sr/alerts/check/<ticker>")
@login_required
def check_alerts(ticker: str):
    """
    Check if any alerts have been triggered for a ticker

    Returns triggered alerts (removes them from active alerts)
    """
    ticker = ticker.upper().strip()

    # Get current price
    mtf_analyzer = MultiTimeframeSR()
    bars = mtf_analyzer._fetch_bars(ticker, "5", limit=2)

    if not bars:
        return jsonify({"error": "Failed to fetch current price"}), 400

    current_price = bars[-1].get("c", 0)
    prev_price = bars[-2].get("c", 0) if len(bars) > 1 else current_price

    # Check alerts
    analyzer = get_advanced_sr_analyzer()
    triggered = analyzer.alert_manager.check_alerts(ticker, current_price, prev_price)

    return jsonify({
        "ticker": ticker,
        "current_price": current_price,
        "triggered_count": len(triggered),
        "triggered_alerts": triggered,
        "timestamp": datetime.now().isoformat(),
    })


# Quick Analysis Endpoint (No Login Required)
@api_advanced_sr.route("/api/sr/quick/<ticker>")
def quick_sr_analysis(ticker: str):
    """
    Quick S/R Analysis (No Login Required)

    Returns basic S/R levels without full analysis
    """
    ticker = ticker.upper().strip()

    if not ticker or len(ticker) > 12:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    mtf_analyzer = MultiTimeframeSR()
    result = mtf_analyzer.analyze_multi_timeframe(ticker, ["5", "15"])

    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "ticker": ticker,
        "current_price": result.get("current_price"),
        "nearest_support": result.get("nearest_support"),
        "nearest_resistance": result.get("nearest_resistance"),
        "message": "Login for full analysis with bounce predictions and alerts",
        "timestamp": datetime.now().isoformat(),
    })

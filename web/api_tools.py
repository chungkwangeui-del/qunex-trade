"""
Trading Tools API - Risk Management & Position Sizing

Provides calculators for:
- Position size based on risk %
- Risk/Reward calculations
- Kelly Criterion sizing
- Stop loss placement suggestions
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
import math

api_tools = Blueprint("api_tools", __name__)


@api_tools.route("/api/tools/position-size", methods=["POST"])
@login_required
def calculate_position_size():
    """
    Calculate optimal position size based on risk management.
    
    Uses Fixed Fractional method - never risk more than X% per trade.
    
    Request JSON:
        account_size: float - Total account value
        risk_percent: float - Max risk per trade (default 2%)
        entry_price: float - Planned entry price
        stop_loss: float - Stop loss price
        
    Returns:
        shares: int - Number of shares to buy
        position_value: float - Total position value
        risk_amount: float - Dollar amount at risk
        risk_per_share: float - Risk per share
    """
    data = request.get_json() or {}
    
    try:
        account_size = float(data.get("account_size", 10000))
        risk_percent = float(data.get("risk_percent", 2))
        entry_price = float(data.get("entry_price", 0))
        stop_loss = float(data.get("stop_loss", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric values"}), 400
    
    if entry_price <= 0:
        return jsonify({"error": "Entry price must be positive"}), 400
    if stop_loss <= 0:
        return jsonify({"error": "Stop loss must be positive"}), 400
    if risk_percent <= 0 or risk_percent > 100:
        return jsonify({"error": "Risk percent must be between 0 and 100"}), 400
    
    # Calculate risk per share
    risk_per_share = abs(entry_price - stop_loss)
    
    if risk_per_share == 0:
        return jsonify({"error": "Entry and stop loss cannot be the same"}), 400
    
    # Max dollar risk allowed
    max_risk = account_size * (risk_percent / 100)
    
    # Calculate position size
    shares = int(max_risk / risk_per_share)
    position_value = shares * entry_price
    actual_risk = shares * risk_per_share
    
    # Calculate R multiples for targets
    risk_multiples = []
    for r in [1, 1.5, 2, 3, 5]:
        if stop_loss < entry_price:  # Long trade
            target = entry_price + (risk_per_share * r)
        else:  # Short trade
            target = entry_price - (risk_per_share * r)
        
        profit = shares * risk_per_share * r
        risk_multiples.append({
            "r": r,
            "target_price": round(target, 2),
            "profit": round(profit, 2),
        })
    
    return jsonify({
        "shares": shares,
        "position_value": round(position_value, 2),
        "risk_amount": round(actual_risk, 2),
        "risk_percent": risk_percent,
        "risk_per_share": round(risk_per_share, 4),
        "account_percent_used": round((position_value / account_size) * 100, 1),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "trade_direction": "long" if stop_loss < entry_price else "short",
        "targets": risk_multiples,
        "warnings": _get_position_warnings(account_size, position_value, shares, entry_price),
    })


def _get_position_warnings(account_size: float, position_value: float, shares: int, entry_price: float) -> list:
    """Generate warnings for position sizing"""
    warnings = []
    
    position_pct = (position_value / account_size) * 100
    
    if position_pct > 25:
        warnings.append(f"Large position: {position_pct:.1f}% of account in single trade")
    
    if shares < 1:
        warnings.append("Position size too small - consider smaller risk % or larger account")
    
    if entry_price < 1:
        warnings.append("Penny stock alert: High volatility and spread risk")
    
    return warnings


@api_tools.route("/api/tools/kelly-criterion", methods=["POST"])
@login_required
def calculate_kelly():
    """
    Calculate Kelly Criterion position sizing.
    
    Kelly % = W - [(1-W) / R]
    Where:
        W = Win rate (probability of winning)
        R = Win/Loss ratio (average win / average loss)
        
    Request JSON:
        win_rate: float - Win percentage (0-100)
        avg_win: float - Average winning trade $
        avg_loss: float - Average losing trade $
        account_size: float - Total account value
        kelly_fraction: float - Fraction of Kelly to use (default 0.5 = Half Kelly)
    """
    data = request.get_json() or {}
    
    try:
        win_rate = float(data.get("win_rate", 50)) / 100  # Convert to decimal
        avg_win = float(data.get("avg_win", 100))
        avg_loss = float(data.get("avg_loss", 100))
        account_size = float(data.get("account_size", 10000))
        kelly_fraction = float(data.get("kelly_fraction", 0.5))  # Half Kelly is safer
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric values"}), 400
    
    if avg_loss == 0:
        return jsonify({"error": "Average loss cannot be zero"}), 400
    
    # Win/Loss ratio
    win_loss_ratio = avg_win / avg_loss
    
    # Kelly formula: K% = W - [(1-W) / R]
    kelly_percent = win_rate - ((1 - win_rate) / win_loss_ratio)
    
    # Apply Kelly fraction (Half Kelly is recommended)
    adjusted_kelly = kelly_percent * kelly_fraction
    
    # Never risk more than 25% even if Kelly suggests it
    capped_kelly = min(adjusted_kelly, 0.25)
    
    # Calculate suggested position
    suggested_risk = account_size * max(0, capped_kelly)
    
    return jsonify({
        "full_kelly_percent": round(kelly_percent * 100, 2),
        "adjusted_kelly_percent": round(adjusted_kelly * 100, 2),
        "capped_kelly_percent": round(capped_kelly * 100, 2),
        "kelly_fraction_used": kelly_fraction,
        "suggested_risk_amount": round(suggested_risk, 2),
        "win_rate": round(win_rate * 100, 1),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "expectancy": round((win_rate * avg_win) - ((1 - win_rate) * avg_loss), 2),
        "recommendation": _kelly_recommendation(kelly_percent),
    })


def _kelly_recommendation(kelly_percent: float) -> str:
    """Generate recommendation based on Kelly %"""
    if kelly_percent <= 0:
        return "Negative edge - Do not trade this strategy"
    elif kelly_percent < 0.05:
        return "Very small edge - Use minimal position size"
    elif kelly_percent < 0.15:
        return "Moderate edge - Use Half Kelly or less"
    elif kelly_percent < 0.25:
        return "Good edge - Half Kelly recommended"
    else:
        return "Strong edge - Still use Half Kelly for safety"


@api_tools.route("/api/tools/stop-loss-levels", methods=["POST"])
@login_required
def calculate_stop_levels():
    """
    Calculate suggested stop loss levels using multiple methods.
    
    Methods:
    - ATR-based (1.5x, 2x, 3x ATR)
    - Percentage-based (1%, 2%, 5%)
    - Support/Resistance based
    
    Request JSON:
        ticker: str - Stock symbol
        entry_price: float - Entry price
        trade_direction: str - 'long' or 'short'
        atr: float - Current ATR value (optional)
    """
    data = request.get_json() or {}
    
    entry_price = float(data.get("entry_price", 0))
    direction = data.get("trade_direction", "long").lower()
    atr = float(data.get("atr", 0)) if data.get("atr") else None
    
    if entry_price <= 0:
        return jsonify({"error": "Entry price must be positive"}), 400
    
    levels = []
    
    # Percentage-based stops
    percentages = [1, 2, 3, 5, 7, 10]
    for pct in percentages:
        if direction == "long":
            stop = entry_price * (1 - pct / 100)
        else:
            stop = entry_price * (1 + pct / 100)
        
        levels.append({
            "method": f"{pct}% stop",
            "stop_price": round(stop, 4),
            "distance_pct": pct,
            "risk_level": "tight" if pct <= 2 else "normal" if pct <= 5 else "wide",
        })
    
    # ATR-based stops (if ATR provided)
    if atr and atr > 0:
        atr_multipliers = [1, 1.5, 2, 2.5, 3]
        for mult in atr_multipliers:
            if direction == "long":
                stop = entry_price - (atr * mult)
            else:
                stop = entry_price + (atr * mult)
            
            distance_pct = (abs(entry_price - stop) / entry_price) * 100
            
            levels.append({
                "method": f"{mult}x ATR",
                "stop_price": round(stop, 4),
                "distance_pct": round(distance_pct, 2),
                "atr_value": atr,
                "risk_level": "tight" if mult <= 1.5 else "normal" if mult <= 2 else "wide",
            })
    
    return jsonify({
        "entry_price": entry_price,
        "trade_direction": direction,
        "stop_levels": levels,
        "recommendation": "Use 1.5-2x ATR for swing trades, 2-3% for day trades",
    })


@api_tools.route("/api/tools/risk-reward", methods=["POST"])
@login_required
def calculate_risk_reward():
    """
    Calculate Risk/Reward metrics for a trade setup.
    
    Request JSON:
        entry_price: float
        stop_loss: float
        targets: list[float] - List of target prices
    """
    data = request.get_json() or {}
    
    try:
        entry = float(data.get("entry_price", 0))
        stop = float(data.get("stop_loss", 0))
        targets = data.get("targets", [])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    
    if entry <= 0 or stop <= 0:
        return jsonify({"error": "Prices must be positive"}), 400
    
    risk = abs(entry - stop)
    direction = "long" if stop < entry else "short"
    
    results = []
    for i, target in enumerate(targets, 1):
        try:
            target = float(target)
        except (ValueError, TypeError):
            continue
        
        reward = abs(target - entry)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Win rate needed to break even at this R:R
        breakeven_winrate = (1 / (1 + rr_ratio)) * 100 if rr_ratio > 0 else 100
        
        results.append({
            "target_num": i,
            "target_price": target,
            "reward": round(reward, 4),
            "risk_reward_ratio": round(rr_ratio, 2),
            "breakeven_winrate": round(breakeven_winrate, 1),
            "grade": _grade_rr(rr_ratio),
        })
    
    return jsonify({
        "entry_price": entry,
        "stop_loss": stop,
        "risk": round(risk, 4),
        "trade_direction": direction,
        "targets": results,
        "summary": {
            "best_rr": max([r["risk_reward_ratio"] for r in results]) if results else 0,
            "recommendation": "Minimum 2:1 R:R recommended for consistent profitability",
        }
    })


def _grade_rr(ratio: float) -> str:
    """Grade a risk/reward ratio"""
    if ratio >= 3:
        return "A - Excellent"
    elif ratio >= 2:
        return "B - Good"
    elif ratio >= 1.5:
        return "C - Acceptable"
    elif ratio >= 1:
        return "D - Poor"
    else:
        return "F - Avoid"


@api_tools.route("/api/tools/profit-calculator", methods=["POST"])
@login_required
def calculate_profit():
    """
    Calculate potential profit/loss for a trade.
    
    Request JSON:
        shares: int
        entry_price: float
        exit_price: float
        commission: float (optional, per trade)
    """
    data = request.get_json() or {}
    
    try:
        shares = int(data.get("shares", 0))
        entry_price = float(data.get("entry_price", 0))
        exit_price = float(data.get("exit_price", 0))
        commission = float(data.get("commission", 0))  # Per trade
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    
    # Calculate P&L
    gross_pnl = (exit_price - entry_price) * shares
    total_commission = commission * 2  # Entry + Exit
    net_pnl = gross_pnl - total_commission
    
    pnl_percent = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    
    return jsonify({
        "shares": shares,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "entry_cost": round(entry_price * shares, 2),
        "exit_value": round(exit_price * shares, 2),
        "gross_pnl": round(gross_pnl, 2),
        "commission_total": round(total_commission, 2),
        "net_pnl": round(net_pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "outcome": "profit" if net_pnl > 0 else "loss" if net_pnl < 0 else "breakeven",
    })


"""
Portfolio Analytics API

Advanced analytics for portfolio performance tracking:
- Daily/weekly/monthly performance
- Risk metrics (Sharpe, Sortino, Max Drawdown)
- Correlation analysis
- Performance attribution
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import defaultdict
import math
import logging

try:
    from web.database import db, Transaction, PortfolioSnapshot, TradeJournal
    from web.polygon_service import get_polygon_service
except ImportError:
    from database import db, Transaction, PortfolioSnapshot, TradeJournal
    from polygon_service import get_polygon_service

logger = logging.getLogger(__name__)

api_analytics = Blueprint("api_analytics", __name__)


@api_analytics.route("/api/analytics/performance")
@login_required
def get_performance_analytics():
    """
    Get comprehensive portfolio performance analytics.
    
    Query params:
        period: str - '1W', '1M', '3M', '6M', '1Y', 'ALL' (default '1M')
    """
    period = request.args.get("period", "1M")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    period_days = {
        "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "ALL": 3650
    }
    days = period_days.get(period, 30)
    start_date = end_date - timedelta(days=days)
    
    # Get transactions in period
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= start_date
    ).order_by(Transaction.transaction_date).all()
    
    if not transactions:
        return jsonify({
            "period": period,
            "message": "No transactions in this period",
            "total_trades": 0,
        })
    
    # Calculate holdings and P&L
    holdings = defaultdict(lambda: {"shares": Decimal("0"), "cost_basis": Decimal("0")})
    realized_pnl = Decimal("0")
    
    for txn in transactions:
        ticker = txn.ticker
        shares = Decimal(str(txn.shares))
        price = Decimal(str(txn.price))
        
        if txn.transaction_type == "buy":
            holdings[ticker]["shares"] += shares
            holdings[ticker]["cost_basis"] += shares * price
        elif txn.transaction_type == "sell":
            if holdings[ticker]["shares"] > 0:
                avg_cost = holdings[ticker]["cost_basis"] / holdings[ticker]["shares"]
                realized_pnl += (price - avg_cost) * shares
                holdings[ticker]["shares"] -= shares
                holdings[ticker]["cost_basis"] -= shares * avg_cost
    
    # Get current prices for unrealized P&L
    polygon = get_polygon_service()
    current_holdings = {k: v for k, v in holdings.items() if v["shares"] > 0}
    
    unrealized_pnl = Decimal("0")
    portfolio_value = Decimal("0")
    position_data = []
    
    for ticker, holding in current_holdings.items():
        try:
            quote = polygon.get_stock_quote(ticker)
            current_price = Decimal(str(quote.get("price", 0))) if quote else Decimal("0")
            
            shares = holding["shares"]
            cost_basis = holding["cost_basis"]
            current_value = shares * current_price
            position_pnl = current_value - cost_basis
            
            unrealized_pnl += position_pnl
            portfolio_value += current_value
            
            position_data.append({
                "ticker": ticker,
                "shares": float(shares),
                "avg_cost": float(cost_basis / shares) if shares > 0 else 0,
                "current_price": float(current_price),
                "current_value": float(current_value),
                "pnl": float(position_pnl),
                "pnl_percent": float((position_pnl / cost_basis * 100) if cost_basis > 0 else 0),
                "weight": 0,  # Calculated below
            })
        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {e}")
    
    # Calculate weights
    for pos in position_data:
        pos["weight"] = round((pos["current_value"] / float(portfolio_value) * 100), 2) if portfolio_value > 0 else 0
    
    # Sort by weight
    position_data.sort(key=lambda x: x["weight"], reverse=True)
    
    total_pnl = realized_pnl + unrealized_pnl
    
    return jsonify({
        "period": period,
        "portfolio_value": float(portfolio_value),
        "realized_pnl": float(realized_pnl),
        "unrealized_pnl": float(unrealized_pnl),
        "total_pnl": float(total_pnl),
        "total_trades": len(transactions),
        "positions": position_data,
        "top_performer": position_data[0]["ticker"] if position_data else None,
        "worst_performer": min(position_data, key=lambda x: x["pnl"])["ticker"] if position_data else None,
    })


@api_analytics.route("/api/analytics/risk-metrics")
@login_required
def get_risk_metrics():
    """
    Calculate risk metrics for the portfolio.
    
    Metrics:
    - Sharpe Ratio
    - Sortino Ratio
    - Max Drawdown
    - Beta (vs SPY)
    - Volatility
    """
    # Get portfolio snapshots for calculations
    snapshots = PortfolioSnapshot.query.filter_by(
        user_id=current_user.id
    ).order_by(PortfolioSnapshot.snapshot_date).all()
    
    if len(snapshots) < 10:
        return jsonify({
            "message": "Need at least 10 days of data for risk metrics",
            "days_available": len(snapshots),
        })
    
    # Calculate daily returns
    returns = []
    for i in range(1, len(snapshots)):
        prev_val = float(snapshots[i-1].total_value)
        curr_val = float(snapshots[i].total_value)
        if prev_val > 0:
            daily_return = (curr_val - prev_val) / prev_val
            returns.append(daily_return)
    
    if not returns:
        return jsonify({"message": "Insufficient data for calculations"})
    
    # Mean return (annualized)
    mean_return = sum(returns) / len(returns)
    annualized_return = mean_return * 252
    
    # Standard deviation (annualized)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)
    annualized_volatility = std_dev * math.sqrt(252)
    
    # Sharpe Ratio (assuming 5% risk-free rate)
    risk_free_rate = 0.05
    sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else 0
    
    # Sortino Ratio (only downside deviation)
    negative_returns = [r for r in returns if r < 0]
    if negative_returns:
        downside_variance = sum(r ** 2 for r in negative_returns) / len(returns)
        downside_deviation = math.sqrt(downside_variance) * math.sqrt(252)
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
    else:
        sortino_ratio = float('inf')
    
    # Max Drawdown
    peak = float(snapshots[0].total_value)
    max_drawdown = 0
    
    for snapshot in snapshots:
        value = float(snapshot.total_value)
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)
    
    # Win days vs Loss days
    up_days = sum(1 for r in returns if r > 0)
    down_days = sum(1 for r in returns if r < 0)
    
    return jsonify({
        "days_analyzed": len(snapshots),
        "annualized_return": round(annualized_return * 100, 2),
        "annualized_volatility": round(annualized_volatility * 100, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2) if sortino_ratio != float('inf') else "∞",
        "max_drawdown": round(max_drawdown * 100, 2),
        "up_days": up_days,
        "down_days": down_days,
        "win_day_rate": round((up_days / len(returns) * 100), 1) if returns else 0,
        "best_day": round(max(returns) * 100, 2) if returns else 0,
        "worst_day": round(min(returns) * 100, 2) if returns else 0,
        "avg_daily_return": round(mean_return * 100, 3),
    })


@api_analytics.route("/api/analytics/trade-analysis")
@login_required
def get_trade_analysis():
    """
    Analyze trading patterns from journal entries.
    
    Provides insights on:
    - Best performing days/times
    - Strategy effectiveness
    - Emotional patterns
    - Common mistakes
    """
    entries = TradeJournal.query.filter_by(user_id=current_user.id).all()
    closed_trades = [e for e in entries if e.exit_price is not None]
    
    if len(closed_trades) < 5:
        return jsonify({
            "message": "Need at least 5 closed trades for analysis",
            "trades_available": len(closed_trades),
        })
    
    # Analysis by day of week
    day_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for trade in closed_trades:
        if trade.entry_date:
            day_name = days[trade.entry_date.weekday()]
            day_stats[day_name]["trades"] += 1
            if trade.outcome == "win":
                day_stats[day_name]["wins"] += 1
            day_stats[day_name]["pnl"] += float(trade.pnl or 0)
    
    for day in day_stats:
        if day_stats[day]["trades"] > 0:
            day_stats[day]["win_rate"] = round(
                (day_stats[day]["wins"] / day_stats[day]["trades"]) * 100, 1
            )
    
    # Analysis by timeframe
    tf_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    for trade in closed_trades:
        tf = trade.timeframe or "Unknown"
        tf_stats[tf]["trades"] += 1
        if trade.outcome == "win":
            tf_stats[tf]["wins"] += 1
        tf_stats[tf]["pnl"] += float(trade.pnl or 0)
    
    for tf in tf_stats:
        if tf_stats[tf]["trades"] > 0:
            tf_stats[tf]["win_rate"] = round(
                (tf_stats[tf]["wins"] / tf_stats[tf]["trades"]) * 100, 1
            )
    
    # Emotion analysis
    emotion_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    for trade in closed_trades:
        emotion = trade.emotion_before or "Unknown"
        emotion_stats[emotion]["trades"] += 1
        if trade.outcome == "win":
            emotion_stats[emotion]["wins"] += 1
        emotion_stats[emotion]["pnl"] += float(trade.pnl or 0)
    
    for emotion in emotion_stats:
        if emotion_stats[emotion]["trades"] > 0:
            emotion_stats[emotion]["win_rate"] = round(
                (emotion_stats[emotion]["wins"] / emotion_stats[emotion]["trades"]) * 100, 1
            )
    
    # Common mistakes analysis
    mistakes = []
    for trade in closed_trades:
        if trade.mistakes:
            mistakes.append(trade.mistakes.lower())
    
    # Find most common mistake words
    mistake_words = defaultdict(int)
    common_issues = ["fomo", "revenge", "early", "late", "stop", "size", "plan", "patience"]
    for mistake in mistakes:
        for issue in common_issues:
            if issue in mistake:
                mistake_words[issue] += 1
    
    # Best and worst setups
    setup_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    for trade in closed_trades:
        setup = trade.setup_type or "Unknown"
        setup_stats[setup]["trades"] += 1
        if trade.outcome == "win":
            setup_stats[setup]["wins"] += 1
        setup_stats[setup]["pnl"] += float(trade.pnl or 0)
    
    for setup in setup_stats:
        if setup_stats[setup]["trades"] > 0:
            setup_stats[setup]["win_rate"] = round(
                (setup_stats[setup]["wins"] / setup_stats[setup]["trades"]) * 100, 1
            )
    
    # Sort setups by win rate
    best_setups = sorted(
        [(k, v) for k, v in setup_stats.items() if v["trades"] >= 3],
        key=lambda x: x[1]["win_rate"],
        reverse=True
    )
    
    return jsonify({
        "total_trades_analyzed": len(closed_trades),
        "by_day": dict(day_stats),
        "by_timeframe": dict(tf_stats),
        "by_emotion": dict(emotion_stats),
        "by_setup": dict(setup_stats),
        "best_day": max(day_stats.items(), key=lambda x: x[1].get("win_rate", 0))[0] if day_stats else None,
        "best_setup": best_setups[0][0] if best_setups else None,
        "common_mistakes": dict(sorted(mistake_words.items(), key=lambda x: x[1], reverse=True)[:5]),
        "insights": _generate_insights(closed_trades, day_stats, emotion_stats),
    })


def _generate_insights(trades, day_stats, emotion_stats) -> list:
    """Generate actionable insights from trading data."""
    insights = []
    
    # Check for FOMO trading
    if emotion_stats.get("fomo", {}).get("trades", 0) > 0:
        fomo_wr = emotion_stats["fomo"].get("win_rate", 0)
        if fomo_wr < 40:
            insights.append({
                "type": "warning",
                "message": f"FOMO trades have only {fomo_wr}% win rate. Consider waiting for proper setups.",
            })
    
    # Check plan adherence
    followed = sum(1 for t in trades if t.followed_plan)
    not_followed = len(trades) - followed
    if not_followed > len(trades) * 0.3:
        insights.append({
            "type": "warning", 
            "message": f"You deviated from your plan in {not_followed} trades. Discipline is key!",
        })
    
    # Find best day
    if day_stats:
        best = max(day_stats.items(), key=lambda x: x[1].get("win_rate", 0))
        if best[1].get("win_rate", 0) > 60:
            insights.append({
                "type": "positive",
                "message": f"{best[0]}s are your best day with {best[1]['win_rate']}% win rate!",
            })
    
    # Check for overtrading
    trade_count = len(trades)
    if trade_count > 50:  # Assuming monthly analysis
        insights.append({
            "type": "info",
            "message": "High trade volume detected. Consider focusing on higher quality setups.",
        })
    
    return insights


@api_analytics.route("/api/analytics/equity-curve")
@login_required
def get_equity_curve():
    """
    Get equity curve data for charting.
    
    Returns daily portfolio values over time.
    """
    period = request.args.get("period", "1M")
    
    period_days = {
        "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "ALL": 3650
    }
    days = period_days.get(period, 30)
    start_date = datetime.now().date() - timedelta(days=days)
    
    snapshots = PortfolioSnapshot.query.filter(
        PortfolioSnapshot.user_id == current_user.id,
        PortfolioSnapshot.snapshot_date >= start_date
    ).order_by(PortfolioSnapshot.snapshot_date).all()
    
    data_points = []
    for snapshot in snapshots:
        data_points.append({
            "date": snapshot.snapshot_date.isoformat(),
            "value": float(snapshot.total_value),
            "pnl": float(snapshot.daily_pnl) if snapshot.daily_pnl else 0,
        })
    
    return jsonify({
        "period": period,
        "data_points": data_points,
        "count": len(data_points),
    })


@api_analytics.route("/api/analytics/snapshot", methods=["POST"])
@login_required
def create_portfolio_snapshot():
    """
    Create a daily portfolio snapshot.
    
    Should be called by a cron job or manually to track performance over time.
    """
    from collections import defaultdict
    
    today = datetime.now().date()
    
    # Check if snapshot already exists for today
    existing = PortfolioSnapshot.query.filter_by(
        user_id=current_user.id,
        snapshot_date=today
    ).first()
    
    if existing:
        return jsonify({"message": "Snapshot already exists for today", "snapshot": existing.to_dict()})
    
    # Calculate current portfolio value
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    holdings = defaultdict(lambda: {"shares": Decimal("0"), "cost_basis": Decimal("0")})
    
    for txn in transactions:
        ticker = txn.ticker
        shares = Decimal(str(txn.shares))
        price = Decimal(str(txn.price))
        
        if txn.transaction_type == "buy":
            holdings[ticker]["shares"] += shares
            holdings[ticker]["cost_basis"] += shares * price
        else:
            if holdings[ticker]["shares"] > 0:
                avg_cost = holdings[ticker]["cost_basis"] / holdings[ticker]["shares"]
                holdings[ticker]["shares"] -= shares
                holdings[ticker]["cost_basis"] -= shares * avg_cost
    
    # Get current prices
    polygon = get_polygon_service()
    current_holdings = {k: v for k, v in holdings.items() if v["shares"] > 0}
    
    total_value = Decimal("0")
    invested_value = Decimal("0")
    
    for ticker, holding in current_holdings.items():
        try:
            quote = polygon.get_stock_quote(ticker)
            current_price = Decimal(str(quote.get("price", 0))) if quote else Decimal("0")
            total_value += holding["shares"] * current_price
            invested_value += holding["cost_basis"]
        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {e}")
    
    # Get yesterday's snapshot for daily P&L
    yesterday = today - timedelta(days=1)
    prev_snapshot = PortfolioSnapshot.query.filter_by(
        user_id=current_user.id,
        snapshot_date=yesterday
    ).first()
    
    daily_pnl = Decimal("0")
    daily_pnl_percent = 0
    
    if prev_snapshot:
        daily_pnl = total_value - prev_snapshot.total_value
        if prev_snapshot.total_value > 0:
            daily_pnl_percent = float((daily_pnl / prev_snapshot.total_value) * 100)
    
    # Create snapshot
    snapshot = PortfolioSnapshot(
        user_id=current_user.id,
        snapshot_date=today,
        total_value=total_value,
        invested_value=invested_value,
        daily_pnl=daily_pnl,
        daily_pnl_percent=daily_pnl_percent,
        total_pnl=total_value - invested_value,
        total_pnl_percent=float((total_value - invested_value) / invested_value * 100) if invested_value > 0 else 0,
        positions_count=len(current_holdings),
    )
    
    db.session.add(snapshot)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "snapshot": snapshot.to_dict(),
    })


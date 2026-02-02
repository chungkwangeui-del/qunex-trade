"""
Paper Trading Leaderboard API - Competitive Rankings

Features:
- Global rankings by total P&L
- Weekly/Monthly competitions
- Performance metrics (win rate, Sharpe ratio, etc.)
- Achievement badges
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.extensions import csrf, cache
from web.database import db, User, PaperAccount, PaperTrade
from web.polygon_service import get_polygon_service
from sqlalchemy import func, desc
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import logging
from datetime import timedelta
from datetime import timezone

logger = logging.getLogger(__name__)

api_leaderboard = Blueprint("api_leaderboard", __name__)
csrf.exempt(api_leaderboard)

INITIAL_BALANCE = Decimal("100000.00")

def calculate_user_metrics(user_id: int) -> dict:
    """Calculate detailed trading metrics for a user"""
    account = PaperAccount.query.filter_by(user_id=user_id).first()
    if not account:
        return None

    trades = PaperTrade.query.filter_by(user_id=user_id).all()

    # Get current holdings value
    holdings = {}
    for trade in trades:
        if trade.ticker not in holdings:
            holdings[trade.ticker] = {"shares": Decimal("0"), "cost": Decimal("0")}

        if trade.trade_type == "buy":
            holdings[trade.ticker]["shares"] += trade.shares
            holdings[trade.ticker]["cost"] += trade.shares * trade.price
        else:
            holdings[trade.ticker]["shares"] -= trade.shares
            holdings[trade.ticker]["cost"] -= trade.shares * trade.price

    # Filter active holdings
    active_holdings = {k: v for k, v in holdings.items() if v["shares"] > 0}

    # Get current prices
    portfolio_value = Decimal("0")
    if active_holdings:
        polygon = get_polygon_service()
        tickers = list(active_holdings.keys())
        snapshots = polygon.get_market_snapshot(tickers)

        for ticker, holding in active_holdings.items():
            snapshot = snapshots.get(ticker, {})
            current_price = Decimal(str(snapshot.get("price", 0) or 0))
            portfolio_value += holding["shares"] * current_price

    total_value = float(account.balance) + float(portfolio_value)
    total_pnl = total_value - float(INITIAL_BALANCE)
    total_pnl_pct = (total_pnl / float(INITIAL_BALANCE)) * 100

    # Calculate win rate from closed trades
    buy_trades = [t for t in trades if t.trade_type == "buy"]
    sell_trades = [t for t in trades if t.trade_type == "sell"]

    # Match buys and sells to calculate wins
    wins = 0
    losses = 0

    for ticker in set(t.ticker for t in trades):
        ticker_buys = [t for t in buy_trades if t.ticker == ticker]
        ticker_sells = [t for t in sell_trades if t.ticker == ticker]

        if ticker_buys and ticker_sells:
            avg_buy = sum(float(t.price) for t in ticker_buys) / len(ticker_buys)
            avg_sell = sum(float(t.price) for t in ticker_sells) / len(ticker_sells)

            if avg_sell > avg_buy:
                wins += 1
            else:
                losses += 1

    total_closed = wins + losses
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

    # Calculate trades per day (activity score)
    if trades:
        first_trade = min(t.trade_date for t in trades)
        days_active = max(1, (datetime.now(timezone.utc) - first_trade).days)
        trades_per_day = len(trades) / days_active
    else:
        trades_per_day = 0

    return {
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl_pct, 2),
        "cash": float(account.balance),
        "portfolio_value": float(portfolio_value),
        "total_trades": len(trades),
        "win_rate": round(win_rate, 1),
        "wins": wins,
        "losses": losses,
        "trades_per_day": round(trades_per_day, 2),
        "positions_count": len(active_holdings),
        "days_since_reset": (datetime.now(timezone.utc) - account.last_reset).days if account.last_reset else 0
    }

def get_user_rank(user_id: int, rankings: list) -> int:
    """Get user's rank from rankings list"""
    for i, r in enumerate(rankings):
        if r["user_id"] == user_id:
            return i + 1
    return 0

def get_badge(pnl_pct: float, trades: int, win_rate: float) -> dict:
    """Determine user's achievement badge"""
    badges = []

    # Performance badges
    if pnl_pct >= 100:
        badges.append({"name": "Double Up", "icon": "🚀", "color": "#fbbf24"})
    elif pnl_pct >= 50:
        badges.append({"name": "High Flyer", "icon": "✈️", "color": "#60a5fa"})
    elif pnl_pct >= 25:
        badges.append({"name": "Strong Start", "icon": "💪", "color": "#34d399"})
    elif pnl_pct >= 10:
        badges.append({"name": "Green Thumb", "icon": "🌱", "color": "#22c55e"})

    # Activity badges
    if trades >= 100:
        badges.append({"name": "Active Trader", "icon": "⚡", "color": "#a855f7"})
    elif trades >= 50:
        badges.append({"name": "Regular", "icon": "📈", "color": "#06b6d4"})

    # Win rate badges
    if win_rate >= 70 and trades >= 10:
        badges.append({"name": "Sharpshooter", "icon": "🎯", "color": "#ef4444"})
    elif win_rate >= 60 and trades >= 10:
        badges.append({"name": "Consistent", "icon": "📊", "color": "#f97316"})

    return badges[0] if badges else {"name": "Beginner", "icon": "🌟", "color": "#94a3b8"}

@api_leaderboard.route("/api/leaderboard")
@cache.cached(timeout=60, query_string=True)
def get_leaderboard():
    """
    Get paper trading leaderboard

    Query params:
    - period: 'all', 'week', 'month' (default: 'all')
    - limit: number of results (default: 50, max: 100)
    """
    period = request.args.get("period", "all")
    limit = min(int(request.args.get("limit", 50)), 100)

    # Get all paper accounts
    accounts = PaperAccount.query.all()

    rankings = []
    for account in accounts:
        user = User.query.get(account.user_id)
        if not user:
            continue

        # Filter by period
        if period == "week":
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            if account.last_reset and account.last_reset < cutoff:
                continue
        elif period == "month":
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            if account.last_reset and account.last_reset < cutoff:
                continue

        metrics = calculate_user_metrics(account.user_id)
        if not metrics:
            continue

        badge = get_badge(metrics["total_pnl_pct"], metrics["total_trades"], metrics["win_rate"])

        rankings.append({
            "user_id": account.user_id,
            "username": user.username,
            "total_value": metrics["total_value"],
            "total_pnl": metrics["total_pnl"],
            "total_pnl_pct": metrics["total_pnl_pct"],
            "win_rate": metrics["win_rate"],
            "total_trades": metrics["total_trades"],
            "badge": badge,
            "days_active": metrics["days_since_reset"]
        })

    # Sort by total P&L percentage (best performance)
    rankings.sort(key=lambda x: x["total_pnl_pct"], reverse=True)
    rankings = rankings[:limit]

    # Add rank
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    return jsonify({
        "success": True,
        "period": period,
        "rankings": rankings,
        "total_traders": len(accounts),
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

@api_leaderboard.route("/api/leaderboard/me")
@login_required
def get_my_ranking():
    """Get current user's ranking and stats"""
    metrics = calculate_user_metrics(current_user.id)

    if not metrics:
        return jsonify({
            "success": True,
            "has_account": False,
            "message": "Start paper trading to appear on the leaderboard!"
        })

    # Get user's rank
    accounts = PaperAccount.query.all()
    all_rankings = []

    for account in accounts:
        user_metrics = calculate_user_metrics(account.user_id)
        if user_metrics:
            all_rankings.append({
                "user_id": account.user_id,
                "total_pnl_pct": user_metrics["total_pnl_pct"]
            })

    all_rankings.sort(key=lambda x: x["total_pnl_pct"], reverse=True)
    rank = get_user_rank(current_user.id, all_rankings)

    badge = get_badge(metrics["total_pnl_pct"], metrics["total_trades"], metrics["win_rate"])

    return jsonify({
        "success": True,
        "has_account": True,
        "rank": rank,
        "total_traders": len(all_rankings),
        "percentile": round((1 - rank / len(all_rankings)) * 100, 1) if all_rankings else 0,
        "metrics": metrics,
        "badge": badge,
        "username": current_user.username
    })

@api_leaderboard.route("/api/leaderboard/top-performers")
@cache.cached(timeout=300)
def get_top_performers():
    """Get top performers with detailed stats for homepage display"""
    accounts = PaperAccount.query.all()

    performers = []
    for account in accounts:
        user = User.query.get(account.user_id)
        if not user:
            continue

        metrics = calculate_user_metrics(account.user_id)
        if not metrics or metrics["total_trades"] < 3:  # Minimum 3 trades
            continue

        badge = get_badge(metrics["total_pnl_pct"], metrics["total_trades"], metrics["win_rate"])

        performers.append({
            "username": user.username,
            "total_pnl_pct": metrics["total_pnl_pct"],
            "win_rate": metrics["win_rate"],
            "total_trades": metrics["total_trades"],
            "badge": badge
        })

    # Sort and get top 5
    performers.sort(key=lambda x: x["total_pnl_pct"], reverse=True)
    top_5 = performers[:5]

    for i, p in enumerate(top_5):
        p["rank"] = i + 1

    return jsonify({
        "success": True,
        "top_performers": top_5
    })

@api_leaderboard.route("/api/leaderboard/stats")
@cache.cached(timeout=300)
def get_leaderboard_stats():
    """Get overall leaderboard statistics"""
    accounts = PaperAccount.query.all()

    total_traders = len(accounts)
    total_volume = Decimal("0")
    profitable_traders = 0
    total_trades = 0

    for account in accounts:
        metrics = calculate_user_metrics(account.user_id)
        if metrics:
            total_volume += Decimal(str(metrics["total_value"]))
            if metrics["total_pnl"] > 0:
                profitable_traders += 1
            total_trades += metrics["total_trades"]

    return jsonify({
        "success": True,
        "stats": {
            "total_traders": total_traders,
            "total_volume": float(total_volume),
            "profitable_traders": profitable_traders,
            "profitable_rate": round(profitable_traders / total_traders * 100, 1) if total_traders > 0 else 0,
            "total_trades": total_trades,
            "avg_trades_per_trader": round(total_trades / total_traders, 1) if total_traders > 0 else 0
        }
    })

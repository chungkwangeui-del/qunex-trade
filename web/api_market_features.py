"""
Market Features API - Extended Hours, Sector Heatmap, Performance Analytics
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.database import db, Transaction, Watchlist
from web.polygon_service import get_polygon_service
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

api_market_features = Blueprint('api_market_features', __name__)


# ============================================================================
# EXTENDED HOURS (PREMARKET/AFTERHOURS) ENDPOINTS
# ============================================================================

@api_market_features.route("/api/market/extended-hours/<ticker>")
@login_required
def get_extended_hours(ticker):
    """Get premarket/afterhours data for a single ticker"""
    try:
        polygon = get_polygon_service()
        data = polygon.get_extended_hours_data(ticker.upper())

        if not data:
            return jsonify({
                "success": False,
                "error": f"No extended hours data available for {ticker}"
            }), 404

        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"Error fetching extended hours for {ticker}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_market_features.route("/api/market/extended-hours/watchlist")
@login_required
def get_extended_hours_watchlist():
    """Get extended hours data for user's watchlist"""
    try:
        watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
        tickers = [w.ticker for w in watchlist]

        if not tickers:
            return jsonify({
                "success": True,
                "data": {},
                "market_status": None
            })

        polygon = get_polygon_service()

        # Get market status
        market_status = polygon.get_market_status()

        # Get extended hours data for all tickers
        extended_data = polygon.get_extended_hours_bulk(tickers)

        return jsonify({
            "success": True,
            "data": extended_data,
            "market_status": market_status
        })
    except Exception as e:
        logger.error(f"Error fetching extended hours for watchlist: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_market_features.route("/api/market/status")
def get_market_status():
    """Get current market status (open, closed, pre-market, post-market)"""
    try:
        polygon = get_polygon_service()
        status = polygon.get_market_status()

        if not status:
            return jsonify({
                "success": False,
                "error": "Unable to fetch market status"
            }), 500

        return jsonify({
            "success": True,
            "status": status
        })
    except Exception as e:
        logger.error(f"Error fetching market status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# SECTOR HEATMAP ENDPOINTS
# ============================================================================

@api_market_features.route("/api/market/sector-heatmap")
@login_required
def get_sector_heatmap():
    """
    Get sector performance data for heatmap visualization.
    Returns all 11 GICS sectors with their performance metrics.
    """
    try:
        polygon = get_polygon_service()
        sectors = polygon.get_sector_performance()

        if not sectors:
            return jsonify({
                "success": False,
                "error": "Unable to fetch sector data"
            }), 500

        # Calculate overall market stats
        total_change = sum(s.get("change_percent", 0) for s in sectors)
        avg_change = total_change / len(sectors) if sectors else 0

        # Determine market sentiment
        gainers = len([s for s in sectors if s.get("change_percent", 0) > 0])
        losers = len([s for s in sectors if s.get("change_percent", 0) < 0])

        if gainers > 8:
            sentiment = "bullish"
        elif losers > 8:
            sentiment = "bearish"
        else:
            sentiment = "mixed"

        # Find best and worst performers
        sorted_sectors = sorted(sectors, key=lambda x: x.get("change_percent", 0), reverse=True)
        best_sector = sorted_sectors[0] if sorted_sectors else None
        worst_sector = sorted_sectors[-1] if sorted_sectors else None

        return jsonify({
            "success": True,
            "sectors": sectors,
            "summary": {
                "avg_change": round(avg_change, 2),
                "gainers": gainers,
                "losers": losers,
                "sentiment": sentiment,
                "best_sector": {
                    "name": best_sector.get("sector"),
                    "change_percent": best_sector.get("change_percent")
                } if best_sector else None,
                "worst_sector": {
                    "name": worst_sector.get("sector"),
                    "change_percent": worst_sector.get("change_percent")
                } if worst_sector else None
            }
        })
    except Exception as e:
        logger.error(f"Error fetching sector heatmap: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# PERFORMANCE ANALYTICS ENDPOINTS
# ============================================================================

@api_market_features.route("/api/portfolio/analytics")
@login_required
def get_portfolio_analytics():
    """
    Get comprehensive portfolio performance analytics.

    Calculates:
    - Win rate
    - Average gain/loss
    - Best/worst trades
    - Daily/weekly/monthly P&L
    - Performance by ticker
    - Risk metrics
    """
    try:
        user_id = current_user.id

        # Get all transactions
        transactions = Transaction.query.filter_by(user_id=user_id)\
            .order_by(Transaction.transaction_date.asc()).all()

        if not transactions:
            return jsonify({
                "success": True,
                "analytics": {
                    "total_trades": 0,
                    "message": "No transactions to analyze"
                }
            })

        polygon = get_polygon_service()

        # Build position history and calculate realized P&L
        positions = defaultdict(lambda: {"shares": 0, "cost_basis": 0, "buys": [], "sells": []})
        realized_trades = []

        for txn in transactions:
            ticker = txn.ticker
            shares = float(txn.shares)
            price = float(txn.price)

            if txn.transaction_type == "buy":
                positions[ticker]["shares"] += shares
                positions[ticker]["cost_basis"] += shares * price
                positions[ticker]["buys"].append({
                    "shares": shares,
                    "price": price,
                    "date": txn.transaction_date
                })
            else:  # sell
                if positions[ticker]["shares"] > 0:
                    # Calculate average cost at time of sale
                    avg_cost = positions[ticker]["cost_basis"] / positions[ticker]["shares"]

                    # Calculate realized P&L for this sale
                    realized_pnl = (price - avg_cost) * shares
                    realized_pct = ((price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

                    realized_trades.append({
                        "ticker": ticker,
                        "shares": shares,
                        "buy_price": avg_cost,
                        "sell_price": price,
                        "pnl": realized_pnl,
                        "pnl_percent": realized_pct,
                        "date": txn.transaction_date,
                        "is_win": realized_pnl > 0
                    })

                    # Update position
                    positions[ticker]["shares"] -= shares
                    positions[ticker]["cost_basis"] -= shares * avg_cost
                    positions[ticker]["sells"].append({
                        "shares": shares,
                        "price": price,
                        "date": txn.transaction_date
                    })

        # Calculate win/loss metrics
        wins = [t for t in realized_trades if t["is_win"]]
        losses = [t for t in realized_trades if not t["is_win"]]

        total_realized = len(realized_trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_realized * 100) if total_realized > 0 else 0

        # Average gain/loss
        avg_win = sum(t["pnl"] for t in wins) / win_count if win_count > 0 else 0
        avg_loss = sum(t["pnl"] for t in losses) / loss_count if loss_count > 0 else 0
        avg_win_pct = sum(t["pnl_percent"] for t in wins) / win_count if win_count > 0 else 0
        avg_loss_pct = sum(t["pnl_percent"] for t in losses) / loss_count if loss_count > 0 else 0

        # Best and worst trades
        sorted_by_pnl = sorted(realized_trades, key=lambda x: x["pnl"], reverse=True)
        best_trades = sorted_by_pnl[:5] if sorted_by_pnl else []
        worst_trades = sorted_by_pnl[-5:][::-1] if sorted_by_pnl else []

        # Total realized P&L
        total_realized_pnl = sum(t["pnl"] for t in realized_trades)

        # Calculate unrealized P&L for current holdings
        current_holdings = []
        total_unrealized_pnl = 0
        total_current_value = 0
        total_cost = 0

        for ticker, pos in positions.items():
            if pos["shares"] > 0:
                try:
                    quote = polygon.get_stock_quote(ticker)
                    current_price = quote.get("price", 0) if quote else 0
                except:
                    current_price = 0

                avg_cost = pos["cost_basis"] / pos["shares"] if pos["shares"] > 0 else 0
                current_value = pos["shares"] * current_price
                unrealized_pnl = current_value - pos["cost_basis"]
                unrealized_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

                current_holdings.append({
                    "ticker": ticker,
                    "shares": pos["shares"],
                    "avg_cost": avg_cost,
                    "current_price": current_price,
                    "current_value": current_value,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pct": unrealized_pct
                })

                total_unrealized_pnl += unrealized_pnl
                total_current_value += current_value
                total_cost += pos["cost_basis"]

        # Performance by ticker
        ticker_performance = defaultdict(lambda: {"realized_pnl": 0, "trades": 0, "wins": 0})
        for trade in realized_trades:
            ticker = trade["ticker"]
            ticker_performance[ticker]["realized_pnl"] += trade["pnl"]
            ticker_performance[ticker]["trades"] += 1
            if trade["is_win"]:
                ticker_performance[ticker]["wins"] += 1

        # Convert to list and calculate win rates
        ticker_stats = []
        for ticker, stats in ticker_performance.items():
            win_rate_ticker = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
            ticker_stats.append({
                "ticker": ticker,
                "realized_pnl": stats["realized_pnl"],
                "trades": stats["trades"],
                "wins": stats["wins"],
                "win_rate": win_rate_ticker
            })

        # Sort by realized P&L
        ticker_stats.sort(key=lambda x: x["realized_pnl"], reverse=True)

        # Profit factor (gross profit / gross loss)
        gross_profit = sum(t["pnl"] for t in wins) if wins else 0
        gross_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0)

        # Risk/Reward ratio
        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Monthly P&L breakdown
        monthly_pnl = defaultdict(float)
        for trade in realized_trades:
            if trade["date"]:
                month_key = trade["date"].strftime("%Y-%m")
                monthly_pnl[month_key] += trade["pnl"]

        # Convert to sorted list
        monthly_breakdown = [
            {"month": k, "pnl": v}
            for k, v in sorted(monthly_pnl.items())
        ]

        return jsonify({
            "success": True,
            "analytics": {
                # Summary
                "total_trades": total_realized,
                "total_transactions": len(transactions),
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": round(win_rate, 1),

                # P&L
                "total_realized_pnl": round(total_realized_pnl, 2),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "total_pnl": round(total_realized_pnl + total_unrealized_pnl, 2),

                # Portfolio value
                "total_current_value": round(total_current_value, 2),
                "total_cost_basis": round(total_cost, 2),

                # Averages
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "avg_win_percent": round(avg_win_pct, 2),
                "avg_loss_percent": round(avg_loss_pct, 2),

                # Risk metrics
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
                "risk_reward_ratio": round(risk_reward, 2),

                # Trades
                "best_trades": [
                    {
                        "ticker": t["ticker"],
                        "pnl": round(t["pnl"], 2),
                        "pnl_percent": round(t["pnl_percent"], 2),
                        "date": t["date"].isoformat() if t["date"] else None
                    } for t in best_trades
                ],
                "worst_trades": [
                    {
                        "ticker": t["ticker"],
                        "pnl": round(t["pnl"], 2),
                        "pnl_percent": round(t["pnl_percent"], 2),
                        "date": t["date"].isoformat() if t["date"] else None
                    } for t in worst_trades
                ],

                # By ticker
                "ticker_performance": ticker_stats[:10],  # Top 10

                # Monthly
                "monthly_pnl": monthly_breakdown[-12:],  # Last 12 months

                # Current holdings
                "current_holdings": sorted(
                    current_holdings,
                    key=lambda x: x["current_value"],
                    reverse=True
                )
            }
        })
    except Exception as e:
        logger.error(f"Error calculating portfolio analytics: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_market_features.route("/api/portfolio/performance-chart")
@login_required
def get_performance_chart():
    """
    Get portfolio value over time for charting.
    Returns daily portfolio value based on transaction history.
    """
    try:
        user_id = current_user.id
        days = request.args.get("days", 30, type=int)

        # Get all transactions
        transactions = Transaction.query.filter_by(user_id=user_id)\
            .order_by(Transaction.transaction_date.asc()).all()

        if not transactions:
            return jsonify({
                "success": True,
                "data": []
            })

        # Build daily portfolio value
        # This is simplified - tracks cost basis over time
        daily_values = []
        positions = defaultdict(lambda: {"shares": 0, "cost": 0})

        start_date = transactions[0].transaction_date.date() if transactions else datetime.now().date()
        end_date = datetime.now().date()

        # Limit to requested days
        if days:
            start_date = max(start_date, end_date - timedelta(days=days))

        current_date = start_date
        txn_idx = 0

        while current_date <= end_date:
            # Process any transactions on this date
            while txn_idx < len(transactions):
                txn = transactions[txn_idx]
                txn_date = txn.transaction_date.date() if txn.transaction_date else None

                if txn_date and txn_date <= current_date:
                    ticker = txn.ticker
                    shares = float(txn.shares)
                    price = float(txn.price)

                    if txn.transaction_type == "buy":
                        positions[ticker]["shares"] += shares
                        positions[ticker]["cost"] += shares * price
                    else:
                        if positions[ticker]["shares"] > 0:
                            avg_cost = positions[ticker]["cost"] / positions[ticker]["shares"]
                            positions[ticker]["shares"] -= shares
                            positions[ticker]["cost"] -= shares * avg_cost

                    txn_idx += 1
                else:
                    break

            # Calculate total portfolio value (cost basis) for this date
            total_cost = sum(p["cost"] for p in positions.values())

            daily_values.append({
                "date": current_date.isoformat(),
                "value": round(total_cost, 2)
            })

            current_date += timedelta(days=1)

        return jsonify({
            "success": True,
            "data": daily_values
        })
    except Exception as e:
        logger.error(f"Error generating performance chart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

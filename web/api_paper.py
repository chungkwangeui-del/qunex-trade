"""
Paper Trading API - Practice trading with virtual money
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.database import db, PaperAccount, PaperTrade
from web.polygon_service import get_polygon_service
from web.extensions import csrf
from decimal import Decimal
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

api_paper = Blueprint("api_paper", __name__)
csrf.exempt(api_paper)

INITIAL_BALANCE = Decimal("100000.00")  # $100k starting balance


def get_or_create_account(user_id):
    """Get user's paper account or create one"""
    account = PaperAccount.query.filter_by(user_id=user_id).first()
    if not account:
        account = PaperAccount(
            user_id=user_id,
            balance=INITIAL_BALANCE,
            initial_balance=INITIAL_BALANCE
        )
        db.session.add(account)
        db.session.commit()
    return account


def get_paper_holdings(user_id):
    """Calculate current paper holdings from trades"""
    trades = PaperTrade.query.filter_by(user_id=user_id, is_closed=False).all()

    holdings = {}
    for trade in trades:
        ticker = trade.ticker
        if ticker not in holdings:
            holdings[ticker] = {"shares": Decimal("0"), "cost_basis": Decimal("0")}

        if trade.trade_type == "buy":
            holdings[ticker]["shares"] += trade.shares
            holdings[ticker]["cost_basis"] += trade.shares * trade.price
        else:  # sell
            holdings[ticker]["shares"] -= trade.shares
            holdings[ticker]["cost_basis"] -= trade.shares * trade.price

    # Filter out zero holdings
    return {k: v for k, v in holdings.items() if v["shares"] > 0}


@api_paper.route("/api/paper/account", methods=["GET"])
@login_required
def get_account():
    """Get paper trading account info"""
    account = get_or_create_account(current_user.id)
    holdings = get_paper_holdings(current_user.id)

    # Get current prices for holdings
    polygon = get_polygon_service()
    tickers = list(holdings.keys())

    portfolio_value = Decimal("0")
    holdings_list = []

    if tickers:
        snapshots = polygon.get_market_snapshot(tickers)

        for ticker, holding in holdings.items():
            snapshot = snapshots.get(ticker, {})
            current_price = Decimal(str(snapshot.get("price", 0) or 0))
            shares = holding["shares"]
            cost_basis = holding["cost_basis"]

            market_value = shares * current_price
            avg_cost = cost_basis / shares if shares > 0 else Decimal("0")
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else Decimal("0")

            portfolio_value += market_value

            holdings_list.append({
                "ticker": ticker,
                "shares": float(shares),
                "avg_cost": float(avg_cost),
                "current_price": float(current_price),
                "market_value": float(market_value),
                "cost_basis": float(cost_basis),
                "unrealized_pnl": float(unrealized_pnl),
                "unrealized_pnl_pct": float(unrealized_pnl_pct),
            })

    total_value = float(account.balance) + float(portfolio_value)
    total_pnl = total_value - float(account.initial_balance)
    total_pnl_pct = (total_pnl / float(account.initial_balance) * 100) if account.initial_balance > 0 else 0

    return jsonify({
        "success": True,
        "account": {
            "cash": float(account.balance),
            "portfolio_value": float(portfolio_value),
            "total_value": total_value,
            "initial_balance": float(account.initial_balance),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "last_reset": account.last_reset.isoformat() if account.last_reset else None,
        },
        "holdings": holdings_list,
    })


@api_paper.route("/api/paper/trade", methods=["POST"])
@login_required
def execute_trade():
    """Execute a paper trade (buy or sell)"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    ticker = data.get("ticker", "").upper().strip()
    shares = data.get("shares")
    trade_type = data.get("trade_type", "").lower()
    notes = data.get("notes", "")

    # Validation
    if not ticker:
        return jsonify({"success": False, "message": "Ticker is required"}), 400

    if not shares or shares <= 0:
        return jsonify({"success": False, "message": "Shares must be greater than 0"}), 400

    if trade_type not in ["buy", "sell"]:
        return jsonify({"success": False, "message": "Trade type must be 'buy' or 'sell'"}), 400

    # Get current price
    polygon = get_polygon_service()
    snapshot = polygon.get_snapshot(ticker)

    if not snapshot or not snapshot.get("price"):
        return jsonify({"success": False, "message": f"Could not get price for {ticker}"}), 400

    price = Decimal(str(snapshot["price"]))
    shares = Decimal(str(shares))
    total_cost = shares * price

    account = get_or_create_account(current_user.id)

    if trade_type == "buy":
        # Check if enough cash
        if total_cost > account.balance:
            return jsonify({
                "success": False,
                "message": f"Insufficient funds. Need ${total_cost:.2f}, have ${account.balance:.2f}"
            }), 400

        # Deduct from balance
        account.balance -= total_cost

    else:  # sell
        # Check if enough shares
        holdings = get_paper_holdings(current_user.id)
        current_shares = holdings.get(ticker, {}).get("shares", Decimal("0"))

        if shares > current_shares:
            return jsonify({
                "success": False,
                "message": f"Insufficient shares. Have {current_shares}, trying to sell {shares}"
            }), 400

        # Add to balance
        account.balance += total_cost

    # Create trade record
    trade = PaperTrade(
        user_id=current_user.id,
        ticker=ticker,
        shares=shares,
        price=price,
        trade_type=trade_type,
        notes=notes,
    )

    db.session.add(trade)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Successfully {trade_type} {shares} shares of {ticker} @ ${price:.2f}",
        "trade": trade.to_dict(),
        "new_balance": float(account.balance),
    })


@api_paper.route("/api/paper/trades", methods=["GET"])
@login_required
def get_trades():
    """Get paper trading history"""
    limit = request.args.get("limit", 50, type=int)

    trades = PaperTrade.query.filter_by(user_id=current_user.id)\
        .order_by(PaperTrade.trade_date.desc())\
        .limit(limit)\
        .all()

    return jsonify({
        "success": True,
        "trades": [t.to_dict() for t in trades],
    })


@api_paper.route("/api/paper/reset", methods=["POST"])
@login_required
def reset_account():
    """Reset paper trading account to initial balance"""
    account = get_or_create_account(current_user.id)

    # Delete all trades
    PaperTrade.query.filter_by(user_id=current_user.id).delete()

    # Reset balance
    account.balance = INITIAL_BALANCE
    account.last_reset = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Account reset to $100,000",
        "balance": float(account.balance),
    })

"""
Portfolio API endpoints for managing user holdings and transactions.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.database import db, Transaction, User
from web.polygon_service import get_polygon_service
from web.extensions import csrf, cache
from src.services.async_http_service import AsyncHttpClient
import asyncio
from datetime import datetime, timezone
from sqlalchemy import func
from decimal import Decimal
from collections import defaultdict
import logging
import json
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

api_portfolio = Blueprint('api_portfolio', __name__)
csrf.exempt(api_portfolio)

def run_async(coro):
    """Run a coroutine from synchronous code"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@cache.memoize(timeout=300)
def get_current_price(ticker):
    """
    Get current price for a ticker with caching.
    Tries multiple sources: Polygon snapshot, Polygon previous close, Twelve Data
    """
    # Try Polygon snapshot first
    try:
        polygon = get_polygon_service()
        snapshot = polygon.get_snapshot(ticker)
        if snapshot and snapshot.get("price"):
            return float(snapshot["price"])
    except Exception as e:
        logger.info(f"Polygon snapshot error for {ticker}: {e}")

    # Try Polygon previous close
    try:
        polygon = get_polygon_service()
        prev_close = polygon.get_previous_close(ticker)
        if prev_close and prev_close.get("close"):
            return float(prev_close["close"])
    except Exception as e:
        logger.info(f"Polygon prev_close error for {ticker}: {e}")

    # Try Twelve Data (800 calls/day free - best backup!)
    try:
        twelvedata_key = os.getenv("TWELVEDATA_API_KEY", "")
        if twelvedata_key:
            url = "https://api.twelvedata.com/quote"
            data = run_async(AsyncHttpClient.get(url, params={"symbol": ticker, "apikey": twelvedata_key}, timeout=10))
            if data and not data.get("code") and data.get("close"):
                return float(data["close"])
    except Exception as e:
        logger.info(f"Twelve Data API error for {ticker}: {e}")

    # Try Finnhub as last resort
    try:
        finnhub_key = os.getenv("FINNHUB_API_KEY", "")
        if finnhub_key:
            url = "https://finnhub.io/api/v1/quote"
            data = run_async(AsyncHttpClient.get(url, params={"symbol": ticker, "token": finnhub_key}, timeout=5))
            if data and data.get("c", 0) > 0:
                return float(data["c"])
    except Exception as e:
        logger.info(f"Finnhub API error for {ticker}: {e}")

    return 0.0

@api_portfolio.route("/api/portfolio")
@login_required
def get_portfolio():
    """Get user's portfolio with holdings and transactions"""
    user_id = current_user.id

    # Get all transactions for the user
    transactions = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.transaction_date.desc()).all()

    # Calculate holdings from transactions
    holdings_map = {}

    for t in transactions:
        ticker = t.ticker
        shares = float(t.shares)
        price = float(t.price)

        if ticker not in holdings_map:
            holdings_map[ticker] = {
                'ticker': ticker,
                'shares': 0,
                'total_cost': 0,
                'buy_count': 0
            }

        if t.transaction_type == 'buy':
            holdings_map[ticker]['shares'] += shares
            holdings_map[ticker]['total_cost'] += shares * price
            holdings_map[ticker]['buy_count'] += 1
        else:  # sell
            holdings_map[ticker]['shares'] -= shares
            # Reduce cost basis proportionally
            if holdings_map[ticker]['shares'] > 0:
                avg_cost = holdings_map[ticker]['total_cost'] / (holdings_map[ticker]['shares'] + shares)
                holdings_map[ticker]['total_cost'] = holdings_map[ticker]['shares'] * avg_cost
            else:
                holdings_map[ticker]['total_cost'] = 0

    # Filter out holdings with 0 or negative shares
    holdings = []
    total_value = 0
    total_cost = 0

    for ticker, data in holdings_map.items():
        if data['shares'] > 0:
            current_price = get_current_price(ticker)
            avg_cost = data['total_cost'] / data['shares'] if data['shares'] > 0 else 0
            value = data['shares'] * current_price

            holdings.append({
                'id': ticker,  # Use ticker as ID for simplicity
                'ticker': ticker,
                'name': '',  # Could fetch from API if needed
                'shares': data['shares'],
                'avg_cost': avg_cost,
                'current_price': current_price,
                'value': value,
                'gain': (current_price - avg_cost) * data['shares'],
                'gain_percent': ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
            })

            total_value += value
            total_cost += data['total_cost']

    # Sort by value descending
    holdings.sort(key=lambda x: x['value'], reverse=True)

    # Format transactions for response
    transactions_list = []
    for t in transactions[:50]:  # Limit to last 50
        transactions_list.append({
            'id': t.id,
            'ticker': t.ticker,
            'type': t.transaction_type,
            'shares': float(t.shares),
            'price': float(t.price),
            'date': t.transaction_date.isoformat() if t.transaction_date else None,
            'total': float(t.shares) * float(t.price)
        })

    return jsonify({
        'success': True,
        'holdings': holdings,
        'transactions': transactions_list,
        'total_value': total_value,
        'total_cost': total_cost,
        'total_gain': total_value - total_cost,
        'total_gain_percent': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    })

@api_portfolio.route("/api/portfolio/transaction", methods=['POST'])
@login_required
def add_transaction():
    """Add a new transaction (buy or sell)"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    ticker = data.get('ticker', '').upper().strip()
    shares = data.get('shares')
    price = data.get('price')
    transaction_type = data.get('transaction_type', 'buy').lower()
    transaction_date = data.get('date')

    # Validation
    if not ticker:
        return jsonify({'success': False, 'message': 'Ticker is required'}), 400

    if not shares or shares <= 0:
        return jsonify({'success': False, 'message': 'Shares must be greater than 0'}), 400

    if not price or price <= 0:
        return jsonify({'success': False, 'message': 'Price must be greater than 0'}), 400

    if transaction_type not in ['buy', 'sell']:
        return jsonify({'success': False, 'message': 'Transaction type must be buy or sell'}), 400

    # For sell transactions, validate user has enough shares
    if transaction_type == 'sell':
        current_shares = get_user_shares(current_user.id, ticker)
        if shares > current_shares:
            return jsonify({
                'success': False,
                'message': f'Cannot sell {shares} shares. You only own {current_shares} shares of {ticker}'
            }), 400

    # Parse date
    if transaction_date:
        try:
            transaction_date = datetime.fromisoformat(transaction_date.replace('Z', '+00:00'))
        except ValueError:
            try:
                transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d')
            except ValueError:
                transaction_date = datetime.now(timezone.utc)
    else:
        transaction_date = datetime.now(timezone.utc)

    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        ticker=ticker,
        shares=Decimal(str(shares)),
        price=Decimal(str(price)),
        transaction_type=transaction_type,
        transaction_date=transaction_date
    )

    db.session.add(transaction)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding transaction: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    return jsonify({
        'success': True,
        'message': f'Successfully added {transaction_type} transaction for {shares} shares of {ticker}',
        'transaction': transaction.to_dict()
    })

@api_portfolio.route("/api/portfolio/holding/<ticker>", methods=['PUT'])
@login_required
def update_holding(ticker):
    """Update a holding (replace all transactions for this ticker with a single buy)"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    shares = data.get('shares')
    price = data.get('price')  # This will be the new average cost

    if not shares or shares <= 0:
        return jsonify({'success': False, 'message': 'Shares must be greater than 0'}), 400

    if not price or price <= 0:
        return jsonify({'success': False, 'message': 'Price must be greater than 0'}), 400

    ticker = ticker.upper()

    # Delete all existing transactions for this ticker
    Transaction.query.filter_by(user_id=current_user.id, ticker=ticker).delete()

    # Create a single buy transaction with the new values
    transaction = Transaction(
        user_id=current_user.id,
        ticker=ticker,
        shares=Decimal(str(shares)),
        price=Decimal(str(price)),
        transaction_type='buy',
        transaction_date=datetime.now(timezone.utc)
    )

    db.session.add(transaction)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating holding: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    return jsonify({
        'success': True,
        'message': f'Successfully updated holding for {ticker}'
    })

@api_portfolio.route("/api/portfolio/holding/<ticker>", methods=['DELETE'])
@login_required
def delete_holding(ticker):
    """Delete all transactions for a ticker (remove holding)"""
    ticker = ticker.upper()

    deleted = Transaction.query.filter_by(user_id=current_user.id, ticker=ticker).delete()
    db.session.commit()

    if deleted:
        return jsonify({
            'success': True,
            'message': f'Successfully deleted all transactions for {ticker}'
        })
    else:
        return jsonify({
            'success': False,
            'message': f'No transactions found for {ticker}'
        }), 404

@api_portfolio.route("/api/portfolio/transactions", methods=['GET'])
@login_required
def get_transactions():
    """Get all transactions (trade journal)"""
    # Optional filters
    ticker = request.args.get('ticker', '').upper().strip()
    transaction_type = request.args.get('type', '').lower()
    limit = request.args.get('limit', 50, type=int)

    query = Transaction.query.filter_by(user_id=current_user.id)

    if ticker:
        query = query.filter_by(ticker=ticker)

    if transaction_type in ['buy', 'sell']:
        query = query.filter_by(transaction_type=transaction_type)

    transactions = query.order_by(Transaction.transaction_date.desc()).limit(limit).all()

    # Calculate stats
    total_buys = sum(float(t.shares * t.price) for t in transactions if t.transaction_type == 'buy')
    total_sells = sum(float(t.shares * t.price) for t in transactions if t.transaction_type == 'sell')

    return jsonify({
        'success': True,
        'transactions': [t.to_dict() for t in transactions],
        'stats': {
            'total_transactions': len(transactions),
            'total_buys': total_buys,
            'total_sells': total_sells,
            'net_invested': total_buys - total_sells
        }
    })

@api_portfolio.route("/api/portfolio/transaction/<int:transaction_id>", methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    """Delete a specific transaction"""
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()

    if not transaction:
        return jsonify({'success': False, 'message': 'Transaction not found'}), 404

    ticker = transaction.ticker
    db.session.delete(transaction)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Transaction for {ticker} deleted successfully'
    })

def get_user_shares(user_id, ticker):
    """Calculate current shares owned by user for a ticker"""
    transactions = Transaction.query.filter_by(user_id=user_id, ticker=ticker.upper()).all()

    total_shares = 0
    for t in transactions:
        if t.transaction_type == 'buy':
            total_shares += float(t.shares)
        else:
            total_shares -= float(t.shares)

    return max(0, total_shares)

@api_portfolio.route("/api/portfolio/analysis", methods=['GET'])
@login_required
def portfolio_analysis():
    """
    Get comprehensive portfolio analysis including:
    - Sector allocation
    - Performance metrics
    - Risk indicators
    - Top performers/losers
    """
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    if not transactions:
        return jsonify({
            'success': True,
            'message': 'No transactions found',
            'analysis': None
        })

    # Calculate holdings
    holdings = defaultdict(lambda: {"shares": Decimal("0"), "cost_basis": Decimal("0")})

    for txn in transactions:
        ticker = txn.ticker
        shares = Decimal(str(txn.shares))
        price = Decimal(str(txn.price))

        if txn.transaction_type == "buy":
            holdings[ticker]["shares"] += shares
            holdings[ticker]["cost_basis"] += shares * price
        elif txn.transaction_type == "sell":
            holdings[ticker]["shares"] -= shares
            if holdings[ticker]["shares"] > 0:
                avg_cost = holdings[ticker]["cost_basis"] / (holdings[ticker]["shares"] + shares)
                holdings[ticker]["cost_basis"] -= shares * avg_cost

    current_holdings = {ticker: data for ticker, data in holdings.items() if data["shares"] > 0}

    if not current_holdings:
        return jsonify({
            'success': True,
            'message': 'No current holdings',
            'analysis': None
        })

    # Get current prices and company details
    polygon = get_polygon_service()
    tickers = list(current_holdings.keys())
    snapshots = polygon.get_market_snapshot(tickers)

    # Build portfolio analysis
    positions = []
    total_value = Decimal("0")
    total_cost = Decimal("0")
    sector_allocation = defaultdict(lambda: Decimal("0"))
    daily_pnl = Decimal("0")

    for ticker, holding in current_holdings.items():
        snapshot = snapshots.get(ticker, {})
        current_price = Decimal(str(snapshot.get("price", 0) or 0))

        shares = holding["shares"]
        cost_basis = holding["cost_basis"]
        current_value = shares * current_price
        pnl = current_value - cost_basis
        pnl_pct = float(pnl / cost_basis * 100) if cost_basis > 0 else 0

        # Get ticker details for sector
        details = polygon.get_ticker_details(ticker)
        sector = details.get("sector", "Unknown") if details else "Unknown"

        positions.append({
            "ticker": ticker,
            "shares": float(shares),
            "avg_cost": float(cost_basis / shares) if shares > 0 else 0,
            "current_price": float(current_price),
            "current_value": float(current_value),
            "cost_basis": float(cost_basis),
            "pnl": float(pnl),
            "pnl_pct": pnl_pct,
            "sector": sector,
            "weight": 0,  # Will calculate after total
            "daily_change": snapshot.get("change_percent", 0),
        })

        total_value += current_value
        total_cost += cost_basis
        sector_allocation[sector] += current_value

        # Daily P&L
        daily_change = Decimal(str(snapshot.get("todaysChange", 0) or 0))
        daily_pnl += shares * daily_change

    # Calculate weights and sort
    for pos in positions:
        pos["weight"] = float(Decimal(str(pos["current_value"])) / total_value * 100) if total_value > 0 else 0

    # Sort by weight
    positions.sort(key=lambda x: x["weight"], reverse=True)

    # Top performers and losers
    sorted_by_pnl = sorted(positions, key=lambda x: x["pnl_pct"], reverse=True)
    top_performers = sorted_by_pnl[:3]
    worst_performers = sorted_by_pnl[-3:] if len(sorted_by_pnl) >= 3 else sorted_by_pnl

    # Sector breakdown
    sector_breakdown = [
        {"sector": sector, "value": float(value), "weight": float(value / total_value * 100) if total_value > 0 else 0}
        for sector, value in sorted(sector_allocation.items(), key=lambda x: x[1], reverse=True)
    ]

    # Portfolio metrics
    total_pnl = total_value - total_cost
    total_pnl_pct = float(total_pnl / total_cost * 100) if total_cost > 0 else 0

    # Diversity score (1 - Herfindahl Index)
    herfindahl = sum((pos["weight"] / 100) ** 2 for pos in positions)
    diversity_score = round((1 - herfindahl) * 100, 1)

    return jsonify({
        'success': True,
        'analysis': {
            'summary': {
                'total_value': float(total_value),
                'total_cost': float(total_cost),
                'total_pnl': float(total_pnl),
                'total_pnl_pct': total_pnl_pct,
                'daily_pnl': float(daily_pnl),
                'num_positions': len(positions),
                'diversity_score': diversity_score,
            },
            'positions': positions,
            'sector_allocation': sector_breakdown,
            'top_performers': top_performers,
            'worst_performers': worst_performers,
        }
    })

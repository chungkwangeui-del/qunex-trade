"""
Portfolio API endpoints for managing user holdings and transactions.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.database import db, Transaction
from web.polygon_service import get_polygon_service
from datetime import datetime
from sqlalchemy import func
from decimal import Decimal

api_portfolio = Blueprint('api_portfolio', __name__)


def get_current_price(ticker):
    """Get current price for a ticker from Polygon API"""
    try:
        polygon = get_polygon_service()
        quote = polygon.get_previous_close(ticker)
        if quote and 'results' in quote and len(quote['results']) > 0:
            return float(quote['results'][0].get('c', 0))
    except Exception as e:
        print(f"Error getting price for {ticker}: {e}")
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
                transaction_date = datetime.utcnow()
    else:
        transaction_date = datetime.utcnow()

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
    db.session.commit()

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
        transaction_date=datetime.utcnow()
    )

    db.session.add(transaction)
    db.session.commit()

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

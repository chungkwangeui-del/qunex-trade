"""
Watchlist API endpoints
Manage user stock watchlists with real-time data
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database import db, Watchlist
from polygon_service import get_polygon_service
from datetime import datetime
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

api_watchlist = Blueprint('api_watchlist', __name__)

@api_watchlist.route('/api/watchlist', methods=['GET'])
@login_required
def get_watchlist() -> Tuple[Any, int]:
    """
    Get user's watchlist with real-time quotes.

    Returns:
        JSON array of watchlist items with real-time data
    """
    try:
        watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).order_by(Watchlist.added_at.desc()).all()

        if not watchlist_items:
            return jsonify([])

        polygon = get_polygon_service()
        results = []

        for item in watchlist_items:
            # Get current price and previous close to calculate changes
            quote = polygon.get_stock_quote(item.ticker)
            prev_data = polygon.get_previous_close(item.ticker)

            stock_data = {
                'id': item.id,
                'ticker': item.ticker,
                'company_name': item.company_name,
                'notes': item.notes,
                'added_at': item.added_at.isoformat(),
                'alert_price_above': item.alert_price_above,
                'alert_price_below': item.alert_price_below
            }

            if quote and prev_data:
                current_price = quote.get('price')
                prev_close = prev_data.get('close')

                # Calculate change and change_percent
                change = current_price - prev_close if (current_price and prev_close) else 0
                change_percent = (change / prev_close * 100) if prev_close else 0

                stock_data.update({
                    'price': current_price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': prev_data.get('volume'),
                    'high': prev_data.get('high'),
                    'low': prev_data.get('low'),
                    'open': prev_data.get('open'),
                    'prev_close': prev_close
                })
            elif prev_data:
                # Use previous close data only
                stock_data.update({
                    'price': prev_data.get('close'),
                    'change': 0,
                    'change_percent': 0,
                    'volume': prev_data.get('volume'),
                    'high': prev_data.get('high'),
                    'low': prev_data.get('low'),
                    'open': prev_data.get('open'),
                    'prev_close': prev_data.get('close')
                })
            else:
                stock_data.update({
                    'price': 0,
                    'change': 0,
                    'change_percent': 0,
                    'volume': 0,
                    'error': 'Quote data unavailable'
                })

            results.append(stock_data)

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_watchlist.route('/api/watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add a stock to watchlist"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper().strip()

        if not ticker:
            return jsonify({'error': 'Ticker is required'}), 400

        # Check if already in watchlist
        existing = Watchlist.query.filter_by(user_id=current_user.id, ticker=ticker).first()
        if existing:
            return jsonify({'error': 'Stock already in watchlist'}), 400

        # Get company name (use ticker as fallback)
        company_name = data.get('company_name', ticker)

        # Create watchlist entry
        watchlist_item = Watchlist(
            user_id=current_user.id,
            ticker=ticker,
            company_name=company_name,
            notes=data.get('notes', ''),
            alert_price_above=data.get('alert_price_above'),
            alert_price_below=data.get('alert_price_below')
        )

        db.session.add(watchlist_item)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{ticker} added to watchlist',
            'id': watchlist_item.id,
            'ticker': ticker,
            'company_name': company_name
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding to watchlist: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_watchlist.route('/api/watchlist/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_watchlist(item_id):
    """Remove a stock from watchlist"""
    try:
        item = Watchlist.query.filter_by(id=item_id, user_id=current_user.id).first()

        if not item:
            return jsonify({'error': 'Watchlist item not found'}), 404

        ticker = item.ticker
        db.session.delete(item)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{ticker} removed from watchlist'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing from watchlist: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_watchlist.route('/api/watchlist/<int:item_id>', methods=['PUT'])
@login_required
def update_watchlist_item(item_id):
    """Update watchlist item (notes, alerts)"""
    try:
        item = Watchlist.query.filter_by(id=item_id, user_id=current_user.id).first()

        if not item:
            return jsonify({'error': 'Watchlist item not found'}), 404

        data = request.get_json()

        # Update allowed fields
        if 'notes' in data:
            item.notes = data['notes']
        if 'alert_price_above' in data:
            item.alert_price_above = data['alert_price_above']
        if 'alert_price_below' in data:
            item.alert_price_below = data['alert_price_below']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Watchlist item updated',
            'ticker': item.ticker
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating watchlist item: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_watchlist.route('/api/watchlist/stats', methods=['GET'])
@login_required
def get_watchlist_stats():
    """Get watchlist statistics (total P/L, best/worst performers)"""
    try:
        watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()

        if not watchlist_items:
            return jsonify({
                'total_stocks': 0,
                'gainers': 0,
                'losers': 0,
                'best_performer': None,
                'worst_performer': None
            })

        polygon = get_polygon_service()
        gainers = 0
        losers = 0
        best_performer = None
        worst_performer = None
        best_change = float('-inf')
        worst_change = float('inf')

        for item in watchlist_items:
            # Get current price and previous close to calculate change
            quote = polygon.get_stock_quote(item.ticker)
            prev_data = polygon.get_previous_close(item.ticker)

            if quote and prev_data:
                current_price = quote.get('price')
                prev_close = prev_data.get('close')

                if current_price and prev_close:
                    change = current_price - prev_close
                    change_pct = (change / prev_close * 100)

                    if change_pct > 0:
                        gainers += 1
                    elif change_pct < 0:
                        losers += 1

                    if change_pct > best_change:
                        best_change = change_pct
                        best_performer = {
                            'ticker': item.ticker,
                            'change_percent': change_pct,
                            'price': current_price
                        }

                    if change_pct < worst_change:
                        worst_change = change_pct
                        worst_performer = {
                            'ticker': item.ticker,
                            'change_percent': change_pct,
                            'price': current_price
                        }

        return jsonify({
            'total_stocks': len(watchlist_items),
            'gainers': gainers,
            'losers': losers,
            'neutral': len(watchlist_items) - gainers - losers,
            'best_performer': best_performer,
            'worst_performer': worst_performer
        })

    except Exception as e:
        logger.error(f"Error getting watchlist stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

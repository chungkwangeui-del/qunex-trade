"""
Polygon.io Market Data API Endpoints
Real-time market data routes for frontend
"""

from flask import Blueprint, jsonify, request
from web.polygon_service import get_polygon_service
from datetime import datetime, timedelta

api_polygon = Blueprint('api_polygon', __name__)


@api_polygon.route('/api/market/quote/<ticker>')
def get_quote(ticker):
    """Get latest quote for a stock"""
    polygon = get_polygon_service()
    quote = polygon.get_stock_quote(ticker.upper())

    if not quote:
        return jsonify({'error': 'Quote not found'}), 404

    return jsonify(quote)


@api_polygon.route('/api/market/previous-close/<ticker>')
def get_prev_close(ticker):
    """Get previous day's close data"""
    polygon = get_polygon_service()
    data = polygon.get_previous_close(ticker.upper())

    if not data:
        return jsonify({'error': 'Data not found'}), 404

    return jsonify(data)


@api_polygon.route('/api/market/history/<ticker>')
def get_history(ticker):
    """
    Get historical data
    Query params:
      - days: Number of days (default 30)
      - timespan: minute/hour/day/week/month (default day)
    """
    days = int(request.args.get('days', 30))
    timespan = request.args.get('timespan', 'day')

    from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    to_date = datetime.now().strftime('%Y-%m-%d')

    polygon = get_polygon_service()
    data = polygon.get_aggregates(
        ticker.upper(),
        multiplier=1,
        timespan=timespan,
        from_date=from_date,
        to_date=to_date,
        limit=500
    )

    if not data:
        return jsonify({'error': 'Data not found'}), 404

    return jsonify({
        'ticker': ticker.upper(),
        'timespan': timespan,
        'data': data
    })


@api_polygon.route('/api/market/snapshot')
def get_snapshot():
    """
    Get snapshot of multiple tickers
    Query params:
      - tickers: Comma-separated list (e.g., AAPL,MSFT,GOOGL)
    """
    tickers_str = request.args.get('tickers', '')
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]

    if not tickers:
        return jsonify({'error': 'No tickers provided'}), 400

    polygon = get_polygon_service()
    snapshot = polygon.get_market_snapshot(tickers)

    return jsonify(snapshot)


@api_polygon.route('/api/market/gainers')
def get_gainers():
    """Get top gainers"""
    polygon = get_polygon_service()
    gainers = polygon.get_gainers_losers('gainers')

    return jsonify({
        'count': len(gainers),
        'data': gainers
    })


@api_polygon.route('/api/market/losers')
def get_losers():
    """Get top losers"""
    polygon = get_polygon_service()
    losers = polygon.get_gainers_losers('losers')

    return jsonify({
        'count': len(losers),
        'data': losers
    })


@api_polygon.route('/api/market/status')
def get_market_status():
    """Get current market status"""
    polygon = get_polygon_service()
    status = polygon.get_market_status()

    if not status:
        return jsonify({'error': 'Status not available'}), 500

    return jsonify(status)


@api_polygon.route('/api/market/search')
def search_tickers():
    """
    Search for tickers
    Query params:
      - q: Search query (ticker symbol or company name)
      - limit: Max results (default 10)
    """
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))

    if not query:
        return jsonify({'error': 'Query required'}), 400

    polygon = get_polygon_service()
    results = polygon.search_tickers(query, limit)

    return jsonify({
        'query': query,
        'count': len(results),
        'results': results
    })


@api_polygon.route('/api/market/details/<ticker>')
def get_ticker_details(ticker):
    """Get detailed information about a ticker"""
    polygon = get_polygon_service()
    details = polygon.get_ticker_details(ticker.upper())

    if not details:
        return jsonify({'error': 'Ticker not found'}), 404

    return jsonify(details)


@api_polygon.route('/api/market/technicals/<ticker>')
def get_technicals(ticker):
    """Get technical indicators for a stock"""
    days = int(request.args.get('days', 50))

    polygon = get_polygon_service()
    technicals = polygon.get_technical_indicators(ticker.upper(), days)

    if not technicals:
        return jsonify({'error': 'Data not available'}), 404

    return jsonify(technicals)


@api_polygon.route('/api/market/sector-map')
def get_sector_map():
    """
    Get real-time sector map data
    Uses top stocks from each sector
    """
    # Major stocks by sector
    sector_stocks = {
        'Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'ADBE', 'AMD'],
        'Healthcare': ['LLY', 'UNH', 'JNJ', 'ABBV', 'MRK'],
        'Financials': ['BRK-B', 'JPM', 'V', 'MA', 'BAC'],
        'Consumer Disc.': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'],
        'Communication': ['GOOGL', 'META', 'NFLX', 'DIS'],
        'Industrials': ['GE', 'CAT', 'RTX', 'UPS'],
        'Consumer Staples': ['WMT', 'PG', 'KO', 'PEP'],
        'Energy': ['XOM', 'CVX', 'COP'],
        'Utilities': ['NEE', 'DUK', 'SO'],
        'Real Estate': ['PLD', 'AMT', 'CCI'],
        'Materials': ['LIN', 'APD', 'ECL']
    }

    # Collect all tickers
    all_tickers = []
    for stocks in sector_stocks.values():
        all_tickers.extend(stocks)

    # Get snapshot data
    polygon = get_polygon_service()
    snapshot = polygon.get_market_snapshot(all_tickers)

    # Build sector map
    stocks = []
    for sector, tickers in sector_stocks.items():
        for ticker in tickers:
            if ticker in snapshot:
                data = snapshot[ticker]
                stocks.append({
                    'ticker': ticker,
                    'name': ticker,  # Could be enhanced with company name
                    'sector': sector,
                    'price': data.get('price'),
                    'marketCap': data.get('day_volume', 0) * data.get('price', 0) / 1000,  # Rough estimate
                    'change': data.get('change_percent', 0),
                    'volume': data.get('day_volume', 0)
                })

    return jsonify({'stocks': stocks})


@api_polygon.route('/api/market/movers')
def get_movers():
    """Get both gainers and losers"""
    polygon = get_polygon_service()

    gainers = polygon.get_gainers_losers('gainers')
    losers = polygon.get_gainers_losers('losers')

    return jsonify({
        'gainers': gainers[:10],  # Top 10
        'losers': losers[:10],  # Top 10
        'timestamp': datetime.now().isoformat()
    })


@api_polygon.route('/api/market/batch-quotes')
def get_batch_quotes():
    """
    Get quotes for multiple tickers
    Query params:
      - tickers: Comma-separated list
    """
    tickers_str = request.args.get('tickers', '')
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]

    if not tickers:
        return jsonify({'error': 'No tickers provided'}), 400

    polygon = get_polygon_service()

    # Get quotes for each ticker
    quotes = {}
    for ticker in tickers:
        quote = polygon.get_stock_quote(ticker)
        if quote:
            quotes[ticker] = quote

    return jsonify({
        'count': len(quotes),
        'quotes': quotes,
        'timestamp': datetime.now().isoformat()
    })

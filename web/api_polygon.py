"""
Polygon.io Market Data API Endpoints
Real-time market data routes for frontend
"""

from flask import Blueprint, jsonify, request, make_response
from datetime import datetime, timedelta
import csv
import io

try:
    from polygon_service import get_polygon_service
    from app import cache
except ImportError:
    from web.polygon_service import get_polygon_service
    from web.app import cache

api_polygon = Blueprint("api_polygon", __name__)


@api_polygon.route("/api/market/quote/<ticker>")
def get_quote(ticker):
    """
    Get latest real-time quote for a stock.

    Args:
        ticker (str): Stock ticker symbol

    Returns:
        flask.Response: JSON quote data or error with 404 status
    """
    polygon = get_polygon_service()
    quote = polygon.get_stock_quote(ticker.upper())

    if not quote:
        return jsonify({"error": "Quote not found"}), 404

    return jsonify(quote)


@api_polygon.route("/api/market/previous-close/<ticker>")
def get_prev_close(ticker):
    """
    Get previous trading day's closing data for a stock.

    Args:
        ticker (str): Stock ticker symbol

    Returns:
        flask.Response: JSON previous close data or error with 404 status
    """
    polygon = get_polygon_service()
    data = polygon.get_previous_close(ticker.upper())

    if not data:
        return jsonify({"error": "Data not found"}), 404

    return jsonify(data)


@api_polygon.route("/api/market/history/<ticker>")
def get_history(ticker):
    """
    Get historical data
    Query params:
      - days: Number of days (default 30)
      - timespan: minute/hour/day/week/month (default day)
    """
    days = int(request.args.get("days", 30))
    timespan = request.args.get("timespan", "day")

    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    polygon = get_polygon_service()
    data = polygon.get_aggregates(
        ticker.upper(),
        multiplier=1,
        timespan=timespan,
        from_date=from_date,
        to_date=to_date,
        limit=500,
    )

    if not data:
        return jsonify({"error": "Data not found"}), 404

    return jsonify({"ticker": ticker.upper(), "timespan": timespan, "data": data})


@api_polygon.route("/api/market/snapshot")
def get_snapshot():
    """
    Get real-time snapshot data for multiple tickers.

    Query Parameters:
        tickers (str): Comma-separated list of ticker symbols
            Example: "AAPL,MSFT,GOOGL"

    Returns:
        flask.Response: JSON dict with ticker symbols as keys and
            quote data as values, or error with 400 if no tickers provided
    """
    tickers_str = request.args.get("tickers", "")
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]

    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    polygon = get_polygon_service()
    snapshot = polygon.get_market_snapshot(tickers)

    return jsonify(snapshot)


@api_polygon.route("/api/market/gainers")
def get_gainers():
    """
    Get top gaining stocks for the current trading day.

    Returns:
        flask.Response: JSON with count and array of top gainers
    """
    polygon = get_polygon_service()
    gainers = polygon.get_gainers_losers("gainers")

    return jsonify({"count": len(gainers), "data": gainers})


@api_polygon.route("/api/market/losers")
def get_losers():
    """
    Get top losing stocks for the current trading day.

    Returns:
        flask.Response: JSON with count and array of top losers
    """
    polygon = get_polygon_service()
    losers = polygon.get_gainers_losers("losers")

    return jsonify({"count": len(losers), "data": losers})


@api_polygon.route("/api/market/status")
def get_market_status():
    """
    Get current market status (open/closed/extended hours).

    Returns:
        flask.Response: JSON market status data or error with 500 status
    """
    polygon = get_polygon_service()
    status = polygon.get_market_status()

    if not status:
        return jsonify({"error": "Status not available"}), 500

    return jsonify(status)


@api_polygon.route("/api/market/search")
def search_tickers():
    """
    Search for tickers
    Query params:
      - q: Search query (ticker symbol or company name)
      - limit: Max results (default 10)
    """
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 10))

    if not query:
        return jsonify({"error": "Query required"}), 400

    polygon = get_polygon_service()
    results = polygon.search_tickers(query, limit)

    return jsonify({"query": query, "count": len(results), "results": results})


@api_polygon.route("/api/market/details/<ticker>")
def get_ticker_details(ticker):
    """
    Get detailed company information for a ticker.

    Includes company name, description, market cap, sector, industry, etc.

    Args:
        ticker (str): Stock ticker symbol

    Returns:
        flask.Response: JSON ticker details or error with 404 status
    """
    polygon = get_polygon_service()
    details = polygon.get_ticker_details(ticker.upper())

    if not details:
        return jsonify({"error": "Ticker not found"}), 404

    return jsonify(details)


@api_polygon.route("/api/market/technicals/<ticker>")
def get_technicals(ticker):
    """
    Calculate and return technical indicators for a stock.

    Computes RSI, MACD, moving averages, and other technical indicators
    based on historical price data.

    Args:
        ticker (str): Stock ticker symbol

    Query Parameters:
        days (int, optional): Number of days of data to analyze (default: 50)

    Returns:
        flask.Response: JSON technical indicators or error with 404 status
    """
    days = int(request.args.get("days", 50))

    polygon = get_polygon_service()
    technicals = polygon.get_technical_indicators(ticker.upper(), days)

    if not technicals:
        return jsonify({"error": "Data not available"}), 404

    return jsonify(technicals)


@api_polygon.route("/api/market/sector-map")
def get_sector_map():
    """
    Get real-time sector map data
    Uses top stocks from each sector
    """
    # Major stocks by sector
    sector_stocks = {
        "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "AMD"],
        "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
        "Financials": ["BRK-B", "JPM", "V", "MA", "BAC"],
        "Consumer Disc.": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
        "Communication": ["GOOGL", "META", "NFLX", "DIS"],
        "Industrials": ["GE", "CAT", "RTX", "UPS"],
        "Consumer Staples": ["WMT", "PG", "KO", "PEP"],
        "Energy": ["XOM", "CVX", "COP"],
        "Utilities": ["NEE", "DUK", "SO"],
        "Real Estate": ["PLD", "AMT", "CCI"],
        "Materials": ["LIN", "APD", "ECL"],
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
                stocks.append(
                    {
                        "ticker": ticker,
                        "name": ticker,  # Could be enhanced with company name
                        "sector": sector,
                        "price": data.get("price"),
                        "marketCap": data.get("day_volume", 0)
                        * data.get("price", 0)
                        / 1000,  # Rough estimate
                        "change": data.get("change_percent", 0),
                        "volume": data.get("day_volume", 0),
                    }
                )

    return jsonify({"stocks": stocks})


@api_polygon.route("/api/market/movers")
@cache.cached(timeout=300, key_prefix="market_movers")  # Cache for 5 minutes
def get_movers():
    """
    Get both top gainers and top losers for the trading day.

    Returns:
        flask.Response: JSON with separate arrays for top 10 gainers
            and top 10 losers, plus timestamp
    """
    polygon = get_polygon_service()

    gainers = polygon.get_gainers_losers("gainers")
    losers = polygon.get_gainers_losers("losers")

    return jsonify(
        {
            "gainers": gainers[:10],  # Top 10
            "losers": losers[:10],  # Top 10
            "timestamp": datetime.now().isoformat(),
        }
    )


@api_polygon.route("/api/market/batch-quotes")
def get_batch_quotes():
    """
    Get real-time quotes for multiple tickers in one request.

    Query Parameters:
        tickers (str): Comma-separated list of ticker symbols
            Example: "AAPL,MSFT,GOOGL"

    Returns:
        flask.Response: JSON with:
            - count (int): Number of successful quotes
            - quotes (dict): Dict with ticker symbols as keys
            - timestamp (str): ISO timestamp of request
            - error (str): Error message if no tickers provided (400 status)
    """
    tickers_str = request.args.get("tickers", "")
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]

    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    polygon = get_polygon_service()

    # Get quotes for each ticker
    quotes = {}
    for ticker in tickers:
        quote = polygon.get_stock_quote(ticker)
        if quote:
            quotes[ticker] = quote

    return jsonify(
        {"count": len(quotes), "quotes": quotes, "timestamp": datetime.now().isoformat()}
    )


@api_polygon.route("/api/market/indices")
def get_indices():
    """
    Get real-time data for major market indices.

    Returns data for S&P 500, NASDAQ Composite, Dow Jones Industrial Average,
    Russell 2000, and VIX volatility index.

    Returns:
        flask.Response: JSON with indices dict and timestamp, or
            error with 500 status if data unavailable
    """
    polygon = get_polygon_service()
    indices = polygon.get_market_indices()

    if not indices:
        return jsonify({"error": "Indices data not available"}), 500

    return jsonify({"indices": indices, "timestamp": datetime.now().isoformat()})


@api_polygon.route("/api/market/sectors")
def get_sectors():
    """
    Get performance data for all market sectors.

    Calculates aggregate performance for each of the 11 major sectors
    (Technology, Healthcare, Financials, etc.) based on top stocks.

    Returns:
        flask.Response: JSON with:
            - sectors (list): Array of sector performance data
            - count (int): Number of sectors
            - timestamp (str): ISO timestamp
            - error (str): Error message if unavailable (500 status)
    """
    polygon = get_polygon_service()
    sectors = polygon.get_sector_performance()

    if not sectors:
        return jsonify({"error": "Sector data not available"}), 500

    return jsonify(
        {"sectors": sectors, "count": len(sectors), "timestamp": datetime.now().isoformat()}
    )


@api_polygon.route("/api/market/health")
def health_check():
    """
    Health check endpoint to verify Polygon API configuration.

    Tests if API key is configured and makes a test API call to verify
    connectivity and authentication.

    Returns:
        flask.Response: JSON with:
            - api_key_configured (bool): Whether API key is set
            - api_key_preview (str): First 8 chars of API key or "NOT SET"
            - api_working (bool): Whether test API call succeeded
            - market_status (dict): Market status response or error details
            - timestamp (str): ISO timestamp
    """
    import os

    polygon = get_polygon_service()

    # Check API key
    api_key_set = bool(os.getenv("POLYGON_API_KEY"))
    api_key_preview = f"{os.getenv('POLYGON_API_KEY', '')[:8]}..." if api_key_set else "NOT SET"

    # Try a simple API call
    try:
        status = polygon.get_market_status()
        api_working = status is not None
    except Exception as e:
        api_working = False
        status = {"error": str(e)}

    return jsonify(
        {
            "api_key_configured": api_key_set,
            "api_key_preview": api_key_preview,
            "api_working": api_working,
            "market_status": status,
            "timestamp": datetime.now().isoformat(),
        }
    )


@api_polygon.route("/api/market/screener")
def stock_screener():
    """
    Screen stocks based on criteria
    Query params:
      - min_volume: Minimum volume
      - min_price: Minimum price
      - max_price: Maximum price
      - min_change_percent: Minimum % change
      - max_change_percent: Maximum % change
    """
    criteria = {}

    # Parse criteria from query params
    if request.args.get("min_volume"):
        criteria["min_volume"] = int(request.args.get("min_volume"))
    if request.args.get("min_price"):
        criteria["min_price"] = float(request.args.get("min_price"))
    if request.args.get("max_price"):
        criteria["max_price"] = float(request.args.get("max_price"))
    if request.args.get("min_change_percent"):
        criteria["min_change_percent"] = float(request.args.get("min_change_percent"))
    if request.args.get("max_change_percent"):
        criteria["max_change_percent"] = float(request.args.get("max_change_percent"))

    polygon = get_polygon_service()
    results = polygon.screen_stocks(criteria)

    return jsonify(
        {
            "criteria": criteria,
            "count": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    )


@api_polygon.route("/api/market/screener/export")
def export_screener_csv():
    """
    Export stock screener results to CSV file.

    Uses same filtering criteria as /api/market/screener endpoint.

    Query Parameters:
        min_volume (int, optional): Minimum trading volume
        min_price (float, optional): Minimum stock price
        max_price (float, optional): Maximum stock price
        min_change_percent (float, optional): Minimum % change
        max_change_percent (float, optional): Maximum % change

    Returns:
        flask.Response: CSV file download with screener results
            Filename format: screener_results_YYYYMMDD_HHMMSS.csv
    """
    criteria = {}

    # Parse criteria from query params
    if request.args.get("min_volume"):
        criteria["min_volume"] = int(request.args.get("min_volume"))
    if request.args.get("min_price"):
        criteria["min_price"] = float(request.args.get("min_price"))
    if request.args.get("max_price"):
        criteria["max_price"] = float(request.args.get("max_price"))
    if request.args.get("min_change_percent"):
        criteria["min_change_percent"] = float(request.args.get("min_change_percent"))
    if request.args.get("max_change_percent"):
        criteria["max_change_percent"] = float(request.args.get("max_change_percent"))

    polygon = get_polygon_service()
    results = polygon.screen_stocks(criteria)

    # Create CSV in memory
    si = io.StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        ["Ticker", "Price", "Change", "Change %", "Volume", "Market Cap", "Day High", "Day Low"]
    )

    # Write data
    for stock in results:
        writer.writerow(
            [
                stock.get("ticker", ""),
                f"${stock.get('price', 0):.2f}",
                f"{stock.get('change', 0):.2f}",
                f"{stock.get('change_percent', 0):.2f}%",
                f"{stock.get('volume', 0):,}",
                f"${stock.get('market_cap', 0):,.0f}",
                f"${stock.get('day_high', 0):.2f}",
                f"${stock.get('day_low', 0):.2f}",
            ]
        )

    # Create response
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = (
        f"attachment; filename=screener_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    output.headers["Content-type"] = "text/csv"

    return output

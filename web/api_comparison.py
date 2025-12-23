"""
Stock Comparison API

Compare multiple stocks side by side on key metrics.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from datetime import datetime
import logging

try:
    from web.polygon_service import get_polygon_service
    from web.extensions import cache
except ImportError:
    from polygon_service import get_polygon_service
    from extensions import cache

logger = logging.getLogger(__name__)

api_comparison = Blueprint("api_comparison", __name__)


@api_comparison.route("/api/compare/stocks")
@login_required
def compare_stocks():
    """
    Compare multiple stocks on key metrics.
    
    Query params:
        tickers: str - Comma-separated list of tickers (2-5 stocks)
        
    Returns comparison of:
    - Price & performance
    - Valuation ratios
    - Financial metrics
    - Technical indicators
    """
    tickers_str = request.args.get("tickers", "")
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
    
    if len(tickers) < 2:
        return jsonify({"error": "At least 2 tickers required"}), 400
    
    if len(tickers) > 5:
        return jsonify({"error": "Maximum 5 tickers allowed"}), 400
    
    comparison = []
    polygon = get_polygon_service()
    
    for ticker in tickers:
        try:
            stock_data = _get_stock_comparison_data(ticker, polygon)
            if stock_data:
                comparison.append(stock_data)
        except Exception as e:
            logger.error(f"Error getting data for {ticker}: {e}")
            comparison.append({"ticker": ticker, "error": str(e)})
    
    # Calculate rankings
    rankings = _calculate_rankings(comparison)
    
    return jsonify({
        "tickers": tickers,
        "comparison": comparison,
        "rankings": rankings,
        "timestamp": datetime.now().isoformat(),
    })


def _get_stock_comparison_data(ticker: str, polygon) -> dict:
    """Get comprehensive data for a single stock."""
    try:
        import yfinance as yf
    except ImportError:
        # Fallback to Polygon only
        return _get_polygon_only_data(ticker, polygon)
    
    # Get Polygon data (real-time)
    quote = polygon.get_stock_quote(ticker)
    details = polygon.get_ticker_details(ticker)
    technicals = polygon.get_technical_indicators(ticker, days=50)
    
    # Get Yahoo Finance data (fundamentals)
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
    except Exception:
        info = {}
    
    current_price = quote.get("price", 0) if quote else 0
    
    return {
        "ticker": ticker,
        "name": details.get("name") if details else info.get("shortName", ticker),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        
        # Price data
        "price": current_price,
        "market_cap": info.get("marketCap"),
        "market_cap_formatted": _format_large_number(info.get("marketCap")),
        
        # Performance
        "change_1d": info.get("regularMarketChangePercent"),
        "change_5d": _calculate_change(stock, 5) if 'stock' in dir() else None,
        "change_1m": _calculate_change(stock, 22) if 'stock' in dir() else None,
        "change_ytd": info.get("ytdReturn"),
        "change_1y": info.get("52WeekChange"),
        "high_52w": info.get("fiftyTwoWeekHigh"),
        "low_52w": info.get("fiftyTwoWeekLow"),
        "from_52w_high": _pct_from_high(current_price, info.get("fiftyTwoWeekHigh")),
        
        # Valuation
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "ps_ratio": info.get("priceToSalesTrailing12Months"),
        "pb_ratio": info.get("priceToBook"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        
        # Financials
        "revenue": info.get("totalRevenue"),
        "revenue_formatted": _format_large_number(info.get("totalRevenue")),
        "revenue_growth": info.get("revenueGrowth"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        
        # Dividends
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        
        # Technical
        "sma_20": technicals.get("sma_20") if technicals else None,
        "sma_50": technicals.get("sma_50") if technicals else None,
        "rsi_14": technicals.get("rsi_14") if technicals else None,
        "above_sma_20": current_price > technicals.get("sma_20", 0) if technicals and technicals.get("sma_20") else None,
        "above_sma_50": current_price > technicals.get("sma_50", 0) if technicals and technicals.get("sma_50") else None,
        
        # Volume
        "avg_volume": info.get("averageVolume"),
        "avg_volume_formatted": _format_large_number(info.get("averageVolume")),
        
        # Analyst
        "target_price": info.get("targetMeanPrice"),
        "upside_potential": _calculate_upside(current_price, info.get("targetMeanPrice")),
        "recommendation": info.get("recommendationKey"),
        "analyst_count": info.get("numberOfAnalystOpinions"),
    }


def _get_polygon_only_data(ticker: str, polygon) -> dict:
    """Fallback when yfinance is not available."""
    quote = polygon.get_stock_quote(ticker)
    details = polygon.get_ticker_details(ticker)
    technicals = polygon.get_technical_indicators(ticker, days=50)
    
    return {
        "ticker": ticker,
        "name": details.get("name") if details else ticker,
        "price": quote.get("price", 0) if quote else 0,
        "market_cap": details.get("market_cap") if details else None,
        "sma_20": technicals.get("sma_20") if technicals else None,
        "sma_50": technicals.get("sma_50") if technicals else None,
        "rsi_14": technicals.get("rsi_14") if technicals else None,
    }


def _calculate_rankings(stocks: list) -> dict:
    """Calculate rankings for each metric."""
    if not stocks or len(stocks) < 2:
        return {}
    
    # Filter out stocks with errors
    valid_stocks = [s for s in stocks if "error" not in s]
    if len(valid_stocks) < 2:
        return {}
    
    rankings = {}
    
    # Metrics where higher is better
    higher_better = [
        "price", "market_cap", "change_1d", "change_1m", "change_1y",
        "revenue_growth", "profit_margin", "operating_margin", "roe", "roa",
        "dividend_yield", "upside_potential"
    ]
    
    # Metrics where lower is better
    lower_better = [
        "pe_ratio", "forward_pe", "peg_ratio", "ps_ratio", "pb_ratio",
        "ev_ebitda", "debt_to_equity", "from_52w_high"
    ]
    
    for metric in higher_better:
        values = [(s["ticker"], s.get(metric)) for s in valid_stocks if s.get(metric) is not None]
        if values:
            sorted_vals = sorted(values, key=lambda x: x[1], reverse=True)
            rankings[metric] = {v[0]: i + 1 for i, v in enumerate(sorted_vals)}
    
    for metric in lower_better:
        values = [(s["ticker"], s.get(metric)) for s in valid_stocks if s.get(metric) is not None]
        if values:
            sorted_vals = sorted(values, key=lambda x: x[1])
            rankings[metric] = {v[0]: i + 1 for i, v in enumerate(sorted_vals)}
    
    # Overall score (simple average of rankings)
    ticker_scores = {}
    for stock in valid_stocks:
        ticker = stock["ticker"]
        rank_sum = 0
        rank_count = 0
        for metric_rankings in rankings.values():
            if ticker in metric_rankings:
                rank_sum += metric_rankings[ticker]
                rank_count += 1
        if rank_count > 0:
            ticker_scores[ticker] = rank_sum / rank_count
    
    # Sort by score (lower is better)
    overall_ranking = sorted(ticker_scores.items(), key=lambda x: x[1])
    rankings["overall"] = {ticker: i + 1 for i, (ticker, _) in enumerate(overall_ranking)}
    
    return rankings


def _format_large_number(value) -> str:
    """Format large numbers (e.g., 1.5B, 250M)."""
    if value is None:
        return None
    
    try:
        value = float(value)
        if value >= 1e12:
            return f"${value / 1e12:.2f}T"
        elif value >= 1e9:
            return f"${value / 1e9:.2f}B"
        elif value >= 1e6:
            return f"${value / 1e6:.2f}M"
        elif value >= 1e3:
            return f"${value / 1e3:.2f}K"
        else:
            return f"${value:.2f}"
    except (ValueError, TypeError):
        return None


def _pct_from_high(current: float, high: float) -> float:
    """Calculate percentage from 52-week high."""
    if not current or not high or high == 0:
        return None
    return round(((current - high) / high) * 100, 2)


def _calculate_upside(current: float, target: float) -> float:
    """Calculate upside potential to analyst target."""
    if not current or not target or current == 0:
        return None
    return round(((target - current) / current) * 100, 2)


def _calculate_change(stock, days: int) -> float:
    """Calculate price change over N days."""
    try:
        hist = stock.history(period=f"{days + 5}d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            past = hist['Close'].iloc[-min(days, len(hist))]
            return round(((current - past) / past) * 100, 2)
    except Exception:
        pass
    return None


@api_comparison.route("/api/compare/quick/<ticker1>/<ticker2>")
@login_required
def quick_compare(ticker1, ticker2):
    """
    Quick comparison of two stocks - key metrics only.
    """
    ticker1 = ticker1.upper()
    ticker2 = ticker2.upper()
    
    polygon = get_polygon_service()
    
    data1 = _get_quick_comparison(ticker1, polygon)
    data2 = _get_quick_comparison(ticker2, polygon)
    
    # Determine winner for each metric
    winners = {}
    metrics = ["price", "market_cap", "pe_ratio", "rsi_14", "dividend_yield"]
    
    for metric in metrics:
        v1 = data1.get(metric)
        v2 = data2.get(metric)
        
        if v1 is None and v2 is None:
            winners[metric] = "tie"
        elif v1 is None:
            winners[metric] = ticker2
        elif v2 is None:
            winners[metric] = ticker1
        elif metric == "pe_ratio":  # Lower is better
            winners[metric] = ticker1 if v1 < v2 else ticker2
        else:  # Higher is better
            winners[metric] = ticker1 if v1 > v2 else ticker2
    
    return jsonify({
        ticker1: data1,
        ticker2: data2,
        "winners": winners,
    })


def _get_quick_comparison(ticker: str, polygon) -> dict:
    """Get quick comparison data for a stock."""
    quote = polygon.get_stock_quote(ticker)
    details = polygon.get_ticker_details(ticker)
    technicals = polygon.get_technical_indicators(ticker)
    
    # Try to get PE from yfinance
    pe_ratio = None
    dividend_yield = None
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        pe_ratio = info.get("trailingPE")
        dividend_yield = info.get("dividendYield")
    except Exception:
        pass
    
    return {
        "ticker": ticker,
        "name": details.get("name") if details else ticker,
        "price": quote.get("price") if quote else None,
        "market_cap": details.get("market_cap") if details else None,
        "pe_ratio": pe_ratio,
        "rsi_14": technicals.get("rsi_14") if technicals else None,
        "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
    }


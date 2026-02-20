"""
Earnings, IPO & Dividend Calendar API

Provides upcoming earnings, IPO dates, and dividend information.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from datetime import datetime, timedelta
import logging
import pandas as pd

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

try:
    from web.polygon_service import get_polygon_service
    from web.extensions import cache
except ImportError:
    from polygon_service import get_polygon_service
    from extensions import cache

logger = logging.getLogger(__name__)

api_earnings = Blueprint("api_earnings", __name__)

# Major stocks to track for earnings
EARNINGS_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
    "UNH", "JNJ", "V", "WMT", "JPM", "PG", "XOM", "MA", "HD", "CVX",
    "MRK", "ABBV", "PEP", "KO", "COST", "AVGO", "TMO", "MCD", "CSCO",
    "ACN", "LLY", "ABT", "CRM", "AMD", "NFLX", "INTC", "DIS", "VZ",
    "CMCSA", "ADBE", "TXN", "QCOM", "NKE", "BMY", "UPS", "RTX", "HON",
    "SBUX", "BA", "CAT", "GS", "MS", "BLK", "SCHW", "AXP", "SPGI"
]

@api_earnings.route("/api/earnings/upcoming")
@login_required
@cache.cached(timeout=3600, key_prefix="earnings_upcoming")
def get_upcoming_earnings():
    """
    Get stocks with upcoming earnings in the next 14 days.

    Uses yfinance for earnings calendar data.
    """
    if not YFINANCE_AVAILABLE:
        return jsonify({"error": "yfinance not installed"}), 500

    earnings = []
    today = datetime.now().date()

    for ticker in EARNINGS_WATCHLIST[:30]:  # Limit to avoid rate limits
        try:
            stock = yf.Ticker(ticker)

            # Get calendar info
            try:
                calendar = stock.calendar
            except Exception:
                continue

            if calendar is None or calendar.empty if hasattr(calendar, 'empty') else not calendar:
                continue

            # Handle different calendar formats
            earnings_date = None
            if isinstance(calendar, dict):
                earnings_date = calendar.get('Earnings Date')
            elif hasattr(calendar, 'get'):
                earnings_date = calendar.get('Earnings Date')

            if earnings_date is None:
                continue

            # Handle list of dates
            if isinstance(earnings_date, list) and earnings_date:
                earnings_date = earnings_date[0]

            # Convert to date if needed
            if hasattr(earnings_date, 'date'):
                earnings_date = earnings_date.date()
            elif isinstance(earnings_date, str):
                try:
                    earnings_date = datetime.strptime(earnings_date, "%Y-%m-%d").date()
                except ValueError:
                    continue

            # Check if within next 14 days
            if earnings_date and today <= earnings_date <= today + timedelta(days=14):
                # Get additional info
                info = stock.info or {}

                earnings.append({
                    "ticker": ticker,
                    "company_name": info.get("shortName", ticker),
                    "earnings_date": str(earnings_date),
                    "days_until": (earnings_date - today).days,
                    "market_cap": info.get("marketCap"),
                    "sector": info.get("sector"),
                    "eps_estimate": None,  # Would need separate API
                    "revenue_estimate": None,
                })

        except Exception as e:
            logger.debug(f"Error getting earnings for {ticker}: {e}")
            continue

    # Sort by date
    earnings.sort(key=lambda x: x["earnings_date"])

    return jsonify({
        "count": len(earnings),
        "earnings": earnings,
        "updated_at": datetime.now().isoformat(),
    })

@api_earnings.route("/api/earnings/stock/<ticker>")
@login_required
def get_stock_earnings(ticker):
    """
    Get earnings history and estimates for a specific stock.
    """
    if not YFINANCE_AVAILABLE:
        return jsonify({"error": "yfinance not installed"}), 500

    ticker = ticker.upper()

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Get earnings history
        earnings_history = []
        try:
            hist = stock.earnings_history
            if hist is not None and not hist.empty:
                for row in hist.itertuples():
                    idx = row.Index
                    earnings_history.append({
                        "date": str(idx) if hasattr(idx, '__str__') else str(idx),
                        "eps_actual": getattr(row, 'epsActual', None),
                        "eps_estimate": getattr(row, 'epsEstimate', None),
                        "surprise_pct": getattr(row, 'surprisePercent', None),
                    })
        except Exception as e:
            logger.debug(f"Error getting earnings history for {ticker}: {e}")

        # Get quarterly earnings
        quarterly = []
        try:
            q_earnings = stock.quarterly_earnings
            if q_earnings is not None and not q_earnings.empty:
                for row in q_earnings.itertuples():
                    idx = row.Index
                    quarterly.append({
                        "quarter": str(idx),
                        "revenue": getattr(row, 'Revenue', None),
                        "earnings": getattr(row, 'Earnings', None),
                    })
        except Exception as e:
            logger.debug(f"Error getting quarterly earnings for {ticker}: {e}")

        return jsonify({
            "ticker": ticker,
            "company_name": info.get("shortName", ticker),
            "earnings_history": earnings_history[-8:],  # Last 8 quarters
            "quarterly_earnings": quarterly[-8:],
            "forward_eps": info.get("forwardEps"),
            "trailing_eps": info.get("trailingEps"),
            "peg_ratio": info.get("pegRatio"),
            "forward_pe": info.get("forwardPE"),
            "trailing_pe": info.get("trailingPE"),
        })

    except Exception as e:
        logger.error(f"Error getting earnings for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@api_earnings.route("/api/dividends/upcoming")
@login_required
@cache.cached(timeout=3600, key_prefix="dividends_upcoming")
def get_upcoming_dividends():
    """
    Get stocks with upcoming ex-dividend dates.
    """
    if not YFINANCE_AVAILABLE:
        return jsonify({"error": "yfinance not installed"}), 500

    dividends = []
    today = datetime.now().date()

    # Dividend aristocrats and high-yield stocks
    div_stocks = [
        "JNJ", "PG", "KO", "PEP", "MCD", "WMT", "HD", "MMM", "ABT", "ABBV",
        "XOM", "CVX", "T", "VZ", "IBM", "MO", "PM", "O", "SCHD", "VYM",
        "SPY", "QQQ", "DIA", "IVV", "VTI"
    ]

    for ticker in div_stocks:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}

            div_yield = info.get("dividendYield", 0) or 0
            div_rate = info.get("dividendRate", 0) or 0
            ex_date = info.get("exDividendDate")

            if div_yield > 0:
                # Convert timestamp to date
                if ex_date:
                    if isinstance(ex_date, (int, float)):
                        ex_date = datetime.fromtimestamp(ex_date).date()
                    elif hasattr(ex_date, 'date'):
                        ex_date = ex_date.date()

                dividends.append({
                    "ticker": ticker,
                    "company_name": info.get("shortName", ticker),
                    "dividend_yield": round(div_yield * 100, 2),
                    "dividend_rate": div_rate,
                    "ex_dividend_date": str(ex_date) if ex_date else None,
                    "payout_ratio": info.get("payoutRatio"),
                    "five_year_avg_yield": info.get("fiveYearAvgDividendYield"),
                })

        except Exception as e:
            logger.debug(f"Error getting dividend for {ticker}: {e}")
            continue

    # Sort by yield (highest first)
    dividends.sort(key=lambda x: x["dividend_yield"], reverse=True)

    return jsonify({
        "count": len(dividends),
        "dividends": dividends,
        "updated_at": datetime.now().isoformat(),
    })

@api_earnings.route("/api/dividends/stock/<ticker>")
@login_required
def get_stock_dividends(ticker):
    """
    Get dividend history for a specific stock.
    """
    if not YFINANCE_AVAILABLE:
        return jsonify({"error": "yfinance not installed"}), 500

    ticker = ticker.upper()

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Get dividend history
        div_history = []
        try:
            dividends = stock.dividends
            if dividends is not None and len(dividends) > 0:
                for date, amount in dividends.tail(20).items():
                    div_history.append({
                        "date": str(date.date()) if hasattr(date, 'date') else str(date),
                        "amount": round(float(amount), 4),
                    })
        except Exception:
            pass

        return jsonify({
            "ticker": ticker,
            "company_name": info.get("shortName", ticker),
            "dividend_yield": round((info.get("dividendYield") or 0) * 100, 2),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            "ex_dividend_date": info.get("exDividendDate"),
            "dividend_history": div_history,
            "five_year_avg_yield": info.get("fiveYearAvgDividendYield"),
        })

    except Exception as e:
        logger.error(f"Error getting dividends for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@api_earnings.route("/api/ipo/upcoming")
@login_required
@cache.cached(timeout=3600, key_prefix="ipo_upcoming")
def get_upcoming_ipos():
    """
    Get upcoming IPOs.

    Note: IPO data requires specialized API (Finnhub, Polygon, etc.)
    This provides a framework - implement with your preferred data source.
    """
    try:
        from web.finnhub_service import get_finnhub_service
        finnhub = get_finnhub_service()

        if finnhub:
            # Get IPO calendar from Finnhub
            from_date = datetime.now().strftime("%Y-%m-%d")
            to_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            ipos = finnhub.get_ipo_calendar(from_date, to_date)

            return jsonify({
                "count": len(ipos) if ipos else 0,
                "ipos": ipos or [],
                "updated_at": datetime.now().isoformat(),
            })
    except Exception as e:
        logger.warning(f"Finnhub IPO calendar not available: {e}")

    # Fallback: Return placeholder data
    return jsonify({
        "count": 0,
        "ipos": [],
        "message": "IPO calendar requires Finnhub API. Set FINNHUB_API_KEY to enable.",
        "updated_at": datetime.now().isoformat(),
    })

@api_earnings.route("/api/calendar/economic")
@login_required
@cache.cached(timeout=1800, key_prefix="economic_calendar")
def get_economic_calendar():
    """
    Get economic calendar events.

    Returns events from the database (populated by cron job).
    """
    try:
        from web.database import EconomicEvent

        # Get events for next 7 days
        today = datetime.now().date()
        end_date = today + timedelta(days=7)

        events = EconomicEvent.query.filter(
            EconomicEvent.date >= today,
            EconomicEvent.date <= end_date
        ).order_by(EconomicEvent.date, EconomicEvent.time).all()

        return jsonify({
            "count": len(events),
            "events": [e.to_dict() for e in events],
            "updated_at": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting economic calendar: {e}")
        return jsonify({"error": str(e)}), 500

"""
Options Flow & Dark Pool API

Track unusual options activity and institutional trading.
Note: Full implementation requires specialized data feeds (Unusual Whales, FlowAlgo, etc.)
This provides the framework and uses available free data sources.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from datetime import datetime, timedelta
import logging
import pandas as pd

try:
    from web.polygon_service import get_polygon_service
    from web.extensions import cache
except ImportError:
    from polygon_service import get_polygon_service
    from extensions import cache

logger = logging.getLogger(__name__)

api_options = Blueprint("api_options", __name__)

@api_options.route("/api/options/chain/<ticker>")
@login_required
def get_options_chain(ticker):
    """
    Get options chain for a stock.

    Uses yfinance for options data (free but delayed).
    For real-time options flow, consider:
    - Unusual Whales API
    - Tradier API
    - CBOE Data
    """
    ticker = ticker.upper()

    try:
        import yfinance as yf
    except ImportError:
        return jsonify({"error": "yfinance not installed"}), 500

    try:
        stock = yf.Ticker(ticker)

        # Get available expiration dates
        expirations = stock.options

        if not expirations:
            return jsonify({"error": "No options available for this ticker"}), 404

        # Get the requested expiration or default to nearest
        exp_date = request.args.get("expiration", expirations[0])

        if exp_date not in expirations:
            return jsonify({
                "error": "Invalid expiration date",
                "available_expirations": list(expirations),
            }), 400

        # Get options chain
        opts = stock.option_chain(exp_date)

        # Format calls
        calls = [
            {
                "strike": row.strike,
                "last_price": row.lastPrice,
                "bid": row.bid,
                "ask": row.ask,
                "volume": int(row.volume) if hasattr(row, 'volume') and row.volume and not pd.isna(row.volume) else 0,
                "open_interest": int(row.openInterest) if hasattr(row, 'openInterest') and row.openInterest and not pd.isna(row.openInterest) else 0,
                "implied_volatility": row.impliedVolatility,
                "in_the_money": row.inTheMoney,
            }
            for row in opts.calls.itertuples()
        ]

        # Format puts
        puts = [
            {
                "strike": row.strike,
                "last_price": row.lastPrice,
                "bid": row.bid,
                "ask": row.ask,
                "volume": int(row.volume) if hasattr(row, 'volume') and row.volume and not pd.isna(row.volume) else 0,
                "open_interest": int(row.openInterest) if hasattr(row, 'openInterest') and row.openInterest and not pd.isna(row.openInterest) else 0,
                "implied_volatility": row.impliedVolatility,
                "in_the_money": row.inTheMoney,
            }
            for row in opts.puts.itertuples()
        ]

        # Get current stock price
        info = stock.info or {}
        current_price = info.get("regularMarketPrice", 0)

        # Calculate put/call ratio
        total_call_oi = sum(c.get("open_interest", 0) for c in calls)
        total_put_oi = sum(p.get("open_interest", 0) for p in puts)
        pc_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0

        # Find max pain (strike with most open interest)
        all_strikes = {}
        for c in calls:
            strike = c["strike"]
            all_strikes[strike] = all_strikes.get(strike, 0) + c.get("open_interest", 0)
        for p in puts:
            strike = p["strike"]
            all_strikes[strike] = all_strikes.get(strike, 0) + p.get("open_interest", 0)

        max_pain = max(all_strikes.items(), key=lambda x: x[1])[0] if all_strikes else None

        return jsonify({
            "ticker": ticker,
            "current_price": current_price,
            "expiration": exp_date,
            "available_expirations": list(expirations),
            "calls": calls,
            "puts": puts,
            "summary": {
                "total_call_volume": sum(c.get("volume", 0) for c in calls),
                "total_put_volume": sum(p.get("volume", 0) for p in puts),
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "put_call_ratio": round(pc_ratio, 2),
                "max_pain": max_pain,
                "sentiment": "bearish" if pc_ratio > 1 else "bullish" if pc_ratio < 0.7 else "neutral",
            },
        })

    except Exception as e:
        logger.error(f"Error getting options chain for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@api_options.route("/api/options/unusual-activity")
@login_required
@cache.cached(timeout=300, key_prefix="unusual_options")
def get_unusual_activity():
    """
    Get unusual options activity.

    Identifies:
    - High volume vs open interest
    - Large block trades
    - Unusual strike selections

    Note: For real unusual flow, use specialized APIs.
    This is a simplified version using available data.
    """
    try:
        import yfinance as yf
    except ImportError:
        return jsonify({"error": "yfinance not installed"}), 500

    # Popular stocks to scan
    tickers = [
        "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META",
        "AMZN", "GOOGL", "NFLX", "BA", "DIS", "COIN", "GME", "AMC"
    ]

    unusual = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options

            if not expirations:
                continue

            # Check nearest 2 expirations
            for exp in expirations[:2]:
                try:
                    opts = stock.option_chain(exp)

                    # Check calls
                    for row in opts.calls.itertuples():
                        volume = int(row.volume) if hasattr(row, 'volume') and row.volume and not pd.isna(row.volume) else 0
                        oi = int(row.openInterest) if hasattr(row, 'openInterest') and row.openInterest and not pd.isna(row.openInterest) else 0

                        # Unusual if volume > 5x OI and volume > 1000
                        if oi > 0 and volume > oi * 5 and volume > 1000:
                            unusual.append({
                                "ticker": ticker,
                                "type": "CALL",
                                "strike": row.strike,
                                "expiration": exp,
                                "volume": volume,
                                "open_interest": oi,
                                "vol_oi_ratio": round(volume / oi, 1) if oi > 0 else 0,
                                "last_price": row.lastPrice,
                                "implied_volatility": row.impliedVolatility,
                                "sentiment": "bullish",
                            })

                    # Check puts
                    for row in opts.puts.itertuples():
                        volume = int(row.volume) if hasattr(row, 'volume') and row.volume and not pd.isna(row.volume) else 0
                        oi = int(row.openInterest) if hasattr(row, 'openInterest') and row.openInterest and not pd.isna(row.openInterest) else 0

                        if oi > 0 and volume > oi * 5 and volume > 1000:
                            unusual.append({
                                "ticker": ticker,
                                "type": "PUT",
                                "strike": row.strike,
                                "expiration": exp,
                                "volume": volume,
                                "open_interest": oi,
                                "vol_oi_ratio": round(volume / oi, 1) if oi > 0 else 0,
                                "last_price": row.lastPrice,
                                "implied_volatility": row.impliedVolatility,
                                "sentiment": "bearish",
                            })

                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Error scanning {ticker}: {e}")
            continue

    # Sort by vol/OI ratio
    unusual.sort(key=lambda x: x["vol_oi_ratio"], reverse=True)

    return jsonify({
        "count": len(unusual),
        "unusual_activity": unusual[:20],  # Top 20
        "scanned_tickers": tickers,
        "timestamp": datetime.now().isoformat(),
    })

@api_options.route("/api/options/iv-rank/<ticker>")
@login_required
def get_iv_rank(ticker):
    """
    Get Implied Volatility Rank for a stock.

    IV Rank = (Current IV - 52 Week Low IV) / (52 Week High IV - 52 Week Low IV)

    High IV Rank (>50): Good for selling options
    Low IV Rank (<30): Good for buying options
    """
    ticker = ticker.upper()

    try:
        import yfinance as yf
    except ImportError:
        return jsonify({"error": "yfinance not installed"}), 500

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            return jsonify({"error": "No options available"}), 404

        # Get ATM options for nearest expiration
        opts = stock.option_chain(expirations[0])
        info = stock.info or {}
        current_price = info.get("regularMarketPrice", 0)

        # Find ATM call
        calls_df = opts.calls
        if calls_df.empty:
            return jsonify({"error": "No options data available"}), 404

        # Find closest strike to current price
        calls_df["distance"] = abs(calls_df["strike"] - current_price)
        atm_call = calls_df.loc[calls_df["distance"].idxmin()]

        current_iv = atm_call.get("impliedVolatility", 0)

        # For proper IV rank, we'd need historical IV data
        # This is a simplified version
        return jsonify({
            "ticker": ticker,
            "current_price": current_price,
            "current_iv": round(current_iv * 100, 1) if current_iv else None,
            "atm_strike": atm_call.get("strike"),
            "expiration": expirations[0],
            "note": "For full IV Rank calculation, historical IV data is required",
            "recommendation": _get_iv_recommendation(current_iv * 100 if current_iv else 0),
        })

    except Exception as e:
        logger.error(f"Error getting IV for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

def _get_iv_recommendation(iv: float) -> dict:
    """Get trading recommendation based on IV level."""
    if iv >= 80:
        return {
            "level": "Very High",
            "strategy": "Sell premium - Credit spreads, Iron Condors, Covered Calls",
            "risk": "High IV can lead to large moves",
        }
    elif iv >= 50:
        return {
            "level": "High",
            "strategy": "Favor selling strategies - Strangles, Iron Condors",
            "risk": "Moderate - IV crush after earnings/events",
        }
    elif iv >= 30:
        return {
            "level": "Medium",
            "strategy": "Mixed - Both buying and selling can work",
            "risk": "Normal market conditions",
        }
    else:
        return {
            "level": "Low",
            "strategy": "Buy premium - Long calls/puts, Debit spreads",
            "risk": "Low IV means cheaper options but less premium decay",
        }

@api_options.route("/api/darkpool/activity")
@login_required
@cache.cached(timeout=600, key_prefix="darkpool")
def get_darkpool_activity():
    """
    Get dark pool activity indicators.

    Note: Real dark pool data requires specialized feeds like:
    - FINRA ADF data
    - Quandl Alternative Data
    - Market Chameleon

    This provides framework and uses volume analysis as proxy.
    """
    polygon = get_polygon_service()

    # Get today's top volume stocks
    gainers = polygon.get_gainers_losers("gainers")
    losers = polygon.get_gainers_losers("losers")

    # Combine and analyze
    all_movers = gainers[:10] + losers[:10]

    analysis = []
    for stock in all_movers:
        ticker = stock.get("ticker")
        volume = stock.get("volume", 0)

        # Get average volume for comparison
        try:
            details = polygon.get_ticker_details(ticker)
            # Dark pool estimate: Typically 40% of equity volume goes through dark pools
            # We use volume anomalies as a proxy
            analysis.append({
                "ticker": ticker,
                "price": stock.get("price"),
                "change_percent": stock.get("change_percent"),
                "volume": volume,
                "estimated_dark_pool": int(volume * 0.4),  # ~40% estimate
                "note": "Estimated based on typical dark pool participation rates",
            })
        except Exception:
            continue

    return jsonify({
        "count": len(analysis),
        "activity": analysis,
        "note": "Dark pool data is estimated. For real-time dark pool prints, use specialized data feeds.",
        "timestamp": datetime.now().isoformat(),
    })

"""
Market Features API - Extended Hours, Sector Heatmap, Performance Analytics
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.database import db, Transaction, Watchlist
from web.polygon_service import get_polygon_service
from web.extensions import cache
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
@cache.cached(timeout=60, key_prefix='sector_heatmap')  # Cache for 1 minute
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


@api_market_features.route("/api/market/treemap")
@login_required
@cache.cached(timeout=60, key_prefix='treemap_data')  # Cache for 1 minute
def get_treemap_data():
    """
    Get stock data for Finviz-style treemap visualization.
    Uses bulk snapshot API for efficiency (single API call for all stocks).
    """
    try:
        polygon = get_polygon_service()

        # Major stocks by sector with estimated market caps (in billions)
        # Market caps are approximate and used for sizing when API data unavailable
        sector_stocks = {
            "Technology": {
                # Keep these updated so the treemap looks right when live caps are unavailable
                "AAPL": 3000, "MSFT": 2800, "NVDA": 3500, "GOOGL": 1700, "META": 900,
                "AVGO": 400, "ORCL": 300, "CRM": 250, "AMD": 200, "ADBE": 250,
                "CSCO": 200, "INTC": 150, "IBM": 150, "QCOM": 180, "TXN": 160
            },
            "Healthcare": {
                "UNH": 500, "JNJ": 400, "LLY": 550, "PFE": 160, "ABBV": 280,
                "MRK": 270, "TMO": 200, "ABT": 190, "DHR": 170, "BMY": 100,
                "AMGN": 140, "MDT": 110, "GILD": 100, "CVS": 90, "ELV": 100
            },
            "Financial": {
                "JPM": 500, "BAC": 280, "WFC": 180, "GS": 130, "MS": 140,
                "BLK": 120, "C": 100, "SCHW": 110, "AXP": 150, "SPGI": 130,
                "CB": 100, "MMC": 90, "PNC": 70, "USB": 60, "TFC": 50
            },
            "Consumer Cyclical": {
                "AMZN": 1500, "TSLA": 700, "HD": 350, "MCD": 200, "NKE": 150,
                "LOW": 140, "SBUX": 110, "TJX": 100, "BKNG": 120, "MAR": 70,
                "CMG": 70, "ORLY": 60, "YUM": 40, "DHI": 50, "GM": 50
            },
            "Communication": {
                "GOOG": 1700, "DIS": 180, "NFLX": 250, "CMCSA": 160, "VZ": 160,
                "T": 120, "TMUS": 200, "CHTR": 50, "EA": 40, "WBD": 25,
                "TTWO": 30, "OMC": 20, "IPG": 12, "PARA": 10, "FOXA": 15
            },
            "Industrials": {
                "CAT": 150, "GE": 180, "UNP": 140, "HON": 130, "UPS": 120,
                "RTX": 140, "BA": 130, "DE": 110, "LMT": 110, "ADP": 100,
                "MMM": 60, "GD": 70, "WM": 80, "CSX": 70, "NSC": 55
            },
            "Consumer Defensive": {
                "WMT": 420, "PG": 360, "COST": 300, "KO": 260, "PEP": 230,
                "PM": 180, "MO": 80, "MDLZ": 90, "CL": 75, "TGT": 70,
                "KMB": 45, "GIS": 40, "STZ": 45, "KHC": 40, "HSY": 45
            },
            "Energy": {
                "XOM": 450, "CVX": 280, "COP": 130, "EOG": 70, "SLB": 65,
                "MPC": 55, "PXD": 50, "PSX": 50, "VLO": 45, "OXY": 50,
                "WMB": 45, "KMI": 40, "HAL": 30, "DVN": 30, "HES": 45
            },
            "Utilities": {
                "NEE": 150, "DUK": 80, "SO": 85, "D": 45, "AEP": 50,
                "SRE": 50, "XEL": 35, "EXC": 40, "ED": 35, "WEC": 30,
                "ES": 25, "PEG": 35, "AWK": 28, "DTE": 22, "ETR": 22
            },
            "Real Estate": {
                "PLD": 120, "AMT": 100, "EQIX": 75, "CCI": 45, "PSA": 55,
                "SPG": 50, "O": 45, "WELL": 45, "DLR": 40, "AVB": 30,
                "EQR": 25, "VTR": 22, "SBAC": 25, "WY": 22, "ARE": 18
            },
            "Materials": {
                "LIN": 200, "APD": 65, "SHW": 80, "ECL": 55, "FCX": 60,
                "NEM": 45, "NUE": 40, "VMC": 35, "MLM": 35, "DD": 35,
                "DOW": 35, "PPG": 30, "ALB": 15, "CTVA": 35, "CF": 15
            }
        }

        # Get all tickers for bulk request
        all_tickers = []
        for sector_tickers in sector_stocks.values():
            all_tickers.extend(sector_tickers.keys())

        # Fetch bulk snapshot data (single API call)
        bulk_data = polygon.get_market_snapshot(all_tickers)
        
        # Log how many tickers have market cap from snapshot
        tickers_with_cap = sum(1 for t in all_tickers if bulk_data.get(t, {}).get("market_cap"))
        logger.info(f"Treemap: {len(bulk_data)} tickers returned, {tickers_with_cap} have market_cap from snapshot")

        treemap_data = {"name": "Market", "children": []}

        for sector_name, tickers_with_caps in sector_stocks.items():
            sector_data = {"name": sector_name, "children": []}

            for ticker, default_cap_b in tickers_with_caps.items():
                try:
                    snapshot = bulk_data.get(ticker, {})

                    # Use snapshot data - fallback to prev_close when market closed
                    price = (
                        snapshot.get("price") or
                        snapshot.get("day_close") or
                        snapshot.get("prev_close") or
                        0
                    )
                    price = float(price) if price is not None else 0
                    change_percent = float(snapshot.get("change_percent", 0) or 0)
                    volume = snapshot.get("day_volume") or snapshot.get("prev_volume") or 0

                    # Prefer live market cap for accurate sizing
                    market_cap = snapshot.get("market_cap")
                    market_cap_source = "snapshot" if market_cap else None

                    # If snapshot lacks cap, try ticker details API
                    if not market_cap:
                        try:
                            details = polygon.get_ticker_details(ticker)
                            if details and details.get("market_cap"):
                                market_cap = details["market_cap"]
                                market_cap_source = "details"
                        except Exception as detail_err:
                            logger.debug(f"Could not get details for {ticker}: {detail_err}")

                    # Fall back to static defaults (billions) only if API data unavailable
                    if market_cap is None or market_cap <= 0:
                        market_cap = default_cap_b * 1_000_000_000
                        market_cap_source = "static_default"
                        logger.debug(f"{ticker}: Using static default market cap ${default_cap_b}B")
                    else:
                        market_cap = float(market_cap)
                        if market_cap_source == "snapshot":
                            logger.debug(f"{ticker}: Got market cap from Polygon snapshot: ${market_cap/1e9:.1f}B")

                    # Skip if we still don't have a positive cap
                    if market_cap <= 0:
                        logger.debug(f"Skipping {ticker} due to missing market cap")
                        continue

                    sector_data["children"].append({
                        "name": ticker,
                        "ticker": ticker,
                        "value": market_cap,
                        "market_cap": market_cap,
                        "market_cap_source": market_cap_source,  # Track data source
                        "price": price,
                        "change": snapshot.get("change", 0) or 0,
                        "change_percent": round(change_percent, 2),
                        "volume": volume
                    })
                except Exception as e:
                    logger.warning(f"Error processing {ticker}: {e}")
                    continue

            if sector_data["children"]:
                # Calculate sector totals
                sector_market_cap = sum(s["market_cap"] for s in sector_data["children"])
                weighted_change = sum(s["change_percent"] * s["market_cap"] for s in sector_data["children"])
                sector_change = weighted_change / sector_market_cap if sector_market_cap > 0 else 0

                sector_data["value"] = sector_market_cap
                sector_data["change_percent"] = round(sector_change, 2)
                treemap_data["children"].append(sector_data)

        # Calculate market totals and data quality stats
        total_market_cap = sum(s["value"] for s in treemap_data["children"])
        weighted_market_change = sum(s["change_percent"] * s["value"] for s in treemap_data["children"])
        market_change = weighted_market_change / total_market_cap if total_market_cap > 0 else 0
        
        # Count data sources for debugging
        all_stocks = [stock for sector in treemap_data["children"] for stock in sector["children"]]
        source_counts = {
            "snapshot": sum(1 for s in all_stocks if s.get("market_cap_source") == "snapshot"),
            "details": sum(1 for s in all_stocks if s.get("market_cap_source") == "details"),
            "static_default": sum(1 for s in all_stocks if s.get("market_cap_source") == "static_default"),
        }
        
        logger.info(f"Treemap data sources: {source_counts}")

        return jsonify({
            "success": True,
            "data": treemap_data,
            "summary": {
                "total_market_cap": total_market_cap,
                "market_change": round(market_change, 2),
                "sectors_count": len(treemap_data["children"]),
                "stocks_count": sum(len(s["children"]) for s in treemap_data["children"]),
                "data_sources": source_counts  # Show where market cap data came from
            }
        })
    except Exception as e:
        logger.error(f"Error fetching treemap data: {e}", exc_info=True)
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

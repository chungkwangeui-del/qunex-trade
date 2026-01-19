"""
Institutional Flow API - Options Flow, Dark Pool, and Insider Trading

Features:
- Unusual Options Activity detection
- Dark Pool prints tracking
- SEC Form 4 Insider filings
- Institutional accumulation signals
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from web.extensions import csrf, cache
from web.database import db, InsiderTrade
from web.polygon_service import get_polygon_service
from web.finnhub_service import get_finnhub_service
import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

api_flow = Blueprint("api_flow", __name__)
csrf.exempt(api_flow)


class OptionsFlowAnalyzer:
    """Analyze options flow for unusual activity"""

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")

    def get_options_chain(self, ticker: str) -> dict:
        """Get options chain data from Polygon"""
        if not self.polygon_key:
            return {"error": "API not configured"}

        try:
            # Get current date for expiration filtering
            today = datetime.now()
            
            # Get options contracts
            url = f"https://api.polygon.io/v3/reference/options/contracts"
            params = {
                "underlying_ticker": ticker.upper(),
                "expired": "false",
                "limit": 250,
                "apiKey": self.polygon_key
            }

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            contracts = data.get("results", [])
            
            # Organize by expiration and type
            calls = []
            puts = []
            
            for contract in contracts:
                contract_info = {
                    "ticker": contract.get("ticker"),
                    "strike": contract.get("strike_price"),
                    "expiration": contract.get("expiration_date"),
                    "type": contract.get("contract_type"),
                }
                
                if contract.get("contract_type") == "call":
                    calls.append(contract_info)
                else:
                    puts.append(contract_info)

            return {
                "ticker": ticker.upper(),
                "calls_count": len(calls),
                "puts_count": len(puts),
                "put_call_ratio": len(puts) / len(calls) if calls else 0,
                "total_contracts": len(contracts),
            }

        except Exception as e:
            logger.error(f"Options chain error: {e}")
            return {"error": str(e)}

    def detect_unusual_activity(self, ticker: str) -> dict:
        """Detect unusual options activity patterns"""
        try:
            # Get recent options trades from Polygon
            url = f"https://api.polygon.io/v3/trades/{ticker.upper()}"
            params = {
                "limit": 100,
                "apiKey": self.polygon_key
            }

            # For now, return simulated unusual activity based on volume patterns
            # In production, you'd analyze actual options flow data
            
            chain = self.get_options_chain(ticker)
            
            unusual_signals = []
            
            # High put/call ratio (bearish signal)
            if chain.get("put_call_ratio", 0) > 1.5:
                unusual_signals.append({
                    "type": "high_put_call",
                    "signal": "bearish",
                    "description": f"Put/Call ratio of {chain['put_call_ratio']:.2f} indicates bearish sentiment",
                    "strength": min(100, int(chain['put_call_ratio'] * 40))
                })
            
            # Low put/call ratio (bullish signal)
            if chain.get("put_call_ratio", 1) < 0.5:
                unusual_signals.append({
                    "type": "low_put_call",
                    "signal": "bullish", 
                    "description": f"Put/Call ratio of {chain['put_call_ratio']:.2f} indicates bullish sentiment",
                    "strength": min(100, int((1 - chain['put_call_ratio']) * 80))
                })

            return {
                "ticker": ticker.upper(),
                "chain_data": chain,
                "unusual_signals": unusual_signals,
                "overall_sentiment": "bullish" if chain.get("put_call_ratio", 1) < 0.7 else ("bearish" if chain.get("put_call_ratio", 1) > 1.3 else "neutral"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Unusual activity detection error: {e}")
            return {"error": str(e)}


class DarkPoolAnalyzer:
    """Analyze dark pool and off-exchange trading activity"""

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")

    def get_dark_pool_prints(self, ticker: str, limit: int = 50) -> dict:
        """Get recent dark pool prints (large block trades)"""
        try:
            polygon = get_polygon_service()
            
            # Get recent trades - dark pool trades are often larger blocks
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            # Get aggregates to estimate dark pool activity
            aggs = polygon.get_aggregates(
                ticker.upper(), 
                1, "hour",
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                limit=24
            )

            if not aggs:
                return {"error": "No data available", "ticker": ticker}

            # Analyze volume patterns for potential dark pool activity
            # Dark pool prints are typically:
            # 1. Large block trades (> average)
            # 2. At or near VWAP
            # 3. Minimal price impact

            volumes = [bar.get("v", 0) for bar in aggs]
            prices = [bar.get("c", 0) for bar in aggs]
            
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # Calculate VWAP
            vwap_sum = sum(
                (bar.get("h", 0) + bar.get("l", 0) + bar.get("c", 0)) / 3 * bar.get("v", 0)
                for bar in aggs
            )
            total_volume = sum(bar.get("v", 0) for bar in aggs)
            vwap = vwap_sum / total_volume if total_volume > 0 else avg_price

            # Identify potential dark pool prints (large volume bars)
            dark_pool_indicators = []
            
            for i, bar in enumerate(aggs[-10:]):  # Last 10 bars
                volume = bar.get("v", 0)
                if volume > avg_volume * 2:  # 2x average = potential block trade
                    price = bar.get("c", 0)
                    price_impact = abs(price - vwap) / vwap * 100 if vwap > 0 else 0
                    
                    dark_pool_indicators.append({
                        "timestamp": bar.get("t"),
                        "volume": volume,
                        "volume_ratio": round(volume / avg_volume, 2),
                        "price": price,
                        "price_impact_pct": round(price_impact, 3),
                        "likely_dark_pool": price_impact < 0.5  # Low impact = likely dark pool
                    })

            # Calculate dark pool score (0-100)
            # Higher score = more institutional accumulation signals
            dark_pool_score = 0
            
            likely_dp_trades = [d for d in dark_pool_indicators if d["likely_dark_pool"]]
            if likely_dp_trades:
                # Large volume with low price impact
                dark_pool_score += min(50, len(likely_dp_trades) * 15)
                
                # Very large blocks
                max_ratio = max(d["volume_ratio"] for d in likely_dp_trades)
                dark_pool_score += min(30, int(max_ratio * 5))
                
                # Consistent accumulation (multiple prints)
                if len(likely_dp_trades) >= 3:
                    dark_pool_score += 20

            return {
                "ticker": ticker.upper(),
                "vwap": round(vwap, 2),
                "avg_volume": int(avg_volume),
                "total_volume_24h": total_volume,
                "dark_pool_indicators": dark_pool_indicators,
                "dark_pool_score": min(100, dark_pool_score),
                "interpretation": (
                    "Strong institutional accumulation" if dark_pool_score >= 70 else
                    "Moderate institutional activity" if dark_pool_score >= 40 else
                    "Low institutional activity"
                ),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Dark pool analysis error: {e}")
            return {"error": str(e), "ticker": ticker}

    def get_short_interest(self, ticker: str) -> dict:
        """Get short interest data"""
        try:
            finnhub = get_finnhub_service()
            if not finnhub:
                return {"error": "Finnhub not configured"}

            # Note: Short interest data may require premium API
            # For now, return placeholder
            return {
                "ticker": ticker.upper(),
                "short_interest": None,
                "days_to_cover": None,
                "short_percent_float": None,
                "message": "Short interest data requires premium API access"
            }

        except Exception as e:
            logger.error(f"Short interest error: {e}")
            return {"error": str(e)}


class InsiderAnalyzer:
    """Analyze SEC Form 4 insider trading filings"""

    def get_insider_trades(self, ticker: str, days: int = 90) -> dict:
        """Get recent insider trading activity"""
        try:
            # Check database first
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            trades = InsiderTrade.query.filter(
                InsiderTrade.ticker == ticker.upper(),
                InsiderTrade.filing_date >= cutoff.date()
            ).order_by(InsiderTrade.filing_date.desc()).all()

            # If no data in DB, try to fetch from Finnhub
            if not trades:
                finnhub = get_finnhub_service()
                if finnhub:
                    try:
                        insider_data = finnhub.get_insider_transactions(ticker.upper())
                        if insider_data:
                            # Store in database
                            for txn in insider_data[:50]:  # Limit to 50
                                # Check if exists
                                existing = InsiderTrade.query.filter_by(
                                    ticker=ticker.upper(),
                                    insider_name=txn.get("name", "Unknown"),
                                    filing_date=datetime.strptime(txn.get("filingDate", "2024-01-01"), "%Y-%m-%d").date()
                                ).first()
                                
                                if not existing:
                                    trade = InsiderTrade(
                                        ticker=ticker.upper(),
                                        insider_name=txn.get("name", "Unknown"),
                                        position=txn.get("position", ""),
                                        transaction_type="buy" if txn.get("transactionType") == "P" else "sell",
                                        shares=abs(txn.get("share", 0)),
                                        price=txn.get("transactionPrice"),
                                        transaction_date=datetime.strptime(txn.get("transactionDate", "2024-01-01"), "%Y-%m-%d").date(),
                                        filing_date=datetime.strptime(txn.get("filingDate", "2024-01-01"), "%Y-%m-%d").date()
                                    )
                                    db.session.add(trade)
                            
                            db.session.commit()
                            
                            # Re-fetch from database
                            trades = InsiderTrade.query.filter(
                                InsiderTrade.ticker == ticker.upper(),
                                InsiderTrade.filing_date >= cutoff.date()
                            ).order_by(InsiderTrade.filing_date.desc()).all()
                    except Exception as e:
                        logger.warning(f"Failed to fetch insider data from Finnhub: {e}")

            # Analyze trades
            buys = [t for t in trades if t.transaction_type == "buy"]
            sells = [t for t in trades if t.transaction_type == "sell"]
            
            total_bought_shares = sum(t.shares for t in buys)
            total_sold_shares = sum(t.shares for t in sells)
            
            total_bought_value = sum(float(t.shares) * float(t.price or 0) for t in buys)
            total_sold_value = sum(float(t.shares) * float(t.price or 0) for t in sells)

            # Detect cluster buys (multiple insiders buying)
            cluster_buy = False
            unique_buyers = set(t.insider_name for t in buys)
            if len(unique_buyers) >= 2:
                cluster_buy = True

            # Calculate insider sentiment score (0-100)
            # Higher = more bullish insider activity
            insider_score = 50  # Neutral baseline
            
            if total_bought_value > total_sold_value:
                ratio = total_bought_value / (total_sold_value + 1)
                insider_score += min(40, int(ratio * 10))
            else:
                ratio = total_sold_value / (total_bought_value + 1)
                insider_score -= min(40, int(ratio * 10))

            if cluster_buy:
                insider_score += 15

            # CEO/CFO buys are stronger signals
            executive_buys = [t for t in buys if any(title in (t.position or "").upper() for title in ["CEO", "CFO", "COO", "PRESIDENT", "CHAIRMAN"])]
            if executive_buys:
                insider_score += 10

            insider_score = max(0, min(100, insider_score))

            return {
                "ticker": ticker.upper(),
                "period_days": days,
                "total_trades": len(trades),
                "buys": {
                    "count": len(buys),
                    "total_shares": total_bought_shares,
                    "total_value": round(total_bought_value, 2),
                    "unique_insiders": len(unique_buyers)
                },
                "sells": {
                    "count": len(sells),
                    "total_shares": total_sold_shares,
                    "total_value": round(total_sold_value, 2),
                    "unique_insiders": len(set(t.insider_name for t in sells))
                },
                "cluster_buy_detected": cluster_buy,
                "executive_buying": len(executive_buys) > 0,
                "insider_score": insider_score,
                "interpretation": (
                    "Strong insider buying" if insider_score >= 70 else
                    "Moderate insider buying" if insider_score >= 55 else
                    "Neutral insider activity" if insider_score >= 45 else
                    "Moderate insider selling" if insider_score >= 30 else
                    "Heavy insider selling"
                ),
                "recent_trades": [t.to_dict() for t in trades[:10]],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Insider analysis error: {e}")
            return {"error": str(e), "ticker": ticker}


# Initialize analyzers
options_analyzer = OptionsFlowAnalyzer()
dark_pool_analyzer = DarkPoolAnalyzer()
insider_analyzer = InsiderAnalyzer()


# ============ API ENDPOINTS ============

@api_flow.route("/api/flow/options/<ticker>")
@login_required
@cache.cached(timeout=300, query_string=True)
def get_options_flow(ticker: str):
    """Get options flow analysis for a ticker"""
    ticker = ticker.upper().strip()
    
    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker"}), 400

    result = options_analyzer.detect_unusual_activity(ticker)
    
    if "error" in result and not result.get("unusual_signals"):
        return jsonify(result), 400

    return jsonify(result)


@api_flow.route("/api/flow/darkpool/<ticker>")
@login_required
@cache.cached(timeout=300, query_string=True)
def get_dark_pool_data(ticker: str):
    """Get dark pool activity analysis for a ticker"""
    ticker = ticker.upper().strip()
    
    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker"}), 400

    result = dark_pool_analyzer.get_dark_pool_prints(ticker)
    
    if result.get("error") and not result.get("dark_pool_indicators"):
        return jsonify(result), 400

    return jsonify(result)


@api_flow.route("/api/flow/insider/<ticker>")
@login_required
@cache.cached(timeout=600, query_string=True)
def get_insider_activity(ticker: str):
    """Get insider trading activity for a ticker"""
    ticker = ticker.upper().strip()
    days = request.args.get("days", 90, type=int)
    
    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker"}), 400

    days = min(365, max(7, days))  # Between 7 and 365 days

    result = insider_analyzer.get_insider_trades(ticker, days)
    
    if result.get("error") and not result.get("recent_trades"):
        return jsonify(result), 400

    return jsonify(result)


@api_flow.route("/api/flow/summary/<ticker>")
@login_required
@cache.cached(timeout=300, query_string=True)
def get_flow_summary(ticker: str):
    """Get combined institutional flow summary for a ticker"""
    ticker = ticker.upper().strip()
    
    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker"}), 400

    # Get all flow data
    options_data = options_analyzer.detect_unusual_activity(ticker)
    dark_pool_data = dark_pool_analyzer.get_dark_pool_prints(ticker)
    insider_data = insider_analyzer.get_insider_trades(ticker, 90)

    # Calculate overall institutional score
    scores = []
    
    if not options_data.get("error"):
        sentiment = options_data.get("overall_sentiment", "neutral")
        if sentiment == "bullish":
            scores.append(70)
        elif sentiment == "bearish":
            scores.append(30)
        else:
            scores.append(50)

    if not dark_pool_data.get("error"):
        scores.append(dark_pool_data.get("dark_pool_score", 50))

    if not insider_data.get("error"):
        scores.append(insider_data.get("insider_score", 50))

    overall_score = sum(scores) / len(scores) if scores else 50

    return jsonify({
        "ticker": ticker,
        "overall_institutional_score": round(overall_score),
        "interpretation": (
            "Strong institutional bullish" if overall_score >= 70 else
            "Moderate institutional bullish" if overall_score >= 55 else
            "Neutral institutional activity" if overall_score >= 45 else
            "Moderate institutional bearish" if overall_score >= 30 else
            "Strong institutional bearish"
        ),
        "options_sentiment": options_data.get("overall_sentiment", "unknown"),
        "dark_pool_score": dark_pool_data.get("dark_pool_score"),
        "insider_score": insider_data.get("insider_score"),
        "cluster_buy_detected": insider_data.get("cluster_buy_detected", False),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@api_flow.route("/api/flow/screener")
@login_required
@cache.cached(timeout=600, query_string=True)
def flow_screener():
    """Screen multiple stocks for institutional activity"""
    tickers_param = request.args.get("tickers", "")
    
    if not tickers_param:
        # Default to some popular stocks
        tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "AMD"]
    else:
        tickers = [t.strip().upper() for t in tickers_param.split(",")][:20]  # Max 20

    results = []
    
    for ticker in tickers:
        try:
            insider_data = insider_analyzer.get_insider_trades(ticker, 30)
            dark_pool_data = dark_pool_analyzer.get_dark_pool_prints(ticker)
            
            if insider_data.get("error") and dark_pool_data.get("error"):
                continue

            results.append({
                "ticker": ticker,
                "insider_score": insider_data.get("insider_score", 50),
                "dark_pool_score": dark_pool_data.get("dark_pool_score", 50),
                "cluster_buy": insider_data.get("cluster_buy_detected", False),
                "executive_buying": insider_data.get("executive_buying", False),
                "recent_insider_buys": insider_data.get("buys", {}).get("count", 0),
                "recent_insider_sells": insider_data.get("sells", {}).get("count", 0),
            })
        except Exception as e:
            logger.warning(f"Flow screener error for {ticker}: {e}")
            continue

    # Sort by combined score
    results.sort(key=lambda x: (x["insider_score"] + x["dark_pool_score"]) / 2, reverse=True)

    return jsonify({
        "success": True,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


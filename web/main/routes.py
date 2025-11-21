from flask import render_template, jsonify, current_app, request
from flask_login import login_required, current_user
from web.database import db, NewsArticle, Watchlist, AIScore, Transaction
from web.polygon_service import PolygonService, get_polygon_service
from web.utils import calculate_statistics, filter_signals_by_subscription
from . import main
import logging
from decimal import Decimal
from collections import defaultdict
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

logger = logging.getLogger(__name__)

@main.route("/health")
def health_check():
    try:
        db.session.execute(db.select(1)).scalar()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@main.route("/")
def index():
    polygon = PolygonService()
    market_data = []
    try:
        indices = polygon.get_market_indices()
        for symbol, data in indices.items():
            market_data.append(
                {
                    "name": data.get("name", symbol),
                    "symbol": symbol,
                    "price": data.get("price", 0),
                    "change": data.get("change_percent", 0),
                    "change_amount": data.get("change", 0),
                    "volume": data.get("volume", 0),
                    "high": data.get("day_high", 0),
                    "low": data.get("day_low", 0),
                }
            )
        stats = {"total_indices": len(market_data), "market_status": "Active"}
    except Exception as e:
        logger.error(f"Error fetching Polygon indices: {e}")
        market_data = []
        stats = {"total_indices": 0, "market_status": "Unknown"}

    return render_template("index.html", market_data=market_data, stats=stats, user=current_user)

@main.route("/about")
def about():
    return render_template("about.html", user=current_user)

@main.route("/reset-theme")
def reset_theme():
    return render_template("reset_theme.html")

@main.route("/force-dark")
def force_dark():
    return render_template("FORCE_DARK_MODE.html")

@main.route("/terms")
def terms():
    return render_template("terms.html")

@main.route("/privacy")
def privacy():
    return render_template("privacy.html")

@main.route("/market")
def market():
    return render_template("market.html", user=current_user)

@main.route("/screener")
def screener():
    return render_template("screener.html", user=current_user)

@main.route("/dashboard")
@login_required
def dashboard():
    try:
        user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
        watchlist_tickers = [w.ticker for w in user_watchlist]

        ai_scores = {}
        if watchlist_tickers:
            scores = AIScore.query.filter(AIScore.ticker.in_(watchlist_tickers)).all()
            ai_scores = {score.ticker: score.to_dict() for score in scores}

        related_news = []
        if watchlist_tickers:
            search_tickers = watchlist_tickers[:5]
            filters = [NewsArticle.title.contains(ticker) for ticker in search_tickers]
            ticker_news = (
                NewsArticle.query.filter(or_(*filters))
                .order_by(NewsArticle.published_at.desc())
                .limit(15)
                .all()
            )
            related_news = [article.to_dict() for article in ticker_news]

        seen_urls = set()
        unique_news = []
        for news in related_news:
            if news["url"] not in seen_urls:
                seen_urls.add(news["url"])
                unique_news.append(news)
                if len(unique_news) >= 10:
                    break

        return render_template(
            "dashboard.html",
            user=current_user,
            watchlist=watchlist_tickers,
            ai_scores=ai_scores,
            related_news=unique_news,
        )

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        return render_template(
            "dashboard.html", user=current_user, watchlist=[], ai_scores={}, related_news=[]
        )

@main.route("/portfolio")
@login_required
def portfolio():
    try:
        transactions = (
            Transaction.query.options(joinedload(Transaction.user))
            .filter_by(user_id=current_user.id)
            .order_by(Transaction.transaction_date.desc())
            .all()
        )

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
                    avg_cost = holdings[ticker]["cost_basis"] / (
                        holdings[ticker]["shares"] + shares
                    )
                    holdings[ticker]["cost_basis"] -= shares * avg_cost

        current_holdings = {ticker: data for ticker, data in holdings.items() if data["shares"] > 0}

        portfolio_data = []
        total_value = Decimal("0")
        total_cost = Decimal("0")

        try:
            polygon = get_polygon_service()

            for ticker, holding in current_holdings.items():
                try:
                    quote = polygon.get_stock_quote(ticker)
                    current_price = Decimal(str(quote.get("price", 0))) if quote else Decimal("0")

                    shares = holding["shares"]
                    cost_basis = holding["cost_basis"]
                    current_value = shares * current_price
                    pnl = current_value - cost_basis
                    pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else Decimal("0")

                    portfolio_data.append(
                        {
                            "ticker": ticker,
                            "shares": float(shares),
                            "avg_cost": float(cost_basis / shares) if shares > 0 else 0,
                            "current_price": float(current_price),
                            "cost_basis": float(cost_basis),
                            "current_value": float(current_value),
                            "pnl": float(pnl),
                            "pnl_percent": float(pnl_percent),
                        }
                    )

                    total_value += current_value
                    total_cost += cost_basis

                except Exception as e:
                    logger.error(f"Error fetching price for {ticker}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching portfolio prices: {e}", exc_info=True)

        total_pnl = total_value - total_cost
        total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else Decimal("0")

        return render_template(
            "portfolio.html",
            user=current_user,
            transactions=[txn.to_dict() for txn in transactions],
            portfolio=portfolio_data,
            total_cost=float(total_cost),
            total_value=float(total_value),
            total_pnl=float(total_pnl),
            total_pnl_percent=float(total_pnl_percent),
        )

    except Exception as e:
        logger.error(f"Error loading portfolio: {e}", exc_info=True)
        return render_template(
            "portfolio.html",
            user=current_user,
            transactions=[],
            portfolio=[],
            total_cost=0,
            total_value=0,
            total_pnl=0,
            total_pnl_percent=0,
        )

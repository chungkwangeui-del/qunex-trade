"""
Trade Journal API

CRUD operations for trade journal entries.
Helps traders track and improve their performance.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timezone
from decimal import Decimal
import logging
from datetime import timezone
from typing import Optional

try:
    from web.database import db, TradeJournal
except ImportError:
    from database import db, TradeJournal

logger = logging.getLogger(__name__)

api_journal = Blueprint("api_journal", __name__)


@api_journal.route("/api/journal/entries", methods=["GET"])
@login_required
def get_journal_entries():
    """
    Get all trade journal entries for the current user.

    Query params:
        limit: int - Max entries to return (default 50)
        offset: int - Pagination offset
        outcome: str - Filter by outcome ('win', 'loss', 'breakeven')
        ticker: str - Filter by ticker symbol
        strategy: str - Filter by strategy
        date_from: str - Filter from date (YYYY-MM-DD)
        date_to: str - Filter to date (YYYY-MM-DD)
    """
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))

    query = TradeJournal.query.filter_by(user_id=current_user.id)

    # Apply filters
    if request.args.get("outcome"):
        query = query.filter_by(outcome=request.args.get("outcome"))

    if request.args.get("ticker"):
        query = query.filter_by(ticker=request.args.get("ticker").upper())

    if request.args.get("strategy"):
        query = query.filter_by(strategy=request.args.get("strategy"))

    if request.args.get("date_from"):
        try:
            date_from = datetime.strptime(request.args.get("date_from"), "%Y-%m-%d")
            query = query.filter(TradeJournal.entry_date >= date_from)
        except ValueError:
            pass

    if request.args.get("date_to"):
        try:
            date_to = datetime.strptime(request.args.get("date_to"), "%Y-%m-%d")
            query = query.filter(TradeJournal.entry_date <= date_to)
        except ValueError:
            pass

    # Get total count before pagination
    total = query.count()

    # Apply ordering and pagination
    entries = query.order_by(TradeJournal.entry_date.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "entries": [e.to_dict() for e in entries],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@api_journal.route("/api/journal/entries", methods=["POST"])
@login_required
def create_journal_entry():
    """
    Create a new trade journal entry.

    Request JSON:
        ticker: str (required)
        trade_type: str - 'long' or 'short' (required)
        entry_price: float (required)
        shares: float (required)
        entry_date: str - ISO datetime (required)
        exit_price: float (optional)
        exit_date: str (optional)
        stop_loss: float
        take_profit: float
        strategy: str
        setup_type: str
        timeframe: str
        emotion_before: str
        emotion_after: str
        confidence_level: int (1-10)
        followed_plan: bool
        entry_reason: str
        exit_reason: str
        mistakes: str
        lessons_learned: str
        notes: str
        market_condition: str
        news_catalyst: str
    """
    data = request.get_json() or {}

    # Validate required fields
    required = ["ticker", "trade_type", "entry_price", "shares", "entry_date"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    try:
        entry_date = datetime.fromisoformat(data["entry_date"].replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid entry_date format"}), 400

    try:
        entry = TradeJournal(
            user_id=current_user.id,
            ticker=data["ticker"].upper(),
            trade_type=data["trade_type"].lower(),
            entry_price=Decimal(str(data["entry_price"])),
            shares=Decimal(str(data["shares"])),
            entry_date=entry_date,
        )

        # Optional fields
        if data.get("exit_price"):
            entry.exit_price = Decimal(str(data["exit_price"]))

        if data.get("exit_date"):
            try:
                entry.exit_date = datetime.fromisoformat(data["exit_date"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        if data.get("stop_loss"):
            entry.stop_loss = Decimal(str(data["stop_loss"]))

        if data.get("take_profit"):
            entry.take_profit = Decimal(str(data["take_profit"]))

        # Calculate planned R:R if stop and target provided
        if entry.stop_loss and entry.take_profit:
            risk = abs(float(entry.entry_price) - float(entry.stop_loss))
            reward = abs(float(entry.take_profit) - float(entry.entry_price))
            if risk > 0:
                entry.planned_risk_reward = round(reward / risk, 2)

        # String fields
        for field in ["strategy", "setup_type", "timeframe", "emotion_before",
                      "emotion_after", "entry_reason", "exit_reason", "mistakes",
                      "lessons_learned", "notes", "market_condition", "news_catalyst"]:
            if data.get(field):
                setattr(entry, field, data[field])

        # Integer/boolean fields
        if data.get("confidence_level"):
            entry.confidence_level = min(10, max(1, int(data["confidence_level"])))

        if "followed_plan" in data:
            entry.followed_plan = bool(data["followed_plan"])

        # Calculate P&L if exit price provided
        if entry.exit_price:
            _calculate_pnl(entry)

        db.session.add(entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "entry": entry.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating journal entry: {e}")
        return jsonify({"error": str(e)}), 500


@api_journal.route("/api/journal/entries/<int:entry_id>", methods=["GET"])
@login_required
def get_journal_entry(entry_id):
    """Get a specific journal entry."""
    entry = TradeJournal.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first()

    if not entry:
        return jsonify({"error": "Entry not found"}), 404

    return jsonify(entry.to_dict())


@api_journal.route("/api/journal/entries/<int:entry_id>", methods=["PUT"])
@login_required
def update_journal_entry(entry_id):
    """Update a journal entry."""
    entry = TradeJournal.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first()

    if not entry:
        return jsonify({"error": "Entry not found"}), 404

    data = request.get_json() or {}

    try:
        # Update price and dates
        _update_price_and_dates(entry, data)

        # Update metadata and strings
        _update_entry_metadata(entry, data)

        # Recalculate P&L if exit price changed
        if entry.exit_price:
            _calculate_pnl(entry)

        db.session.commit()

        return jsonify({
            "success": True,
            "entry": entry.to_dict(),
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating journal entry: {e}")
        return jsonify({"error": str(e)}), 500

def _update_price_and_dates(entry, data):
    """Update price and date fields from data dictionary"""
    if data.get("exit_price"):
        entry.exit_price = Decimal(str(data["exit_price"]))

    if data.get("exit_date"):
        try:
            entry.exit_date = datetime.fromisoformat(data["exit_date"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    if data.get("stop_loss"):
        entry.stop_loss = Decimal(str(data["stop_loss"]))

    if data.get("take_profit"):
        entry.take_profit = Decimal(str(data["take_profit"]))

def _update_entry_metadata(entry, data):
    """Update non-price metadata fields"""
    # String fields
    for field in ["strategy", "setup_type", "timeframe", "emotion_before",
                  "emotion_after", "entry_reason", "exit_reason", "mistakes",
                  "lessons_learned", "notes", "market_condition", "news_catalyst"]:
        if field in data:
            setattr(entry, field, data[field])

    if data.get("confidence_level"):
        entry.confidence_level = min(10, max(1, int(data["confidence_level"])))

    if "followed_plan" in data:
        entry.followed_plan = bool(data["followed_plan"])


@api_journal.route("/api/journal/entries/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_journal_entry(entry_id):
    """Delete a journal entry."""
    entry = TradeJournal.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first()

    if not entry:
        return jsonify({"error": "Entry not found"}), 404

    try:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_journal.route("/api/journal/close-trade/<int:entry_id>", methods=["POST"])
@login_required
def close_trade(entry_id):
    """
    Close an open trade with exit details.

    Request JSON:
        exit_price: float (required)
        exit_date: str (optional, defaults to now)
        exit_reason: str
        emotion_after: str
        lessons_learned: str
    """
    entry = TradeJournal.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first()

    if not entry:
        return jsonify({"error": "Entry not found"}), 404

    if entry.exit_price:
        return jsonify({"error": "Trade already closed"}), 400

    data = request.get_json() or {}

    if not data.get("exit_price"):
        return jsonify({"error": "exit_price is required"}), 400

    try:
        _apply_close_details(entry, data)

        # Calculate P&L
        _calculate_pnl(entry)

        db.session.commit()

        return jsonify({
            "success": True,
            "entry": entry.to_dict(),
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def _apply_close_details(entry, data):
    """Apply exit price and metadata to closing entry"""
    entry.exit_price = Decimal(str(data["exit_price"]))

    if data.get("exit_date"):
        entry.exit_date = datetime.fromisoformat(data["exit_date"].replace("Z", "+00:00"))
    else:
        entry.exit_date = datetime.now(timezone.utc)

    if data.get("exit_reason"):
        entry.exit_reason = data["exit_reason"]

    if data.get("emotion_after"):
        entry.emotion_after = data["emotion_after"]

    if data.get("lessons_learned"):
        entry.lessons_learned = data["lessons_learned"]


def _calculate_pnl(entry: TradeJournal):
    """Calculate P&L for a closed trade."""
    if not entry.exit_price or not entry.entry_price:
        return

    entry_val = float(entry.entry_price) * float(entry.shares)
    exit_val = float(entry.exit_price) * float(entry.shares)

    if entry.trade_type == "long":
        entry.pnl = Decimal(str(round(exit_val - entry_val, 2)))
    else:  # short
        entry.pnl = Decimal(str(round(entry_val - exit_val, 2)))

    entry.pnl_percent = round((float(entry.pnl) / entry_val) * 100, 2) if entry_val > 0 else 0

    # Determine outcome
    if entry.pnl > 0:
        entry.outcome = "win"
    elif entry.pnl < 0:
        entry.outcome = "loss"
    else:
        entry.outcome = "breakeven"

    # Calculate actual R:R if stop loss was set
    if entry.stop_loss:
        risk_per_share = abs(float(entry.entry_price) - float(entry.stop_loss))
        if risk_per_share > 0:
            entry.actual_risk_reward = round(float(entry.pnl) / (risk_per_share * float(entry.shares)), 2)

def _get_closed_trades(user_id: int):
    """Helper to get all closed trades for a user"""
    return TradeJournal.query.filter(
        TradeJournal.user_id == user_id,
        TradeJournal.exit_price.isnot(None)
    ).all()

def _calculate_win_rate_stats(trades):
    """Calculate win rate, avg win, avg loss"""
    if not trades:
        return 0, 0, 0, 0, 0
    
    wins = [e for e in trades if e.outcome == "win"]
    losses = [e for e in trades if e.outcome == "loss"]
    
    win_rate = (len(wins) / len(trades) * 100)
    avg_win = sum(float(e.pnl or 0) for e in wins) / len(wins) if wins else 0
    avg_loss = sum(float(e.pnl or 0) for e in losses) / len(losses) if losses else 0
    total_win_pnl = sum(float(e.pnl or 0) for e in wins)
    total_loss_pnl = abs(sum(float(e.pnl or 0) for e in losses))
    
    return win_rate, avg_win, avg_loss, total_win_pnl, total_loss_pnl

@api_journal.route("/api/journal/stats", methods=["GET"])
@login_required
def get_journal_stats():
    """
    Get trading statistics from journal entries.
    """
    all_entries = TradeJournal.query.filter_by(user_id=current_user.id).all()
    if not all_entries:
        return jsonify({"total_trades": 0, "message": "No trades recorded yet"})

    closed_trades = [e for e in all_entries if e.exit_price is not None]
    if not closed_trades:
        return jsonify({
            "total_trades": len(all_entries),
            "open_trades": len(all_entries),
            "closed_trades": 0,
            "message": "No closed trades yet",
        })

    # Core Stats
    win_rate, avg_win, avg_loss, tot_w, tot_l = _calculate_win_rate_stats(closed_trades)
    profit_factor = tot_w / tot_l if tot_l > 0 else float('inf')
    
    # Best/Worst
    best_trade = max(closed_trades, key=lambda e: float(e.pnl or 0))
    worst_trade = min(closed_trades, key=lambda e: float(e.pnl or 0))

    # Strategies & Psychology
    strategies = {}
    plan_followers = []
    plan_breakers = []

    for e in closed_trades:
        # Strategy grouping
        strat = e.strategy or "Unknown"
        if strat not in strategies:
            strategies[strat] = {"trades": 0, "wins": 0, "pnl": 0}
        strategies[strat]["trades"] += 1
        if e.outcome == "win":
            strategies[strat]["wins"] += 1
        strategies[strat]["pnl"] += float(e.pnl or 0)
        
        # Plan adherence
        if e.followed_plan:
            plan_followers.append(e)
        else:
            plan_breakers.append(e)

    for s in strategies.values():
        s["win_rate"] = round((s["wins"] / s["trades"]) * 100, 1)
        s["pnl"] = round(s["pnl"], 2)

    return jsonify({
        "total_trades": len(all_entries),
        "open_trades": len(all_entries) - len(closed_trades),
        "closed_trades": len(closed_trades),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(tot_w - tot_l, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
        "expectancy": round((win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss), 2),
        "best_trade": {"ticker": best_trade.ticker, "pnl": float(best_trade.pnl or 0), "date": best_trade.entry_date.isoformat() if best_trade.entry_date else None},
        "worst_trade": {"ticker": worst_trade.ticker, "pnl": float(worst_trade.pnl or 0), "date": worst_trade.entry_date.isoformat() if worst_trade.entry_date else None},
        "by_strategy": strategies,
        "psychology": {
            "followed_plan_pct": round((len(plan_followers)/len(closed_trades)*100), 1),
            "plan_follow_pnl": round(sum(float(e.pnl or 0) for e in plan_followers), 2),
            "plan_break_pnl": round(sum(float(e.pnl or 0) for e in plan_breakers), 2),
        },
    })


@api_journal.route("/api/journal/tickers", methods=["GET"])
@login_required
def get_journal_tickers():
    """Get list of unique tickers from journal."""
    tickers = db.session.query(TradeJournal.ticker).filter_by(
        user_id=current_user.id
    ).distinct().all()

    return jsonify({
        "tickers": sorted([t[0] for t in tickers])
    })


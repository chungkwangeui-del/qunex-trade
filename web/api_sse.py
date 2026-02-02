"""
Server-Sent Events (SSE) API for Real-Time Price Streaming

Provides true real-time updates without polling overhead.
Features:
- Server-Sent Events for instant price updates
- Automatic reconnection handling
- Heartbeat to keep connections alive
- Graceful degradation to polling for incompatible clients
"""

from flask import Blueprint, Response, request, stream_with_context
from flask_login import login_required, current_user
from web.extensions import csrf
from web.database import Watchlist
from web.polygon_service import get_polygon_service
import logging
import json
import time
from datetime import datetime, timezone
from typing import Generator, List, Dict, Optional
import threading
from queue import Queue, Empty
from datetime import timezone
from typing import Dict
from typing import List
from typing import Optional

logger = logging.getLogger(__name__)

api_sse = Blueprint("api_sse", __name__)
csrf.exempt(api_sse)


class SSEPriceStreamer:
    """
    Manages Server-Sent Events for real-time price streaming.

    Uses a background thread to fetch prices and broadcast to all connected clients.
    """

    def __init__(self):
        self.polygon = None
        self._subscribers: Dict[str, List[Queue]] = {}  # ticker -> list of queues
        self._global_subscribers: List[Queue] = []  # subscribers to all updates
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._update_interval = 5  # seconds between price updates
        self._heartbeat_interval = 30  # seconds between heartbeats

    def _get_polygon(self):
        """Lazy initialization of polygon service"""
        if self.polygon is None:
            self.polygon = get_polygon_service()
        return self.polygon

    def start(self):
        """Start the background price fetching thread"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._price_loop, daemon=True)
        self._thread.start()
        logger.info("SSE Price Streamer started")

    def stop(self):
        """Stop the background thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SSE Price Streamer stopped")

    def subscribe(self, tickers: List[str] = None) -> Queue:
        """
        Subscribe to price updates.

        Args:
            tickers: List of tickers to subscribe to. If None, subscribes to all updates.

        Returns:
            Queue that will receive price updates
        """
        queue = Queue(maxsize=100)

        with self._lock:
            if tickers:
                for ticker in tickers:
                    ticker = ticker.upper()
                    if ticker not in self._subscribers:
                        self._subscribers[ticker] = []
                    self._subscribers[ticker].append(queue)
            else:
                self._global_subscribers.append(queue)

        # Ensure streamer is running
        self.start()

        return queue

    def unsubscribe(self, queue: Queue, tickers: List[str] = None):
        """Remove a subscriber"""
        with self._lock:
            if tickers:
                for ticker in tickers:
                    ticker = ticker.upper()
                    if ticker in self._subscribers:
                        try:
                            self._subscribers[ticker].remove(queue)
                        except ValueError:
                            pass
            else:
                try:
                    self._global_subscribers.remove(queue)
                except ValueError:
                    pass

    def _price_loop(self):
        """Background thread that fetches prices and broadcasts updates"""
        last_heartbeat = time.time()

        while self._running:
            try:
                # Get all subscribed tickers
                with self._lock:
                    all_tickers = list(self._subscribers.keys())

                if all_tickers:
                    # Fetch prices
                    polygon = self._get_polygon()
                    try:
                        snapshots = polygon.get_market_snapshot(all_tickers[:50])  # Limit batch size

                        for ticker, data in snapshots.items():
                            if data:
                                price_update = {
                                    "event": "price_update",
                                    "ticker": ticker,
                                    "price": data.get("price"),
                                    "change": data.get("change"),
                                    "change_percent": data.get("change_percent"),
                                    "volume": data.get("volume"),
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                                self._broadcast(ticker, price_update)

                    except Exception as e:
                        logger.error(f"Price fetch error: {e}")

                # Send heartbeat
                if time.time() - last_heartbeat >= self._heartbeat_interval:
                    self._broadcast_heartbeat()
                    last_heartbeat = time.time()

                time.sleep(self._update_interval)

            except Exception as e:
                logger.error(f"Price loop error: {e}")
                time.sleep(5)

    def _broadcast(self, ticker: str, data: dict):
        """Broadcast update to subscribers"""
        message = json.dumps(data)

        with self._lock:
            # Send to ticker-specific subscribers
            queues = self._subscribers.get(ticker, [])
            for queue in queues[:]:  # Copy list to avoid modification during iteration
                try:
                    queue.put_nowait(message)
                except Exception:
                    pass  # Queue full, skip

            # Send to global subscribers
            for queue in self._global_subscribers[:]:
                try:
                    queue.put_nowait(message)
                except Exception:
                    pass

    def _broadcast_heartbeat(self):
        """Send heartbeat to all subscribers"""
        heartbeat = json.dumps({
            "event": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        with self._lock:
            all_queues = list(self._global_subscribers)
            for queues in self._subscribers.values():
                all_queues.extend(queues)

            for queue in all_queues:
                try:
                    queue.put_nowait(heartbeat)
                except Exception:
                    pass


# Global streamer instance
price_streamer = SSEPriceStreamer()


def generate_sse_stream(queue: Queue, tickers: List[str] = None) -> Generator[str, None, None]:
    """
    Generate SSE stream from queue.

    Yields SSE-formatted messages.
    """
    try:
        # Send initial connection message
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'tickers': tickers})}\n\n"

        while True:
            try:
                # Wait for message with timeout
                message = queue.get(timeout=35)  # Slightly longer than heartbeat interval
                yield f"data: {message}\n\n"
            except Empty:
                # Send keepalive comment
                yield ": keepalive\n\n"

    except GeneratorExit:
        # Client disconnected
        logger.debug("SSE client disconnected")
    finally:
        # Cleanup subscription
        price_streamer.unsubscribe(queue, tickers)


@api_sse.route("/api/sse/prices")
def stream_prices():
    """
    SSE endpoint for real-time price streaming.

    Query params:
        tickers: Comma-separated list of tickers (e.g., "AAPL,MSFT,GOOGL")

    Example:
        const source = new EventSource('/api/sse/prices?tickers=AAPL,MSFT');
        source.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    tickers_param = request.args.get("tickers", "")
    tickers = [t.strip().upper() for t in tickers_param.split(",") if t.strip()]

    if not tickers:
        return {"error": "No tickers specified. Use ?tickers=AAPL,MSFT"}, 400

    if len(tickers) > 20:
        tickers = tickers[:20]  # Limit to 20 tickers

    # Subscribe to updates
    queue = price_streamer.subscribe(tickers)

    return Response(
        stream_with_context(generate_sse_stream(queue, tickers)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@api_sse.route("/api/sse/watchlist")
@login_required
def stream_watchlist():
    """
    SSE endpoint for streaming user's watchlist prices.

    Automatically subscribes to all tickers in user's watchlist.
    """
    watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()

    if not watchlist:
        return {"error": "Watchlist is empty"}, 400

    tickers = [w.ticker for w in watchlist]
    queue = price_streamer.subscribe(tickers)

    return Response(
        stream_with_context(generate_sse_stream(queue, tickers)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@api_sse.route("/api/sse/market-pulse")
def stream_market_pulse():
    """
    SSE endpoint for streaming key market indices.

    Automatically subscribes to SPY, QQQ, DIA, IWM, VIX.
    """
    indices = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
    queue = price_streamer.subscribe(indices)

    return Response(
        stream_with_context(generate_sse_stream(queue, indices)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@api_sse.route("/api/sse/status")
def sse_status():
    """Check SSE streaming status"""
    return {
        "status": "available",
        "streaming": price_streamer._running,
        "subscribers": {
            "tickers": len(price_streamer._subscribers),
            "global": len(price_streamer._global_subscribers)
        },
        "update_interval": price_streamer._update_interval,
        "heartbeat_interval": price_streamer._heartbeat_interval
    }


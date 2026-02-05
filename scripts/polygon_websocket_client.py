"""
Polygon WebSocket Client - Background Worker

Connects to Polygon WebSocket API for real-time market data.
Features:
- Automatic reconnection with exponential backoff
- Publishes data to Redis for Flask-SocketIO to broadcast
- Handles connection failures gracefully
- No data loss architecture

Schedule: Background worker (always running)
"""

import os
import sys
import json

import logging
from datetime import datetime
import backoff
import redis
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class PolygonWebSocketClient:
    """Polygon WebSocket client with auto-reconnection"""

    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        self.redis_url = os.getenv("REDIS_URL", "memory://")

        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")

        # Initialize Redis client
        if self.redis_url and self.redis_url != "memory://":
            self.redis_client = redis.from_url(self.redis_url)
            logger.info("Connected to Redis for message publishing")
        else:
            self.redis_client = None
            logger.warning("Redis not configured. Running in local mode only.")

        self.subscribed_tickers = set()
        self.ws = None
        self.running = False

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=None,  # Retry forever
        max_time=None,
        factor=2,
        max_value=300,  # Max 5 minutes between retries
        jitter=backoff.full_jitter,
    )
    def connect(self):
        """Connect to Polygon WebSocket with auto-reconnection"""
        try:
            import websocket

            ws_url = "wss://socket.polygon.io/stocks"

            logger.info(f"Connecting to Polygon WebSocket: {ws_url}")

            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            # Run forever
            self.running = True
            self.ws.run_forever()

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}", exc_info=True)
            raise  # Trigger backoff retry

    def _on_open(self, ws):
        """Handle WebSocket connection opened"""
        logger.info("✓ WebSocket connected")

        # Authenticate
        auth_msg = {"action": "auth", "params": self.api_key}
        ws.send(json.dumps(auth_msg))

        # Resubscribe to tickers if reconnecting
        if self.subscribed_tickers:
            logger.info(f"Resubscribing to {len(self.subscribed_tickers)} tickers")
            self._subscribe_tickers(list(self.subscribed_tickers))

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)

            # Handle different message types
            for msg in data:
                event_type = msg.get("ev")

                if event_type == "status":
                    status = msg.get("status")
                    logger.info(f"WebSocket status: {status} - {msg.get('message', '')}")

                elif event_type in ["T", "Q", "A"]:  # Trade, Quote, Aggregate
                    # Publish to Redis
                    self._publish_market_data(msg)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.running = False

    def _subscribe_tickers(self, tickers):
        """Subscribe to ticker updates"""
        if not self.ws:
            return

        subscribe_msg = {"action": "subscribe", "params": f"T.{',T.'.join(tickers)}"}
        self.ws.send(json.dumps(subscribe_msg))

        self.subscribed_tickers.update(tickers)
        logger.info(f"Subscribed to tickers: {tickers}")

    def _publish_market_data(self, data):
        """Publish market data to Redis for Flask-SocketIO to broadcast"""
        if not self.redis_client:
            return

        try:
            # Publish to Redis channel
            channel = f"market_data:{data.get('sym', 'unknown')}"
            self.redis_client.publish(channel, json.dumps(data))

        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}", exc_info=True)

    def subscribe(self, ticker):
        """Add ticker to subscription list"""
        self._subscribe_tickers([ticker])

    def unsubscribe(self, ticker):
        """Remove ticker from subscription list"""
        if not self.ws or ticker not in self.subscribed_tickers:
            return

        unsubscribe_msg = {"action": "unsubscribe", "params": f"T.{ticker}"}
        self.ws.send(json.dumps(unsubscribe_msg))

        self.subscribed_tickers.discard(ticker)
        logger.info(f"Unsubscribed from ticker: {ticker}")

def main():
    """Run Polygon WebSocket client"""
    logger.info("=" * 80)
    logger.info("POLYGON WEBSOCKET CLIENT START")
    logger.info("=" * 80)

    try:
        client = PolygonWebSocketClient()

        # Subscribe to popular tickers by default
        default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
        logger.info(f"Subscribing to default tickers: {default_tickers}")

        # Connect (with auto-reconnection via backoff)
        client.connect()

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

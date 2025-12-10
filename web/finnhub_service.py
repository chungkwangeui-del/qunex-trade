"""
Finnhub API Service

Real-time stock data with 60 calls/minute free tier.
https://finnhub.io/docs/api
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubService:
    """Finnhub API client for real-time stock data"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or FINNHUB_API_KEY
        self.base_url = FINNHUB_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"X-Finnhub-Token": self.api_key})

    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request with error handling"""
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return None

        try:
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Finnhub API timeout: {endpoint}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Finnhub API HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Finnhub API error: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for a symbol.

        Returns:
            {
                "c": current price,
                "d": change,
                "dp": percent change,
                "h": high,
                "l": low,
                "o": open,
                "pc": previous close,
                "t": timestamp
            }
        """
        data = self._request("quote", {"symbol": symbol.upper()})
        if data and data.get("c", 0) > 0:
            return data
        return None

    def get_candles(
        self,
        symbol: str,
        resolution: str = "5",
        from_ts: int = None,
        to_ts: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get candlestick data for a symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            resolution: Timeframe - 1, 5, 15, 30, 60, D, W, M
            from_ts: Unix timestamp start
            to_ts: Unix timestamp end
            limit: Number of candles to return

        Returns:
            List of candles with o, h, l, c, v, t keys
        """
        # Calculate timestamps if not provided
        if to_ts is None:
            to_ts = int(datetime.now().timestamp())

        if from_ts is None:
            # Calculate from_ts based on resolution
            if resolution in ["1", "5", "15", "30"]:
                # Minutes - get last 2 days
                from_ts = to_ts - (2 * 24 * 60 * 60)
            elif resolution == "60":
                # Hourly - get last 7 days
                from_ts = to_ts - (7 * 24 * 60 * 60)
            elif resolution == "D":
                # Daily - get last 6 months
                from_ts = to_ts - (180 * 24 * 60 * 60)
            elif resolution == "W":
                # Weekly - get last 2 years
                from_ts = to_ts - (730 * 24 * 60 * 60)
            else:
                from_ts = to_ts - (30 * 24 * 60 * 60)

        data = self._request("stock/candle", {
            "symbol": symbol.upper(),
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts
        })

        if not data or data.get("s") != "ok":
            logger.warning(f"No candle data for {symbol}: {data}")
            return []

        # Convert to list of candle dicts
        candles = []
        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        for i in range(len(timestamps)):
            candles.append({
                "t": timestamps[i] * 1000,  # Convert to milliseconds
                "o": opens[i],
                "h": highs[i],
                "l": lows[i],
                "c": closes[i],
                "v": volumes[i] if i < len(volumes) else 0
            })

        # Return last 'limit' candles
        if len(candles) > limit:
            candles = candles[-limit:]

        logger.info(f"Finnhub: Fetched {len(candles)} candles for {symbol} ({resolution})")
        return candles

    def get_candles_for_scalping(
        self,
        symbol: str,
        interval: str = "5",
        limit: int = 100
    ) -> List[Dict]:
        """
        Get candles formatted for scalping analysis.

        Args:
            symbol: Stock symbol
            interval: "1", "5", "15" (minutes)
            limit: Number of candles

        Returns:
            List of candles with o, h, l, c, v keys
        """
        # Map interval to Finnhub resolution
        resolution_map = {"1": "1", "5": "5", "15": "15"}
        resolution = resolution_map.get(interval, "5")

        return self.get_candles(symbol, resolution, limit=limit)

    def get_candles_for_swing(
        self,
        symbol: str,
        timeframe: str = "4H",
        limit: int = 100
    ) -> List[Dict]:
        """
        Get candles formatted for swing trading analysis.

        Args:
            symbol: Stock symbol
            timeframe: "1H", "4H", "1D", "1W"
            limit: Number of candles

        Returns:
            List of candles with o, h, l, c, v keys
        """
        # Map timeframe to Finnhub resolution
        resolution_map = {
            "1H": "60",
            "4H": "60",  # Finnhub doesn't have 4H, use 60min and aggregate
            "1D": "D",
            "1W": "W"
        }
        resolution = resolution_map.get(timeframe, "D")

        candles = self.get_candles(symbol, resolution, limit=limit * 4 if timeframe == "4H" else limit)

        # Aggregate to 4H if needed
        if timeframe == "4H" and candles:
            candles = self._aggregate_candles(candles, 4)

        return candles[-limit:] if len(candles) > limit else candles

    def _aggregate_candles(self, candles: List[Dict], period: int) -> List[Dict]:
        """Aggregate candles into larger timeframe"""
        if not candles or period <= 1:
            return candles

        aggregated = []
        for i in range(0, len(candles), period):
            chunk = candles[i:i + period]
            if not chunk:
                continue

            aggregated.append({
                "t": chunk[0]["t"],
                "o": chunk[0]["o"],
                "h": max(c["h"] for c in chunk),
                "l": min(c["l"] for c in chunk),
                "c": chunk[-1]["c"],
                "v": sum(c["v"] for c in chunk)
            })

        return aggregated

    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """Get company profile information"""
        return self._request("stock/profile2", {"symbol": symbol.upper()})

    def get_market_news(self, category: str = "general") -> List[Dict]:
        """
        Get market news.

        Args:
            category: "general", "forex", "crypto", "merger"
        """
        data = self._request("news", {"category": category})
        return data if isinstance(data, list) else []

    def get_company_news(self, symbol: str, from_date: str = None, to_date: str = None) -> List[Dict]:
        """Get news for a specific company"""
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")

        data = self._request("company-news", {
            "symbol": symbol.upper(),
            "from": from_date,
            "to": to_date
        })
        return data if isinstance(data, list) else []


# Singleton instance
_finnhub_service = None


def get_finnhub_service() -> FinnhubService:
    """Get singleton Finnhub service instance"""
    global _finnhub_service
    if _finnhub_service is None:
        _finnhub_service = FinnhubService()
    return _finnhub_service

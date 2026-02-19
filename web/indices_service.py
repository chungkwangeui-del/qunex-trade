"""
Polygon Indices Service (Free Tier)
Provides accurate market indices data using Polygon Indices Free API
Replaces ETF proxy approach with real index values
"""

import os
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import json

try:
    from src.services.async_http_service import AsyncHttpClient
except ImportError:
    AsyncHttpClient = None

logger = logging.getLogger(__name__)

def run_async(coro):
    """Run a coroutine from synchronous code"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class IndicesService:
    """
    Get market indices data using Polygon Indices Free API

    Plan: Free (5 API calls/minute)
    Limitation: End-of-Day data only (not real-time)
    Benefit: Accurate index values vs ETF proxies
    """

    def __init__(self):
        self.api_key = os.getenv("POLYGON_INDICES_API_KEY")
        self.base_url = "https://api.polygon.io"

        # Cache to avoid hitting 5 calls/minute limit
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = timedelta(minutes=5)  # Cache for 5 minutes

    def get_indices_snapshot(self) -> Dict[str, Dict]:
        """
        Get snapshot of major market indices

        Returns:
            Dict with index data:
            {
                "SPX": {
                    "name": "S&P 500",
                    "value": 4783.45,
                    "change": 23.15,
                    "change_percent": 0.49,
                    "updated_at": "2025-01-13T16:00:00Z"
                },
                ...
            }
        """
        # Check cache first
        if self._is_cache_valid():
            logger.info("[Indices] Returning cached data")
            return self._cache

        if not self.api_key:
            logger.warning(
                "[Indices] POLYGON_INDICES_API_KEY not configured, falling back to ETF proxy"
            )
            return {}

        try:
            # Map of ticker symbols to display names
            indices_map = {
                "I:SPX": {"name": "S&P 500", "short": "SPX"},
                "I:DJI": {"name": "Dow Jones", "short": "DJI"},
                "I:NDX": {"name": "NASDAQ 100", "short": "NDX"},
                "I:RUT": {"name": "Russell 2000", "short": "RUT"},
                "I:VIX": {"name": "VIX", "short": "VIX"},
            }

            # Single API call for all indices
            tickers_str = ",".join(indices_map.keys())
            url = f"{self.base_url}/v3/snapshot/indices"

            params = {"ticker.any_of": tickers_str, "apiKey": self.api_key}

            logger.info(f"[Indices] Fetching data for {len(indices_map)} indices")

            if AsyncHttpClient:
                data = run_async(AsyncHttpClient.get(url, params=params, timeout=10))
            else:
                import requests
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 429:
                    logger.error("[Indices] Rate limit exceeded (5 calls/minute)")
                    return self._cache if self._cache else {}
                if response.status_code != 200:
                    logger.error(f"[Indices] API error {response.status_code}: {response.text}")
                    return self._cache if self._cache else {}
                data = response.json()

            if not data:
                logger.warning("[Indices] No data returned from API")
                return self._cache if self._cache else {}

            results = data.get("results", [])

            if not results:
                logger.warning("[Indices] No data results in API response")
                return self._cache if self._cache else {}

            # Parse results
            indices_data = {}

            for result in results:
                ticker = result.get("ticker", "")

                if ticker not in indices_map:
                    continue

                session = result.get("session", {})
                prev_session = result.get("prev_session", {})

                current_value = session.get("close")
                prev_close = prev_session.get("close")

                if not current_value or not prev_close:
                    logger.warning(f"[Indices] Missing price data for {ticker}")
                    continue

                change = current_value - prev_close
                change_percent = (change / prev_close) * 100

                short_name = indices_map[ticker]["short"]

                indices_data[short_name] = {
                    "name": indices_map[ticker]["name"],
                    "value": round(current_value, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "updated_at": session.get("close_time", ""),
                    "ticker": ticker,
                }

            logger.info(f"[Indices] Successfully fetched {len(indices_data)} indices")

            # Update cache
            self._cache = indices_data
            self._cache_timestamp = datetime.now()

            return indices_data

        except requests.Timeout:
            logger.error("[Indices] Request timeout")
            return self._cache if self._cache else {}

        except Exception as e:
            logger.error(f"[Indices] Error fetching data: {e}", exc_info=True)
            return self._cache if self._cache else {}

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self._cache or not self._cache_timestamp:
            return False

        age = datetime.now() - self._cache_timestamp
        return age < self._cache_duration

    def get_single_index(self, ticker: str) -> Optional[Dict]:
        """
        Get data for a single index

        Args:
            ticker: Index ticker (e.g., "SPX", "DJI", "NDX")

        Returns:
            Dict with index data or None if not found
        """
        indices = self.get_indices_snapshot()
        return indices.get(ticker)


# Singleton instance
_indices_service = None


def get_indices_service() -> IndicesService:
    """Get or create IndicesService singleton"""
    global _indices_service
    if _indices_service is None:
        _indices_service = IndicesService()
    return _indices_service

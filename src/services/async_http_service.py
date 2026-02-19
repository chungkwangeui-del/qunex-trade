"""
Async Client for HTTP Requests
Uses aiohttp for non-blocking I/O
"""

import aiohttp
import asyncio
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class AsyncHttpClient:
    """Shared aiohttp client session wrapper"""

    _session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Get or create a shared ClientSession"""
        if cls._session is None or cls._session.closed:
            # Use a connector with limit to prevent too many open connections
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
            cls._session = aiohttp.ClientSession(connector=connector)
        return cls._session

    @classmethod
    async def close(cls):
        """Close the shared session"""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None

    @classmethod
    async def get(cls, url: str, params: Optional[Dict] = None, timeout: int = 10, **kwargs) -> Optional[Dict]:
        """Perform an async GET request and return JSON response"""
        try:
            session = await cls.get_session()
            async with session.get(url, params=params, timeout=timeout, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    logger.error(f"HTTP GET {url} failed with status {response.status}: {text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"Async GET {url} error: {e}")
            return None

    @classmethod
    async def post(cls, url: str, data: Any = None, json: Any = None, timeout: int = 10, **kwargs) -> Optional[Dict]:
        """Perform an async POST request and return JSON response"""
        try:
            session = await cls.get_session()
            async with session.post(url, data=data, json=json, timeout=timeout, **kwargs) as response:
                if response.status in (200, 201):
                    return await response.json()
                else:
                    text = await response.text()
                    logger.error(f"HTTP POST {url} failed with status {response.status}: {text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"Async POST {url} error: {e}")
            return None

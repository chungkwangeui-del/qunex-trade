import time
import asyncio
import logging
import random
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class APIQuota:
    rpm_limit: int
    tpm_limit: int
    current_rpm: int = 0
    current_tpm: int = 0
    last_reset: float = field(default_factory=time.time)

class APIGovernor:
    """
    Central authority to manage API calls and prevent Rate Limit issues.
    Implemented as a singleton.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIGovernor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Default quotas for different providers/models
        # These can be adjusted based on actual plan limits
        self.quotas = {
            "gemini-pro": APIQuota(rpm_limit=15, tpm_limit=32000),
            "gemini-flash": APIQuota(rpm_limit=100, tpm_limit=1000000),
            "default": APIQuota(rpm_limit=10, tpm_limit=10000)
        }
        self.lock = asyncio.Lock()
        self._initialized = True

    async def acquire_permission(self, model_key: str, estimated_tokens: int = 500) -> bool:
        """
        Requests permission to make an API call.
        Implements a simple token bucket / sliding window logic.
        """
        async with self.lock:
            quota = self.quotas.get(model_key, self.quotas["default"])
            now = time.time()

            # Reset every minute
            if now - quota.last_reset > 60:
                quota.current_rpm = 0
                quota.current_tpm = 0
                quota.last_reset = now

            if quota.current_rpm >= quota.rpm_limit:
                wait_time = 60 - (now - quota.last_reset)
                logger.warning(f"Rate limit approaching for {model_key}. Need to wait {wait_time:.1f}s")
                return False

            # Allow the call
            quota.current_rpm += 1
            quota.current_tpm += estimated_tokens
            return True

    async def execute_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes an async function with exponential backoff.
        """
        retries = 0
        max_retries = 5
        base_delay = 2

        while retries < max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    retries += 1
                    delay = (base_delay ** retries) + (random.random() * 2)
                    logger.warning(f"Rate limit hit. Retrying in {delay:.1f}s... ({retries}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise e

        raise Exception("Max retries exceeded for API call")

def get_governor() -> APIGovernor:
    return APIGovernor()

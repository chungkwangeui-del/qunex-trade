"""
🌐 API Health Checker
Monitors the health of external APIs and services.
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import aiohttp for async requests
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# Fallback to requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class APIEndpoint:
    """An API endpoint to monitor."""
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    timeout: int = 10
    headers: dict = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    endpoint: str
    url: str
    status: str  # healthy, degraded, down
    response_time_ms: float = 0
    status_code: int = 0
    error: str = ""
    checked_at: str = ""


class APIHealthChecker:
    """
    Monitors the health of external APIs and services.
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config/api_endpoints.json")
        self.endpoints = self._load_endpoints()
        self.history: list[dict] = []
        self.results: list[HealthCheckResult] = []

    def _load_endpoints(self) -> list[APIEndpoint]:
        """Load API endpoints from config."""
        endpoints = []

        # Default endpoints (common services to check)
        default_endpoints = [
            APIEndpoint(name="GitHub", url="https://api.github.com", timeout=5),
            APIEndpoint(name="Google", url="https://www.google.com", timeout=5),
        ]

        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text())
                for ep in data.get('endpoints', []):
                    endpoints.append(APIEndpoint(**ep))
            except Exception as e:
                logger.error(f"Error loading API config: {e}")

        return endpoints or default_endpoints

    def add_endpoint(self, name: str, url: str, **kwargs):
        """Add a new endpoint to monitor."""
        endpoint = APIEndpoint(name=name, url=url, **kwargs)
        self.endpoints.append(endpoint)
        self._save_endpoints()

    def _save_endpoints(self):
        """Save endpoints to config file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'endpoints': [
                    {
                        'name': ep.name,
                        'url': ep.url,
                        'method': ep.method,
                        'expected_status': ep.expected_status,
                        'timeout': ep.timeout
                    }
                    for ep in self.endpoints
                ]
            }
            self.config_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error saving API config: {e}")

    def check_endpoint_sync(self, endpoint: APIEndpoint) -> HealthCheckResult:
        """Check endpoint health synchronously."""
        result = HealthCheckResult(
            endpoint=endpoint.name,
            url=endpoint.url,
            checked_at=datetime.now().isoformat()
        )

        if not HAS_REQUESTS:
            result.status = "unknown"
            result.error = "requests library not installed"
            return result

        start_time = time.time()

        try:
            response = requests.request(
                method=endpoint.method,
                url=endpoint.url,
                timeout=endpoint.timeout,
                headers=endpoint.headers,
                allow_redirects=True
            )

            result.response_time_ms = (time.time() - start_time) * 1000
            result.status_code = response.status_code

            if response.status_code == endpoint.expected_status:
                if result.response_time_ms < 1000:
                    result.status = "healthy"
                else:
                    result.status = "degraded"
            else:
                result.status = "degraded"
                result.error = f"Unexpected status code: {response.status_code}"

        except requests.exceptions.Timeout:
            result.status = "down"
            result.error = "Request timed out"
            result.response_time_ms = endpoint.timeout * 1000
        except requests.exceptions.ConnectionError:
            result.status = "down"
            result.error = "Connection failed"
        except Exception as e:
            result.status = "down"
            result.error = str(e)

        return result

    async def check_endpoint_async(self, endpoint: APIEndpoint) -> HealthCheckResult:
        """Check endpoint health asynchronously."""
        result = HealthCheckResult(
            endpoint=endpoint.name,
            url=endpoint.url,
            checked_at=datetime.now().isoformat()
        )

        if not HAS_AIOHTTP:
            # Fall back to sync check
            return self.check_endpoint_sync(endpoint)

        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=endpoint.method,
                    url=endpoint.url,
                    headers=endpoint.headers
                ) as response:
                    result.response_time_ms = (time.time() - start_time) * 1000
                    result.status_code = response.status

                    if response.status == endpoint.expected_status:
                        if result.response_time_ms < 1000:
                            result.status = "healthy"
                        else:
                            result.status = "degraded"
                    else:
                        result.status = "degraded"
                        result.error = f"Unexpected status code: {response.status}"

        except asyncio.TimeoutError:
            result.status = "down"
            result.error = "Request timed out"
            result.response_time_ms = endpoint.timeout * 1000
        except Exception as e:
            result.status = "down"
            result.error = str(e)

        return result

    async def check_all(self) -> list[HealthCheckResult]:
        """Check all endpoints."""
        print("  🌐 Checking API health...")

        if HAS_AIOHTTP:
            # Async check all
            tasks = [self.check_endpoint_async(ep) for ep in self.endpoints]
            self.results = await asyncio.gather(*tasks)
        else:
            # Sync check all
            self.results = [self.check_endpoint_sync(ep) for ep in self.endpoints]

        # Record in history
        for result in self.results:
            self.history.append({
                'endpoint': result.endpoint,
                'status': result.status,
                'response_time_ms': result.response_time_ms,
                'checked_at': result.checked_at
            })

        # Keep only last 1000 entries
        self.history = self.history[-1000:]

        return self.results

    def get_status_summary(self) -> dict:
        """Get summary of API health status."""
        if not self.results:
            return {'status': 'unknown', 'message': 'No checks performed yet'}

        healthy = sum(1 for r in self.results if r.status == 'healthy')
        degraded = sum(1 for r in self.results if r.status == 'degraded')
        down = sum(1 for r in self.results if r.status == 'down')

        if down > 0:
            overall_status = 'critical'
        elif degraded > 0:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'

        return {
            'status': overall_status,
            'total': len(self.results),
            'healthy': healthy,
            'degraded': degraded,
            'down': down,
            'avg_response_time': round(
                sum(r.response_time_ms for r in self.results) / len(self.results), 1
            )
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate API health report."""
        output = output_path or Path("reports/api_health.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        summary = self.get_status_summary()

        # Status emoji
        status_emoji = {
            'healthy': '🟢',
            'warning': '🟠',
            'critical': '🔴',
            'unknown': '⚪'
        }.get(summary.get('status', 'unknown'), '⚪')

        report = """# 🌐 API Health Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Status: {status_emoji} {summary.get('status', 'unknown').upper()}

## Summary

| Metric | Value |
|--------|-------|
| Total Endpoints | {summary.get('total', 0)} |
| Healthy | {summary.get('healthy', 0)} |
| Degraded | {summary.get('degraded', 0)} |
| Down | {summary.get('down', 0)} |
| Avg Response Time | {summary.get('avg_response_time', 0)} ms |

## Endpoint Status

| Endpoint | Status | Response Time | Details |
|----------|--------|---------------|---------|
"""
        for result in self.results:
            status_icon = {
                'healthy': '🟢',
                'degraded': '🟠',
                'down': '🔴'
            }.get(result.status, '⚪')

            details = f"Status: {result.status_code}" if result.status_code else result.error[:30]

            report += f"| {result.endpoint} | {status_icon} {result.status} | {result.response_time_ms:.0f} ms | {details} |\n"

        # Issues section
        down_endpoints = [r for r in self.results if r.status == 'down']
        if down_endpoints:
            report += "\n## ⚠️ Issues Detected\n\n"
            for ep in down_endpoints:
                report += f"- **{ep.endpoint}** is DOWN: {ep.error}\n"

        report += "\n---\n*Report generated by API Health Checker*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_checker: Optional[APIHealthChecker] = None

def get_api_health_checker() -> APIHealthChecker:
    """Get or create API health checker instance."""
    global _checker
    if _checker is None:
        _checker = APIHealthChecker()
    return _checker



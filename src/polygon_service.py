"""Test-friendly wrapper for PolygonService.

Provides a thin facade around :mod:`web.polygon_service` so tests that
import ``src.polygon_service`` can interact with the real implementation
without duplicating logic.
"""

from web.polygon_service import PolygonService  # re-export for tests

__all__ = ["PolygonService"]

"""Test shim for cron_update_ai_scores script."""

from scripts.cron_update_ai_scores import (  # noqa: F401
    calculate_enhanced_features,
    calculate_ai_score,
    determine_rating,
    update_ai_scores,
)
try:
    from scripts.cron_update_ai_scores import FundamentalData  # type: ignore
except ImportError:
    class FundamentalData:  # type: ignore
        def __init__(self, *_, **__):
            pass
from web.polygon_service import PolygonService  # type: ignore

__all__ = [
    "calculate_enhanced_features",
    "calculate_ai_score",
    "determine_rating",
    "update_ai_scores",
    "FundamentalData",
    "PolygonService",
]

# src package to expose services for tests
# This file makes the 'src' package a thin wrapper around the actual implementation in 'web'.

# Export PolygonService
from web.polygon_service import PolygonService, get_polygon_service

# Export NewsCollector and its client
from web.news_collector import NewsCollector, NewsApiClient

# Export other utilities if needed
# (Add more re-exports here as tests require)

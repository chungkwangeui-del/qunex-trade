"""
Real-Time News Collector
Collects credible financial news from multiple reliable sources
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import time

# Configure logging
logger = logging.getLogger(__name__)


class NewsCollector:
    """Collect real-time financial news from reliable sources"""

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")

        # Polygon News API keywords for filtering (market-moving events)
        self.priority_keywords = [
            # Macro/Policy events
            "federal reserve",
            "fed",
            "interest rate",
            "inflation",
            "gdp",
            "cpi",
            "trump",
            "biden",
            "government",
            "congress",
            "senate",
            "treasury",
            # Market events
            "market crash",
            "market rally",
            "s&p 500",
            "nasdaq",
            "dow jones",
            # Company events
            "earnings",
            "merger",
            "acquisition",
            "ceo",
            "ipo",
            "bankruptcy",
        ]

    def collect_from_polygon_filtered(self, limit: int = 100) -> List[Dict]:
        """
        Collect market news from Polygon.io with enhanced filtering

        Uses Polygon's built-in ticker filtering to get relevant news.
        Polygon Starter plan includes unlimited API calls with hourly updates.

        Args:
            limit: Maximum number of articles to fetch (default 100)
        """
        if not self.polygon_key:
            logger.error("POLYGON_API_KEY not found in environment")
            return []

        news_items = []

        try:
            url = "https://api.polygon.io/v2/reference/news"
            params = {
                "apiKey": self.polygon_key,
                "limit": limit,
                "order": "desc",  # Most recent first
            }

            logger.info(f"Fetching news from Polygon API (limit={limit})")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Check for API errors in response
                if data.get("status") == "ERROR":
                    logger.error(f"[Polygon] API returned error: {data.get('error', 'Unknown error')}")
                    return []

                articles = data.get("results", [])

                if not articles:
                    logger.warning("[Polygon] No articles returned from API")
                    return []

                logger.info(f"[Polygon] Retrieved {len(articles)} articles from API")

                for i, article in enumerate(articles):
                    try:
                        # Validate required fields
                        if not article.get("title"):
                            logger.warning(f"Article {i} missing title, skipping")
                            continue

                        if not article.get("article_url"):
                            logger.warning(f"Article {i} missing URL, skipping")
                            continue

                        if not article.get("publisher"):
                            logger.warning(f"Article {i} missing publisher, skipping")
                            continue

                        # Apply quality filter
                        if self._is_quality_news_polygon(article):
                            news_items.append(
                                {
                                    "title": article["title"],
                                    "description": article.get("description", ""),
                                    "content": article.get("description", ""),
                                    "url": article["article_url"],
                                    "source": article["publisher"]["name"],
                                    "published_at": article["published_utc"],
                                    "image_url": article.get("image_url"),
                                    "tickers": article.get("tickers", []),
                                    "collector": "polygon",
                                    "keywords": article.get("keywords", []),
                                }
                            )
                    except KeyError as ke:
                        logger.error(f"Article {i} missing required field: {ke}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing article {i}: {e}")
                        continue

                logger.info(
                    f"[Polygon] Collected {len(news_items)} quality articles from {len(articles)} total"
                )
            elif response.status_code == 401:
                logger.error("[Polygon] API authentication failed - check POLYGON_API_KEY")
            elif response.status_code == 429:
                logger.error("[Polygon] API rate limit exceeded")
            else:
                logger.error(f"[Polygon] API error {response.status_code}: {response.text[:200]}")

        except requests.Timeout:
            logger.error("Polygon API request timed out after 10 seconds")
        except requests.ConnectionError as ce:
            logger.error(f"Failed to connect to Polygon API: {ce}")
        except Exception as e:
            logger.error(f"Error collecting from Polygon API: {e}", exc_info=True)

        return news_items

    def _is_quality_news_polygon(self, article: Dict) -> bool:
        """
        Filter Polygon news for quality and relevance.
        Focus on REAL EVENTS, not analyst opinions or predictions.
        """
        title = article.get("title", "")
        description = article.get("description", "")

        if not title or not description:
            return False

        title_lower = title.lower()
        desc_lower = description.lower()
        combined_text = title_lower + " " + desc_lower

        # FILTER OUT: Analyst opinions, predictions, recommendations
        analyst_keywords = [
            "analyst says",
            "analyst predicts",
            "analyst expects",
            "should you buy",
            "should you sell",
            "time to buy",
            "stock to watch",
            "stocks to buy",
            "top picks",
            "buy rating",
            "sell rating",
            "price target",
            "bull case",
            "bear case",
            "my prediction",
            "could reach",
            "may hit",
            "might see",
            "investor alert",
            "hot stock",
        ]

        for keyword in analyst_keywords:
            if keyword in combined_text:
                return False

        # FILTER OUT: Promotional content
        spam_keywords = [
            "subscribe",
            "click here",
            "limited time",
            "buy now",
            "discount",
            "free trial",
            "advertisement",
            "sponsored",
            "webinar",
            "register now",
            "sign up",
        ]

        for keyword in spam_keywords:
            if keyword in title_lower:
                return False

        return True

    def collect_all_news(self, limit: int = 100) -> List[Dict]:
        """
        Collect news from Polygon.io only (replaced NewsAPI)

        Polygon Starter plan benefits:
        - Unlimited API calls (no 100/day limit like NewsAPI)
        - Real-time news (no 24-hour delay like NewsAPI free tier)
        - Production-ready (NewsAPI free tier is dev-only)
        - Already included in existing $29/month plan

        Args:
            limit: Maximum articles to fetch (default 100)

        Returns:
            List of news items sorted by published time (most recent first)
        """
        logger.info("=" * 60)
        logger.info(f"[NEWS COLLECTOR] Starting Polygon news collection")
        logger.info("=" * 60)

        # Collect from Polygon.io with quality filtering
        all_news = self.collect_from_polygon_filtered(limit=limit)

        # Sort by published time (most recent first)
        all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        logger.info("=" * 60)
        logger.info(f"[SUCCESS] Collected {len(all_news)} quality news items")
        logger.info("=" * 60)

        return all_news


def collect_news() -> List[Dict]:
    """
    Main function to collect news (used by cron job)
    """
    collector = NewsCollector()
    return collector.collect_all_news(limit=100)


if __name__ == "__main__":
    # Test the collector
    from dotenv import load_dotenv

    load_dotenv()

    news = collect_news()

    print(f"\nCollected {len(news)} news items:")
    for i, item in enumerate(news[:5], 1):
        print(f"\n{i}. {item['title']}")
        print(f"   Source: {item['source']}")
        print(f"   Time: {item['published_at']}")
        if item.get("tickers"):
            print(f"   Tickers: {', '.join(item['tickers'][:5])}")

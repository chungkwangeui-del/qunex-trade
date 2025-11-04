"""
Real-Time News Collector
Collects credible financial news from multiple reliable sources
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time


class NewsCollector:
    """Collect real-time financial news from reliable sources"""

    def __init__(self):
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.polygon_key = os.getenv('POLYGON_API_KEY')

        # Reliable financial news sources (tier 1 credibility)
        self.tier1_sources = [
            'bloomberg', 'reuters', 'financial-times', 'wall-street-journal',
            'cnbc', 'marketwatch', 'the-economist', 'fortune'
        ]

        # Additional credible sources (tier 2)
        self.tier2_sources = [
            'business-insider', 'associated-press', 'bbc-news',
            'cnn', 'abc-news', 'nbc-news'
        ]

    def collect_from_newsapi(self, hours: int = 6, tier1_only: bool = True) -> List[Dict]:
        """
        Collect news from NewsAPI

        Args:
            hours: How many hours back to fetch news
            tier1_only: If True, only fetch from tier 1 sources (most reliable)
        """
        if not self.newsapi_key:
            print("[ERROR] NewsAPI key not found")
            return []

        sources = self.tier1_sources if tier1_only else self.tier1_sources + self.tier2_sources

        # Calculate time range
        to_time = datetime.now()
        from_time = to_time - timedelta(hours=hours)

        news_items = []

        # Financial and market keywords (focus on important news)
        keywords = [
            'Federal Reserve', 'Fed', 'interest rate', 'inflation', 'CPI',
            'earnings', 'GDP', 'unemployment', 'Treasury', 'stock market crash',
            'market rally', 'recession', 'economic data', 'jobless claims',
            'FOMC', 'Powell', 'S&P 500', 'Nasdaq', 'Dow Jones'
        ]

        for keyword in keywords:
            try:
                url = 'https://newsapi.org/v2/everything'
                params = {
                    'q': keyword,
                    'from': from_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'to': to_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'apiKey': self.newsapi_key,
                    'pageSize': 10
                }

                # Add sources if available
                if sources:
                    params['sources'] = ','.join(sources)

                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])

                    for article in articles:
                        # Filter out low-quality news
                        if self._is_quality_news(article):
                            news_items.append({
                                'title': article['title'],
                                'description': article.get('description', ''),
                                'content': article.get('content', ''),
                                'url': article['url'],
                                'source': article['source']['name'],
                                'published_at': article['publishedAt'],
                                'image_url': article.get('urlToImage'),
                                'collector': 'newsapi',
                                'keyword': keyword
                            })

                    print(f"[NewsAPI] Collected {len(articles)} articles for keyword: {keyword}")
                else:
                    print(f"[NewsAPI] Error {response.status_code} for keyword: {keyword}")

                # Respect rate limits
                time.sleep(0.5)

            except Exception as e:
                print(f"[NewsAPI] Error collecting keyword '{keyword}': {e}")
                continue

        # Remove duplicates based on title
        unique_news = {}
        for item in news_items:
            if item['title'] not in unique_news:
                unique_news[item['title']] = item

        return list(unique_news.values())

    def collect_from_polygon(self, limit: int = 50) -> List[Dict]:
        """
        Collect market news from Polygon.io (highly reliable, real-time)
        """
        if not self.polygon_key:
            print("[ERROR] Polygon API key not found")
            return []

        news_items = []

        try:
            url = 'https://api.polygon.io/v2/reference/news'
            params = {
                'apiKey': self.polygon_key,
                'limit': limit,
                'order': 'desc'  # Most recent first
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                articles = data.get('results', [])

                for article in articles:
                    # Polygon.io has high-quality, verified news
                    news_items.append({
                        'title': article['title'],
                        'description': article.get('description', ''),
                        'content': article.get('description', ''),  # Polygon doesn't provide full content
                        'url': article['article_url'],
                        'source': article['publisher']['name'],
                        'published_at': article['published_utc'],
                        'image_url': article.get('image_url'),
                        'tickers': article.get('tickers', []),  # Stock tickers mentioned
                        'collector': 'polygon',
                        'keywords': article.get('keywords', [])
                    })

                print(f"[Polygon] Collected {len(articles)} articles")
            else:
                print(f"[Polygon] Error {response.status_code}")

        except Exception as e:
            print(f"[Polygon] Error: {e}")

        return news_items

    def _is_quality_news(self, article: Dict) -> bool:
        """
        Filter out low-quality news
        """
        title = article.get('title', '')
        description = article.get('description', '')

        # Remove articles with missing critical info
        if not title or title == '[Removed]':
            return False

        if not description or len(description) < 50:
            return False

        # Remove promotional content
        spam_keywords = ['subscribe', 'click here', 'limited time', 'buy now',
                        'discount', 'free trial', 'advertisement']

        title_lower = title.lower()
        for keyword in spam_keywords:
            if keyword in title_lower:
                return False

        return True

    def collect_all_news(self, hours: int = 6) -> List[Dict]:
        """
        Collect news from all sources

        Returns:
            List of news items sorted by published time (most recent first)
        """
        print(f"\n{'='*60}")
        print(f"[NEWS COLLECTOR] Starting collection (last {hours} hours)")
        print(f"{'='*60}\n")

        all_news = []

        # Collect from NewsAPI (tier 1 sources only for credibility)
        print("[1/2] Collecting from NewsAPI...")
        newsapi_items = self.collect_from_newsapi(hours=hours, tier1_only=True)
        all_news.extend(newsapi_items)

        # Collect from Polygon.io
        print("\n[2/2] Collecting from Polygon.io...")
        polygon_items = self.collect_from_polygon(limit=50)
        all_news.extend(polygon_items)

        # Remove duplicates
        unique_news = {}
        for item in all_news:
            title = item['title']
            if title not in unique_news:
                unique_news[title] = item

        final_news = list(unique_news.values())

        # Sort by published time (most recent first)
        final_news.sort(
            key=lambda x: x.get('published_at', ''),
            reverse=True
        )

        print(f"\n{'='*60}")
        print(f"[SUCCESS] Collected {len(final_news)} unique news items")
        print(f"{'='*60}\n")

        return final_news


if __name__ == '__main__':
    # Test the collector
    from dotenv import load_dotenv
    load_dotenv()

    collector = NewsCollector()
    news = collector.collect_all_news(hours=12)

    print(f"\nCollected {len(news)} news items:")
    for i, item in enumerate(news[:5], 1):
        print(f"\n{i}. {item['title']}")
        print(f"   Source: {item['source']}")
        print(f"   Time: {item['published_at']}")

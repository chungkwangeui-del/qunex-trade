"""
Real-time News Collection System
- Collects news from NewsAPI, Alpha Vantage News, Yahoo Finance, etc.
- Filters US stock market related news
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NewsCollector:
    """US Stock Market News Collector"""

    def __init__(self):
        self.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        self.alphavantage_key = os.getenv('ALPHAVANTAGE_KEY', '')

        # Market news category keywords (prioritized by impact)
        self.high_priority_keywords = [
            'Federal Reserve', 'Fed', 'Jerome Powell', 'FOMC',
            'interest rate', 'inflation', 'CPI', 'PPI',
            'GDP', 'unemployment', 'job report', 'nonfarm payrolls',
            'Treasury', 'Janet Yellen', 'SEC', 'regulation',
            'White House', 'Congress', 'Biden', 'economic policy'
        ]

        self.medium_priority_keywords = [
            'S&P 500', 'Nasdaq', 'Dow Jones', 'stock market',
            'earnings', 'revenue', 'merger', 'acquisition',
            'IPO', 'bankruptcy', 'sector'
        ]

    def collect_news_api(self, hours: int = 72) -> List[Dict]:
        """
        Collect news from NewsAPI (using top-headlines for better results)
        """
        if not self.newsapi_key:
            print("[WARNING] NEWSAPI_KEY is not configured.")
            return []

        # Use top-headlines instead of everything (more reliable)
        url = 'https://newsapi.org/v2/top-headlines'

        # Focus on government and Fed news first (high impact)
        params = {
            'apiKey': self.newsapi_key,
            'country': 'us',
            'category': 'business',
            'language': 'en',
            'pageSize': 100
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            articles = data.get('articles', [])

            news_list = []
            for article in articles:
                news_item = {
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published_at': article.get('publishedAt', ''),
                    'image_url': article.get('urlToImage', ''),
                    'collected_at': datetime.now().isoformat()
                }
                news_list.append(news_item)

            print(f"[NewsAPI] Collected {len(news_list)} news items")
            return news_list

        except Exception as e:
            print(f"[ERROR] NewsAPI collection failed: {e}")
            return []

    def collect_alpha_vantage_news(self, tickers: Optional[List[str]] = None) -> List[Dict]:
        """
        Collect news from Alpha Vantage News API
        """
        if not self.alphavantage_key:
            print("[WARNING] ALPHAVANTAGE_KEY is not configured.")
            return []

        url = 'https://www.alphavantage.co/query'

        # Use general market news if no tickers provided
        topics = tickers if tickers else ['technology', 'finance', 'economy']

        news_list = []

        for topic in topics[:5]:  # Consider API call limits
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers' if tickers else 'topics': topic,
                'apikey': self.alphavantage_key,
                'limit': 50
            }

            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                feed = data.get('feed', [])

                for article in feed:
                    news_item = {
                        'title': article.get('title', ''),
                        'summary': article.get('summary', ''),
                        'url': article.get('url', ''),
                        'source': article.get('source', 'Unknown'),
                        'published_at': article.get('time_published', ''),
                        'sentiment_score': article.get('overall_sentiment_score', 0),
                        'sentiment_label': article.get('overall_sentiment_label', 'Neutral'),
                        'ticker_sentiment': article.get('ticker_sentiment', []),
                        'topics': article.get('topics', []),
                        'collected_at': datetime.now().isoformat()
                    }
                    news_list.append(news_item)

            except Exception as e:
                print(f"[ERROR] Alpha Vantage collection failed ({topic}): {e}")
                continue

        print(f"[Alpha Vantage] Collected {len(news_list)} news items")
        return news_list

    def get_yahoo_finance_news(self, ticker: str = '^GSPC') -> List[Dict]:
        """
        Get news from Yahoo Finance RSS
        """
        # Yahoo Finance provides RSS feed
        # Omitted for simple implementation, use feedparser library if needed
        return []

    def collect_all_news(self, hours: int = 24) -> List[Dict]:
        """
        Collect news from all sources and prioritize by impact
        """
        all_news = []

        # NewsAPI (government/Fed focused)
        newsapi_news = self.collect_news_api(hours=hours)
        all_news.extend(newsapi_news)

        # Alpha Vantage (use economy topic for government news)
        alphavantage_news = self.collect_alpha_vantage_news(tickers=['economy', 'finance'])
        all_news.extend(alphavantage_news)

        # Remove duplicates (based on URL)
        seen_urls = set()
        unique_news = []

        for news in all_news:
            url = news.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)

        # Prioritize government/Fed news
        unique_news = self._prioritize_news(unique_news)

        print(f"\nTotal {len(unique_news)} unique news items collected (prioritized by impact)")
        return unique_news

    def _prioritize_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        Prioritize news items based on keyword importance
        """
        def get_priority_score(news_item):
            title = news_item.get('title', '').lower()
            description = news_item.get('description', news_item.get('summary', '')).lower()
            full_text = f"{title} {description}"

            # High priority: government/Fed news = score 3
            if any(keyword.lower() in full_text for keyword in self.high_priority_keywords):
                return 3
            # Medium priority: market/company news = score 2
            elif any(keyword.lower() in full_text for keyword in self.medium_priority_keywords):
                return 2
            # Low priority = score 1
            else:
                return 1

        # Sort by priority (high to low)
        news_list.sort(key=get_priority_score, reverse=True)
        return news_list

    def save_news(self, news_list: List[Dict], filepath: str = 'data/news.json'):
        """
        Save collected news to JSON file
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)

        print(f"News saved: {filepath}")


if __name__ == '__main__':
    # Test
    collector = NewsCollector()
    news = collector.collect_all_news(hours=24)

    if news:
        collector.save_news(news)
        print(f"\nCollected news samples:")
        for i, article in enumerate(news[:3], 1):
            print(f"\n{i}. {article.get('title', 'No Title')}")
            print(f"   Source: {article.get('source', 'Unknown')}")
            print(f"   URL: {article.get('url', '')}")

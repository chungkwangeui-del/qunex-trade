"""
실시간 뉴스 수집 시스템
- NewsAPI, Alpha Vantage News, Yahoo Finance 등에서 뉴스 수집
- 미국 주식 시장 관련 뉴스 필터링
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
    """미국 주식 뉴스 수집기"""

    def __init__(self):
        self.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        self.alphavantage_key = os.getenv('ALPHAVANTAGE_KEY', '')

        # 뉴스 카테고리 키워드
        self.market_keywords = [
            'Federal Reserve', 'Fed', 'interest rate', 'inflation',
            'GDP', 'unemployment', 'job report', 'CPI', 'PPI',
            'stock market', 'S&P 500', 'Nasdaq', 'Dow Jones',
            'earnings', 'revenue', 'merger', 'acquisition',
            'IPO', 'bankruptcy', 'SEC', 'regulation'
        ]

    def collect_news_api(self, hours: int = 24) -> List[Dict]:
        """
        NewsAPI에서 뉴스 수집
        """
        if not self.newsapi_key:
            print("[경고] NEWSAPI_KEY가 설정되지 않았습니다.")
            return []

        url = 'https://newsapi.org/v2/everything'

        # 시간 범위 설정
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=hours)

        params = {
            'apiKey': self.newsapi_key,
            'q': 'stock market OR Federal Reserve OR interest rate OR inflation',
            'language': 'en',
            'sortBy': 'publishedAt',
            'from': from_date.isoformat(),
            'to': to_date.isoformat(),
            'domains': 'reuters.com,bloomberg.com,wsj.com,cnbc.com,marketwatch.com,ft.com'
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

            print(f"[NewsAPI] {len(news_list)}개 뉴스 수집 완료")
            return news_list

        except Exception as e:
            print(f"[오류] NewsAPI 수집 실패: {e}")
            return []

    def collect_alpha_vantage_news(self, tickers: Optional[List[str]] = None) -> List[Dict]:
        """
        Alpha Vantage News API에서 뉴스 수집
        """
        if not self.alphavantage_key:
            print("[경고] ALPHAVANTAGE_KEY가 설정되지 않았습니다.")
            return []

        url = 'https://www.alphavantage.co/query'

        # 티커가 없으면 전체 시장 뉴스
        topics = tickers if tickers else ['technology', 'finance', 'economy']

        news_list = []

        for topic in topics[:5]:  # API 호출 제한 고려
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
                print(f"[오류] Alpha Vantage 수집 실패 ({topic}): {e}")
                continue

        print(f"[Alpha Vantage] {len(news_list)}개 뉴스 수집 완료")
        return news_list

    def get_yahoo_finance_news(self, ticker: str = '^GSPC') -> List[Dict]:
        """
        Yahoo Finance RSS에서 뉴스 가져오기
        """
        # Yahoo Finance는 RSS 피드 제공
        # 간단한 구현을 위해 생략, 필요시 feedparser 라이브러리 사용
        return []

    def collect_all_news(self, hours: int = 24) -> List[Dict]:
        """
        모든 소스에서 뉴스 수집
        """
        all_news = []

        # NewsAPI
        newsapi_news = self.collect_news_api(hours=hours)
        all_news.extend(newsapi_news)

        # Alpha Vantage
        alphavantage_news = self.collect_alpha_vantage_news()
        all_news.extend(alphavantage_news)

        # 중복 제거 (URL 기준)
        seen_urls = set()
        unique_news = []

        for news in all_news:
            url = news.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)

        print(f"\n총 {len(unique_news)}개 고유 뉴스 수집 완료")
        return unique_news

    def save_news(self, news_list: List[Dict], filepath: str = 'data/news.json'):
        """
        수집한 뉴스를 JSON 파일로 저장
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)

        print(f"뉴스 저장 완료: {filepath}")


if __name__ == '__main__':
    # 테스트
    collector = NewsCollector()
    news = collector.collect_all_news(hours=24)

    if news:
        collector.save_news(news)
        print(f"\n수집된 뉴스 샘플:")
        for i, article in enumerate(news[:3], 1):
            print(f"\n{i}. {article.get('title', 'No Title')}")
            print(f"   출처: {article.get('source', 'Unknown')}")
            print(f"   URL: {article.get('url', '')}")

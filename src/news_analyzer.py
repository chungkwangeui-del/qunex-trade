"""
AI 기반 뉴스 영향도 분석 시스템
- GPT API를 사용하여 뉴스의 시장 영향도 분석
- 중요도 평가 (1-5 stars)
- 영향받는 주식/섹터 식별
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NewsAnalyzer:
    """뉴스 영향도 분석기"""

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY', '')

        if not self.api_key:
            print("[경고] ANTHROPIC_API_KEY가 설정되지 않았습니다.")

        # 중요도 평가 기준
        self.importance_criteria = {
            5: "전체 시장에 즉각적이고 광범위한 영향 (금리 결정, 대규모 경기 지표)",
            4: "특정 섹터 전체에 큰 영향 (규제 변화, 섹터별 주요 뉴스)",
            3: "중요 기업 또는 중간 규모 영향 (주요 기업 실적, M&A)",
            2: "소규모 영향 또는 단일 종목 (개별 기업 뉴스)",
            1: "최소한의 영향 (루머, 경미한 뉴스)"
        }

    def analyze_news_impact(self, news_item: Dict) -> Dict:
        """
        단일 뉴스 항목의 영향도를 AI로 분석
        """
        if not self.api_key:
            return self._fallback_analysis(news_item)

        try:
            client = anthropic.Anthropic(api_key=self.api_key)

            # Prepare news content
            title = news_item.get('title', '')
            description = news_item.get('description', news_item.get('summary', ''))
            content = news_item.get('content', '')

            news_text = f"""
Title: {title}

Description: {description}

Content: {content[:1000] if content else 'No content available'}
"""

            # Request analysis from Claude
            prompt = f"""Analyze the following news and evaluate its impact on the US stock market:

{news_text}

Please respond in the following JSON format:
{{
    "importance": number between 1-5 (1=minimal impact, 5=market-wide impact),
    "impact_summary": "1-2 sentence summary of the main impact",
    "affected_sectors": ["array of affected sectors"],
    "affected_stocks": ["array of stock tickers that may be affected"],
    "sentiment": "positive/negative/neutral",
    "time_sensitivity": "immediate/short-term/long-term",
    "key_points": ["array of 3-5 key points"]
}}

Importance rating criteria:
5 = Fed rate decisions, GDP, unemployment, etc. - market-wide impact
4 = Major sector regulations, large M&A, etc.
3 = Major company earnings, important corporate news
2 = Individual company general news
1 = Rumors, minor news"""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # 응답 파싱
            response_text = message.content[0].text

            # JSON 추출 (```json ``` 태그 제거)
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()

            analysis = json.loads(response_text)

            # 원본 뉴스 정보 추가
            analysis['news_title'] = title
            analysis['news_url'] = news_item.get('url', '')
            analysis['news_source'] = news_item.get('source', 'Unknown')
            analysis['published_at'] = news_item.get('published_at', '')
            analysis['analyzed_at'] = datetime.now().isoformat()

            return analysis

        except Exception as e:
            print(f"[ERROR] AI analysis failed: {e}")
            return self._fallback_analysis(news_item)

    def _fallback_analysis(self, news_item: Dict) -> Dict:
        """
        Fallback analysis when AI fails (keyword-based)
        """
        title = news_item.get('title', '').lower()
        description = news_item.get('description', news_item.get('summary', '')).lower()
        full_text = f"{title} {description}"

        # Keyword-based importance evaluation
        importance = 1

        high_impact_keywords = ['federal reserve', 'fed', 'interest rate', 'inflation', 'gdp', 'unemployment']
        medium_high_keywords = ['sec', 'regulation', 'merger', 'acquisition', 'earnings', 'bankruptcy']
        medium_keywords = ['stock', 'shares', 'market', 'nasdaq', 's&p 500']

        if any(keyword in full_text for keyword in high_impact_keywords):
            importance = 5
        elif any(keyword in full_text for keyword in medium_high_keywords):
            importance = 4
        elif any(keyword in full_text for keyword in medium_keywords):
            importance = 3
        else:
            importance = 2

        # Sentiment analysis (simple keyword-based)
        positive_keywords = ['gain', 'rise', 'surge', 'increase', 'profit', 'growth']
        negative_keywords = ['fall', 'drop', 'decline', 'loss', 'cut', 'reduce']

        positive_count = sum(1 for k in positive_keywords if k in full_text)
        negative_count = sum(1 for k in negative_keywords if k in full_text)

        if positive_count > negative_count:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {
            'importance': importance,
            'impact_summary': news_item.get('title', ''),
            'affected_sectors': [],
            'affected_stocks': [],
            'sentiment': sentiment,
            'time_sensitivity': 'short-term',
            'key_points': [],
            'news_title': news_item.get('title', ''),
            'news_url': news_item.get('url', ''),
            'news_source': news_item.get('source', 'Unknown'),
            'published_at': news_item.get('published_at', ''),
            'analyzed_at': datetime.now().isoformat(),
            'analysis_method': 'fallback'
        }

    def analyze_news_batch(self, news_list: List[Dict], max_items: int = 20) -> List[Dict]:
        """
        Batch analyze multiple news items
        """
        analyzed_news = []

        for i, news_item in enumerate(news_list[:max_items], 1):
            print(f"Analyzing news... ({i}/{min(len(news_list), max_items)})")

            analysis = self.analyze_news_impact(news_item)
            analyzed_news.append(analysis)

        # Sort by importance
        analyzed_news.sort(key=lambda x: x.get('importance', 0), reverse=True)

        return analyzed_news

    def save_analysis(self, analyzed_news: List[Dict], filepath: str = 'data/news_analysis.json'):
        """
        Save analysis results
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analyzed_news, f, ensure_ascii=False, indent=2)

        print(f"Analysis results saved: {filepath}")

    def get_stars_display(self, importance: int) -> str:
        """
        Convert importance to star emoji display
        """
        return '⭐' * importance


if __name__ == '__main__':
    # 테스트
    analyzer = NewsAnalyzer()

    # 샘플 뉴스
    sample_news = {
        'title': 'Federal Reserve cuts interest rates by 0.25%',
        'description': 'The Federal Reserve announced a quarter-point interest rate cut today, citing cooling inflation and economic stability.',
        'source': 'Reuters',
        'url': 'https://example.com/news',
        'published_at': '2024-10-21T10:00:00Z'
    }

    analysis = analyzer.analyze_news_impact(sample_news)
    print("\n분석 결과:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    print(f"\n중요도: {analyzer.get_stars_display(analysis.get('importance', 1))}")

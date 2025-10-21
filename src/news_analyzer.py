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

            # 뉴스 내용 준비
            title = news_item.get('title', '')
            description = news_item.get('description', news_item.get('summary', ''))
            content = news_item.get('content', '')

            news_text = f"""
제목: {title}

설명: {description}

본문: {content[:1000] if content else '본문 없음'}
"""

            # Claude에게 분석 요청
            prompt = f"""다음 뉴스를 분석하여 미국 주식 시장에 미치는 영향을 평가해주세요:

{news_text}

다음 JSON 형식으로 응답해주세요:
{{
    "importance": 1-5 사이의 숫자 (1=최소 영향, 5=전체 시장 영향),
    "impact_summary": "뉴스의 주요 영향을 1-2문장으로 요약",
    "affected_sectors": ["영향받는 섹터들의 배열"],
    "affected_stocks": ["영향받을 수 있는 주요 종목 티커들의 배열"],
    "sentiment": "positive/negative/neutral 중 하나",
    "time_sensitivity": "immediate/short-term/long-term 중 하나",
    "key_points": ["주요 포인트 3-5개의 배열"]
}}

중요도 평가 기준:
5 = 연준 금리 결정, GDP, 실업률 등 전체 시장 영향
4 = 주요 섹터 규제, 대형 M&A 등
3 = 주요 기업 실적, 중요 기업 뉴스
2 = 개별 기업 일반 뉴스
1 = 루머, 경미한 뉴스"""

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
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
            print(f"[오류] AI 분석 실패: {e}")
            return self._fallback_analysis(news_item)

    def _fallback_analysis(self, news_item: Dict) -> Dict:
        """
        AI 분석 실패시 폴백 분석 (키워드 기반)
        """
        title = news_item.get('title', '').lower()
        description = news_item.get('description', news_item.get('summary', '')).lower()
        full_text = f"{title} {description}"

        # 키워드 기반 중요도 평가
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

        # 감정 분석 (간단한 키워드 기반)
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
        여러 뉴스를 일괄 분석
        """
        analyzed_news = []

        for i, news_item in enumerate(news_list[:max_items], 1):
            print(f"뉴스 분석 중... ({i}/{min(len(news_list), max_items)})")

            analysis = self.analyze_news_impact(news_item)
            analyzed_news.append(analysis)

        # 중요도 순으로 정렬
        analyzed_news.sort(key=lambda x: x.get('importance', 0), reverse=True)

        return analyzed_news

    def save_analysis(self, analyzed_news: List[Dict], filepath: str = 'data/news_analysis.json'):
        """
        분석 결과 저장
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analyzed_news, f, ensure_ascii=False, indent=2)

        print(f"분석 결과 저장 완료: {filepath}")

    def get_stars_display(self, importance: int) -> str:
        """
        중요도를 별 이모티콘으로 변환
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

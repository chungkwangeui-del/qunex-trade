"""
AI-Powered News Analyzer
Uses Claude AI to analyze news importance and market impact
Only keeps credible and important news (4-5 stars)
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from anthropic import Anthropic


class NewsAnalyzer:
    """Analyze news using Claude AI for importance and credibility"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-haiku-20240307"  # Fast and cost-effective model

    def analyze_single_news(self, news_item: Dict) -> Dict:
        """
        Analyze a single news item for importance and market impact

        Returns:
            Dict with analysis results or None if not important enough
        """
        title = news_item.get('title', '')
        description = news_item.get('description', '')
        content = news_item.get('content', '')
        source = news_item.get('source', 'Unknown')

        # Combine all text
        full_text = f"Title: {title}\n\nDescription: {description}\n\nContent: {content}"

        prompt = f"""You are a financial news analyst. Analyze this news and provide a structured assessment.

NEWS:
{full_text}

SOURCE: {source}

Provide your analysis in the following JSON format:
{{
    "importance": <1-5 integer, where 5=critical market-moving, 4=very important, 3=important, 2=minor, 1=irrelevant>,
    "credibility": <1-5 integer, where 5=highly credible, 4=credible, 3=somewhat credible, 2=questionable, 1=unreliable>,
    "impact_summary": "<2-3 sentence summary of market impact>",
    "market_wide_impact": <true/false - true if affects entire market (Fed policy, Trump policy, GDP, inflation, etc.), false if only specific stocks/sectors>,
    "affected_stocks": ["<stock tickers that will be affected, max 5. Use 'MARKET-WIDE' if affects entire market>"],
    "affected_sectors": ["<sectors affected, max 3>"],
    "sentiment": "<bullish/bearish/neutral>",
    "time_sensitivity": "<immediate/short-term/long-term>",
    "key_points": ["<3-5 key bullet points>"],
    "reasoning": "<1-2 sentences explaining the importance score>"
}}

IMPORTANT CRITERIA:
- Only give 5 stars to: Federal Reserve decisions, Trump/government policy changes, major economic data (CPI, GDP, jobs), market crashes/rallies, geopolitical crises
- Give 4 stars to: Significant earnings, major company news, important economic indicators, sector-wide events
- Give 3 stars to: Regular earnings, moderate company news, sector updates
- Give 2 stars or below to: Minor news, speculation, opinion pieces, low-impact events

- market_wide_impact should be TRUE for: Fed policy, Trump/Biden policy, GDP, inflation, unemployment, Treasury yields, market crashes, government decisions
- market_wide_impact should be FALSE for: Individual company earnings, stock-specific news, sector-specific news

- Credibility depends on source reputation and factual content (not speculation or opinion)

Respond ONLY with valid JSON, no additional text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,  # Lower temperature for more consistent analysis
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract JSON from response
            response_text = response.content[0].text.strip()

            # Try to parse JSON
            analysis = json.loads(response_text)

            # Validate required fields
            required_fields = ['importance', 'credibility', 'impact_summary']
            if not all(field in analysis for field in required_fields):
                print(f"[WARN] Missing required fields in analysis")
                return None

            # Only keep important and credible news (4-5 stars on both)
            importance = analysis.get('importance', 0)
            credibility = analysis.get('credibility', 0)

            if importance < 4 or credibility < 3:
                print(f"[FILTER] Filtered out: {title[:60]}... (importance={importance}, credibility={credibility})")
                return None

            # Add original news data
            analysis['news_title'] = title
            analysis['news_url'] = news_item.get('url', '')
            analysis['news_source'] = source
            analysis['published_at'] = news_item.get('published_at', '')
            analysis['image_url'] = news_item.get('image_url', '')
            analysis['analyzed_at'] = datetime.now().isoformat()

            print(f"[ANALYZED] {importance}/5 stars - {title[:60]}...")

            return analysis

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON response: {e}")
            print(f"Response: {response_text[:200]}")
            return None
        except Exception as e:
            print(f"[ERROR] Analysis failed: {e}")
            return None

    def analyze_news_batch(self, news_list: List[Dict], max_items: int = 30) -> List[Dict]:
        """
        Analyze multiple news items

        Args:
            news_list: List of news items to analyze
            max_items: Maximum number of items to analyze (to control API costs)

        Returns:
            List of analyzed news (only important ones)
        """
        if not news_list:
            print("[WARN] No news to analyze")
            return []

        print(f"\n{'='*60}")
        print(f"[NEWS ANALYZER] Starting analysis of {min(len(news_list), max_items)} items")
        print(f"{'='*60}\n")

        analyzed_news = []

        for i, news_item in enumerate(news_list[:max_items], 1):
            print(f"\n[{i}/{min(len(news_list), max_items)}] Analyzing...")

            try:
                analysis = self.analyze_single_news(news_item)

                if analysis:
                    analyzed_news.append(analysis)

            except Exception as e:
                print(f"[ERROR] Failed to analyze item {i}: {e}")
                continue

        # Sort by: market_wide_impact first, then importance, then credibility
        analyzed_news.sort(
            key=lambda x: (
                x.get('market_wide_impact', False),  # Market-wide news first
                x.get('importance', 0),               # Then by importance
                x.get('credibility', 0)               # Then by credibility
            ),
            reverse=True
        )

        # Count market-wide vs specific news
        market_wide_count = len([n for n in analyzed_news if n.get('market_wide_impact', False)])

        print(f"\n{'='*60}")
        print(f"[SUCCESS] Analyzed {len(analyzed_news)} important news items")
        print(f"  - Market-Wide Impact: {market_wide_count}")
        print(f"  - 5 stars: {len([n for n in analyzed_news if n.get('importance') == 5])}")
        print(f"  - 4 stars: {len([n for n in analyzed_news if n.get('importance') == 4])}")
        print(f"{'='*60}\n")

        return analyzed_news

    def save_analysis(self, analyzed_news: List[Dict], output_path: str = None):
        """
        Save analyzed news to JSON file

        Args:
            analyzed_news: List of analyzed news items
            output_path: Path to save JSON file (default: data/news_analysis.json)
        """
        if output_path is None:
            # Save to data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            output_path = os.path.join(data_dir, 'news_analysis.json')

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analyzed_news, f, indent=2, ensure_ascii=False)

            print(f"[SAVED] Analysis saved to: {output_path}")
            print(f"[INFO] Total news items: {len(analyzed_news)}")

        except Exception as e:
            print(f"[ERROR] Failed to save analysis: {e}")


if __name__ == '__main__':
    # Test the analyzer
    from dotenv import load_dotenv
    load_dotenv()

    # Test with sample news
    sample_news = {
        'title': 'Federal Reserve Announces Interest Rate Decision',
        'description': 'The Federal Reserve announced a 25 basis point rate cut, marking a shift in monetary policy.',
        'content': 'Federal Reserve officials voted to reduce interest rates by 25 basis points.',
        'source': 'Reuters',
        'url': 'https://example.com',
        'published_at': datetime.now().isoformat()
    }

    analyzer = NewsAnalyzer()
    result = analyzer.analyze_single_news(sample_news)

    if result:
        print("\n" + "="*60)
        print("ANALYSIS RESULT:")
        print("="*60)
        print(json.dumps(result, indent=2))

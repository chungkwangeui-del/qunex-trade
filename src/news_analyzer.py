"""
AI-Powered News Analyzer
Uses Google Gemini Pro to analyze news importance and market impact
Only keeps credible and important news (4-5 stars)
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """Analyze news using Google Gemini Pro for importance and credibility"""

    def __init__(self, model_name: str = "gemini-1.5-pro"):
        """
        Initialize Gemini-based news analyzer
        
        Args:
            model_name: Gemini model to use (default: gemini-1.5-pro)
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

        # System instruction for news analysis
        self.system_prompt = """You are a financial news analyst. Analyze news and provide a structured assessment.

Provide your analysis in the following JSON format:
{
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
}

IMPORTANT CRITERIA - REAL EVENTS ONLY:
- Only give 5 stars to: ACTUAL Federal Reserve decisions, ACTUAL Trump/government policy changes, ACTUAL economic data releases (CPI, GDP, jobs), ACTUAL market crashes/rallies, ACTUAL geopolitical crises
- Give 4 stars to: ACTUAL significant earnings reports, ACTUAL major company announcements (mergers, acquisitions, CEO changes), ACTUAL important economic indicators
- Give 3 stars to: Regular earnings, moderate company news, sector updates
- Give 2 stars or below to: Analyst opinions, predictions, recommendations, speculation, "should you buy", price targets

CRITICAL: Automatically give 1-2 stars to:
- Analyst predictions or opinions ("analyst says", "expected to", "could reach")
- Investment recommendations ("should you buy", "time to buy", "buy rating")
- Speculation ("may", "might", "could", "potential")
- Opinion pieces (not factual reporting)

ONLY give 4-5 stars to FACTUAL EVENTS that ALREADY HAPPENED:
- "Fed cuts rates by 25bps" ✓ (real event)
- "Analyst expects Fed to cut rates" ✗ (opinion/prediction)
- "Apple reports Q3 earnings $1.5B" ✓ (real data)
- "Apple stock could hit $200" ✗ (prediction)

- market_wide_impact should be TRUE for: Fed policy, Trump/Biden policy, GDP, inflation, unemployment, Treasury yields, market crashes, government decisions
- market_wide_impact should be FALSE for: Individual company earnings, stock-specific news, sector-specific news

- Credibility depends on source reputation and FACTUAL REPORTING (not speculation or opinion)

Respond ONLY with valid JSON, no additional text."""

        logger.info(f"NewsAnalyzer initialized with Gemini model: {model_name}")

    def analyze_single_news(self, news_item: Dict) -> Dict:
        """
        Analyze a single news item for importance and market impact

        Uses Google Gemini Pro for fast and accurate news analysis.

        Returns:
            Dict with analysis results or None if not important enough
        """
        title = news_item.get("title", "")
        description = news_item.get("description", "")
        content = news_item.get("content", "")
        source = news_item.get("source", "Unknown")

        # Combine all text
        full_text = f"Title: {title}\n\nDescription: {description}\n\nContent: {content}"

        # User prompt (varies per request)
        user_prompt = f"""NEWS:
{full_text}

SOURCE: {source}"""

        try:
            # Create model with system instruction
            model_with_system = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt
            )

            response = model_with_system.generate_content(
                user_prompt,
                generation_config={
                    "temperature": 0.3,  # Lower temperature for more consistent analysis
                    "max_output_tokens": 1024,
                },
            )

            # Extract JSON from response
            response_text = response.text.strip()

            # Sometimes JSON is wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Try to parse JSON
            analysis = json.loads(response_text)

            # Validate required fields
            required_fields = ["importance", "credibility", "impact_summary"]
            if not all(field in analysis for field in required_fields):
                logger.warning(f"Missing required fields in analysis for: {title[:60]}")
                return None

            # Only keep important and credible news (4-5 stars on both)
            importance = analysis.get("importance", 0)
            credibility = analysis.get("credibility", 0)

            if importance < 4 or credibility < 3:
                logger.debug(
                    f"Filtered out: {title[:60]}... (importance={importance}, credibility={credibility})"
                )
                return None

            # Add original news data
            analysis["news_title"] = title
            analysis["news_url"] = news_item.get("url", "")
            analysis["news_source"] = source
            analysis["published_at"] = news_item.get("published_at", "")
            analysis["image_url"] = news_item.get("image_url", "")
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analyzer"] = "gemini"

            logger.info(f"Analyzed {importance}/5 stars - {title[:60]}...")

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response in analyze_news: {e}", exc_info=True)
            logger.error(f"Response: {response_text[:200] if 'response_text' in locals() else 'No response'}")
            return None
        except Exception as e:
            logger.error(f"Analysis failed in analyze_news: {e}", exc_info=True)
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
            logger.warning("No news to analyze")
            return []

        logger.info("=" * 60)
        logger.info(f"Starting analysis of {min(len(news_list), max_items)} news items")
        logger.info("=" * 60)

        analyzed_news = []

        for i, news_item in enumerate(news_list[:max_items], 1):
            logger.info(f"Analyzing [{i}/{min(len(news_list), max_items)}]...")

            try:
                analysis = self.analyze_single_news(news_item)

                if analysis:
                    analyzed_news.append(analysis)

            except Exception as e:
                logger.error(
                    f"Failed to analyze item {i} in analyze_news_batch: {e}", exc_info=True
                )
                continue

        # Sort by: market_wide_impact first, then importance, then credibility
        analyzed_news.sort(
            key=lambda x: (
                x.get("market_wide_impact", False),  # Market-wide news first
                x.get("importance", 0),  # Then by importance
                x.get("credibility", 0),  # Then by credibility
            ),
            reverse=True,
        )

        # Count market-wide vs specific news
        market_wide_count = len([n for n in analyzed_news if n.get("market_wide_impact", False)])

        logger.info("=" * 60)
        logger.info(f"Analyzed {len(analyzed_news)} important news items")
        logger.info(f"  - Market-Wide Impact: {market_wide_count}")
        logger.info(f"  - 5 stars: {len([n for n in analyzed_news if n.get('importance') == 5])}")
        logger.info(f"  - 4 stars: {len([n for n in analyzed_news if n.get('importance') == 4])}")
        logger.info("=" * 60)

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
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(data_dir, exist_ok=True)
            output_path = os.path.join(data_dir, "news_analysis.json")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(analyzed_news, f, indent=2, ensure_ascii=False)

            logger.info(f"Analysis saved to: {output_path}")
            logger.info(f"Total news items saved: {len(analyzed_news)}")

        except Exception as e:
            logger.error(f"Failed to save analysis in save_analysis: {e}", exc_info=True)


def analyze_with_claude(news_item: Dict) -> Dict:
    """
    Standalone function to analyze a single news item (used by cron job)
    
    Note: This function name is kept for backward compatibility.
    It now uses Gemini Pro instead of Claude.

    Args:
        news_item: Dictionary with news data

    Returns:
        Dictionary with AI analysis (rating, sentiment, analysis text)
    """
    analyzer = NewsAnalyzer()
    analysis = analyzer.analyze_single_news(news_item)

    if not analysis:
        # Return default values if analysis fails or news is not important
        return {
            "rating": 2,
            "sentiment": "neutral",
            "analysis": "News filtered out - not important enough or low credibility",
        }

    # Convert to format expected by database
    return {
        "rating": analysis.get("importance", 3),
        "sentiment": analysis.get("sentiment", "neutral"),
        "analysis": analysis.get("impact_summary", ""),
    }


if __name__ == "__main__":
    # Test the analyzer
    from dotenv import load_dotenv

    load_dotenv()

    # Test with sample news
    sample_news = {
        "title": "Federal Reserve Announces Interest Rate Decision",
        "description": "The Federal Reserve announced a 25 basis point rate cut, marking a shift in monetary policy.",
        "content": "Federal Reserve officials voted to reduce interest rates by 25 basis points.",
        "source": "Reuters",
        "url": "https://example.com",
        "published_at": datetime.now().isoformat(),
    }

    result = analyze_with_claude(sample_news)

    print("\n" + "=" * 60)
    print("ANALYSIS RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("\nUsing Gemini Pro ✅")
    print("Model: gemini-1.5-pro ✅")

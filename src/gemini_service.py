"""
Google Gemini Pro Service
Uses Gemini 1.5 Pro for AI-powered analysis and assistance
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)


class GeminiService:
    """
    Service class for interacting with Google Gemini Pro API
    Supports various use cases including news analysis, market insights, and general AI assistance
    """

    def __init__(self, model_name: str = "gemini-1.5-pro"):
        """
        Initialize Gemini service

        Args:
            model_name: Gemini model to use. Options:
                - "gemini-1.5-pro" (recommended, most capable)
                - "gemini-1.5-flash" (faster, more cost-effective)
                - "gemini-pro" (previous generation)
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        
        logger.info(f"Gemini service initialized with model: {model_name}")

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        response_format: Optional[str] = "json",
    ) -> Dict[str, Any]:
        """
        Generate text response from Gemini

        Args:
            prompt: User prompt/question
            system_instruction: System instruction to guide model behavior
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic
            max_output_tokens: Maximum tokens in response
            response_format: Format for response ("json" or None for free text)

        Returns:
            Dictionary with response data
        """
        try:
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }

            # Add JSON format instruction if requested
            if response_format == "json":
                full_prompt = f"{prompt}\n\nPlease respond in valid JSON format only."
            else:
                full_prompt = prompt

            # Configure system instruction if provided
            if system_instruction:
                generation_config["system_instruction"] = system_instruction

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            response_text = response.text.strip()

            # Try to parse as JSON if requested
            if response_format == "json":
                try:
                    # Sometimes JSON is wrapped in markdown code blocks
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                    parsed_json = json.loads(response_text)
                    return {
                        "success": True,
                        "text": response_text,
                        "json": parsed_json,
                        "model": self.model_name,
                    }
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response, returning as text")
                    return {
                        "success": True,
                        "text": response_text,
                        "json": None,
                        "model": self.model_name,
                    }
            else:
                return {
                    "success": True,
                    "text": response_text,
                    "model": self.model_name,
                }

        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "model": self.model_name,
            }

    def analyze_news(self, news_item: Dict) -> Optional[Dict]:
        """
        Analyze a single news item (similar to NewsAnalyzer but using Gemini)

        Args:
            news_item: Dictionary with news data (title, description, content, source, url)

        Returns:
            Analysis dictionary or None if not important enough
        """
        title = news_item.get("title", "")
        description = news_item.get("description", "")
        content = news_item.get("content", "")
        source = news_item.get("source", "Unknown")

        # System instruction for news analysis
        system_instruction = """You are a financial news analyst. Analyze news and provide a structured assessment.

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

Respond ONLY with valid JSON, no additional text."""

        # User prompt
        user_prompt = f"""NEWS:
Title: {title}

Description: {description}

Content: {content}

SOURCE: {source}"""

        result = self.generate_text(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=0.3,  # Lower temperature for consistent analysis
            max_output_tokens=1024,
            response_format="json",
        )

        if not result["success"]:
            logger.error(f"Failed to analyze news: {result.get('error')}")
            return None

        if not result.get("json"):
            logger.warning(f"Failed to parse analysis for: {title[:60]}")
            return None

        analysis = result["json"]

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

    def get_market_insight(self, question: str, context: Optional[str] = None) -> Dict:
        """
        Get market insight or answer trading-related questions

        Args:
            question: Question about market, stocks, or trading
            context: Optional context (e.g., current market conditions, specific stocks)

        Returns:
            Dictionary with insight/answer
        """
        system_instruction = """You are a professional financial analyst and trading expert. 
Provide clear, concise, and accurate insights about the stock market, trading strategies, and financial markets.
Focus on factual information and data-driven analysis."""

        prompt = question
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}"

        result = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.7,
            max_output_tokens=1024,
        )

        return result

    def summarize_data(self, data: str, summary_type: str = "general") -> Dict:
        """
        Summarize financial data, reports, or information

        Args:
            data: Data to summarize
            summary_type: Type of summary ("general", "trading", "news", "earnings")

        Returns:
            Dictionary with summary
        """
        system_instructions = {
            "general": "Summarize the following information concisely.",
            "trading": "Summarize this trading data, highlighting key metrics and actionable insights.",
            "news": "Summarize this news, focusing on market impact and implications.",
            "earnings": "Summarize this earnings data, highlighting key financial metrics and trends.",
        }

        system_instruction = system_instructions.get(
            summary_type, system_instructions["general"]
        )

        prompt = f"Please summarize the following:\n\n{data}"

        result = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.5,
            max_output_tokens=512,
        )

        return result


def analyze_with_gemini(news_item: Dict) -> Dict:
    """
    Standalone function to analyze a single news item using Gemini (similar to analyze_with_claude)

    Args:
        news_item: Dictionary with news data

    Returns:
        Dictionary with AI analysis (rating, sentiment, analysis text)
    """
    try:
        service = GeminiService()
        analysis = service.analyze_news(news_item)

        if not analysis:
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
    except Exception as e:
        logger.error(f"Error in analyze_with_gemini: {e}", exc_info=True)
        return {
            "rating": 2,
            "sentiment": "neutral",
            "analysis": f"Analysis failed: {str(e)}",
        }


if __name__ == "__main__":
    # Test the service
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

    print("\n" + "=" * 60)
    print("Testing Gemini Service")
    print("=" * 60)

    try:
        service = GeminiService()
        result = analyze_with_gemini(sample_news)
        print("\nAnalysis Result:")
        print(json.dumps(result, indent=2))

        print("\n" + "=" * 60)
        print("Testing Market Insight")
        print("=" * 60)
        insight = service.get_market_insight(
            "What are the key factors to consider when trading penny stocks?"
        )
        if insight["success"]:
            print(f"\nInsight:\n{insight['text']}")

    except ValueError as e:
        print(f"\nError: {e}")
        print("\nTo use Gemini service:")
        print("1. Get API key from: https://makersuite.google.com/app/apikey")
        print("2. Set environment variable: GEMINI_API_KEY=your_key_here")
        print("3. Or add to .env file: GEMINI_API_KEY=your_key_here")

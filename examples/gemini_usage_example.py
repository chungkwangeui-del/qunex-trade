"""
Example: How to use Gemini Pro in your project

This file demonstrates various ways to integrate Gemini Pro into your trading application.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gemini_service import GeminiService, analyze_with_gemini

# Load environment variables
load_dotenv()


def example_1_basic_usage():
    """Example 1: Basic text generation"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Text Generation")
    print("=" * 60)

    service = GeminiService()

    prompt = "Explain what penny stocks are in 2-3 sentences."
    result = service.generate_text(prompt, temperature=0.7)

    if result["success"]:
        print(f"\nResponse:\n{result['text']}")
    else:
        print(f"\nError: {result.get('error')}")


def example_2_news_analysis():
    """Example 2: Analyze news articles (alternative to Claude)"""
    print("\n" + "=" * 60)
    print("Example 2: News Analysis")
    print("=" * 60)

    sample_news = {
        "title": "Fed Raises Interest Rates by 0.25%",
        "description": "Federal Reserve increases benchmark interest rate amid inflation concerns",
        "content": "The Federal Reserve announced a quarter-point increase in the federal funds rate...",
        "source": "Bloomberg",
        "url": "https://example.com/news1",
    }

    # Method 1: Use standalone function (similar to analyze_with_claude)
    result = analyze_with_gemini(sample_news)
    print(f"\nRating: {result['rating']}/5")
    print(f"Sentiment: {result['sentiment']}")
    print(f"Analysis: {result['analysis']}")

    # Method 2: Use service directly for more control
    service = GeminiService()
    detailed_analysis = service.analyze_news(sample_news)
    if detailed_analysis:
        print(f"\nDetailed Analysis:")
        print(f"  Importance: {detailed_analysis.get('importance')}/5")
        print(f"  Market-wide impact: {detailed_analysis.get('market_wide_impact')}")
        print(f"  Affected sectors: {detailed_analysis.get('affected_sectors')}")


def example_3_market_insights():
    """Example 3: Get trading insights and answers"""
    print("\n" + "=" * 60)
    print("Example 3: Market Insights")
    print("=" * 60)

    service = GeminiService()

    questions = [
        "What are the key indicators to watch when trading penny stocks?",
        "How does volume affect penny stock prices?",
        "What are the risks of trading penny stocks?",
    ]

    for question in questions:
        print(f"\nQuestion: {question}")
        result = service.get_market_insight(question)
        if result["success"]:
            print(f"Answer: {result['text'][:200]}...")
        else:
            print(f"Error: {result.get('error')}")


def example_4_data_summarization():
    """Example 4: Summarize financial data"""
    print("\n" + "=" * 60)
    print("Example 4: Data Summarization")
    print("=" * 60)

    service = GeminiService()

    # Example earnings data
    earnings_data = """
    Company: ABC Corp
    Revenue: $50M (up 15% YoY)
    Net Income: $5M (up 20% YoY)
    EPS: $0.50 (beat estimates by $0.10)
    Guidance: Raised full-year revenue outlook to $220M-$230M
    """

    result = service.summarize_data(earnings_data, summary_type="earnings")
    if result["success"]:
        print(f"\nSummary:\n{result['text']}")


def example_5_integration_with_web_app():
    """Example 5: How to integrate into Flask web app"""
    print("\n" + "=" * 60)
    print("Example 5: Web App Integration")
    print("=" * 60)

    example_code = '''
# In your web/app.py or a new route file:

from flask import Blueprint, jsonify, request
from src.gemini_service import GeminiService

gemini_bp = Blueprint('gemini', __name__)

@gemini_bp.route('/api/gemini/insight', methods=['POST'])
@login_required
def get_insight():
    """Get AI insight on a trading question"""
    data = request.get_json()
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    try:
        service = GeminiService()
        result = service.get_market_insight(question)
        
        if result['success']:
            return jsonify({
                'success': True,
                'insight': result['text']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error')
            }), 500
            
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

# Register blueprint in your app
# app.register_blueprint(gemini_bp, url_prefix='/api')
'''

    print(example_code)


def example_6_custom_analysis():
    """Example 6: Custom analysis for specific use cases"""
    print("\n" + "=" * 60)
    print("Example 6: Custom Analysis")
    print("=" * 60)

    service = GeminiService()

    # Custom prompt for stock screening
    screening_prompt = """
    Analyze the following stock data and provide insights:
    
    Ticker: XYZ
    Price: $2.50
    Volume: 5M (10-day avg: 2M)
    Market Cap: $100M
    Sector: Technology
    Recent News: New product launch, partnership announcement
    
    Provide analysis on:
    1. Price action potential
    2. Volume significance
    3. Risk factors
    """

    system_instruction = """You are a technical analyst specializing in penny stocks.
Provide concise, data-driven analysis focused on trading opportunities and risks."""

    result = service.generate_text(
        prompt=screening_prompt,
        system_instruction=system_instruction,
        temperature=0.6,
        max_output_tokens=500,
    )

    if result["success"]:
        print(f"\nAnalysis:\n{result['text']}")


if __name__ == "__main__":
    print("Gemini Pro Usage Examples")
    print("=" * 60)
    print("\nMake sure you have set GEMINI_API_KEY in your .env file")
    print("Get API key from: https://makersuite.google.com/app/apikey")
    print("\n" + "=" * 60)

    try:
        # Check if API key is set
        if not os.getenv("GEMINI_API_KEY"):
            print("\n⚠️  ERROR: GEMINI_API_KEY not found!")
            print("\nTo fix this:")
            print("1. Get API key from: https://makersuite.google.com/app/apikey")
            print("2. Add to .env file: GEMINI_API_KEY=your_key_here")
            print("3. Or set environment variable: export GEMINI_API_KEY=your_key_here")
            sys.exit(1)

        # Run examples
        example_1_basic_usage()
        example_2_news_analysis()
        example_3_market_insights()
        example_4_data_summarization()
        example_6_custom_analysis()
        
        # Print integration example
        example_5_integration_with_web_app()

        print("\n" + "=" * 60)
        print("✅ All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

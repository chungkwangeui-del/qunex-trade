"""
AI Chat Assistant API - Stock Analysis Q&A with Gemini AI

Features:
- Natural language stock questions
- Portfolio analysis
- Market explanations
- Trading strategy suggestions
- Real-time price context
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from web.extensions import csrf, limiter
from web.polygon_service import get_polygon_service
from web.database import db, Watchlist, PaperTrade, PaperAccount
import os
import logging
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

api_chat = Blueprint("api_chat", __name__)
csrf.exempt(api_chat)


class StockChatAssistant:
    """AI-powered stock market chat assistant using Gemini"""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self._polygon = None
    
    @property
    def polygon(self):
        """Lazy-load polygon service to avoid initialization issues"""
        if self._polygon is None:
            self._polygon = get_polygon_service()
        return self._polygon

    def get_stock_context(self, ticker: str) -> dict:
        """Get real-time stock data for context"""
        try:
            snapshot = self.polygon.get_snapshot(ticker.upper())
            if snapshot:
                # Extract data from nested structures
                day = snapshot.get("day", {})
                prev_day = snapshot.get("prevDay", {})
                
                return {
                    "ticker": ticker.upper(),
                    "price": snapshot.get("price", 0),
                    "change": snapshot.get("todaysChange", 0),
                    "change_percent": snapshot.get("todaysChangePerc", 0),
                    "volume": day.get("v", 0),
                    "high": day.get("h", 0),
                    "low": day.get("l", 0),
                    "open": day.get("o", 0),
                    "prev_close": prev_day.get("c", 0),
                }
        except Exception as e:
            logger.warning(f"Failed to get stock context for {ticker}: {e}")
        return None

    def get_user_context(self, user_id: int) -> dict:
        """Get user's portfolio and watchlist context"""
        try:
            # Get watchlist
            watchlist = Watchlist.query.filter_by(user_id=user_id).all()
            watchlist_tickers = [w.ticker for w in watchlist]

            # Get paper trading account
            account = PaperAccount.query.filter_by(user_id=user_id).first()
            
            # Get recent paper trades
            recent_trades = PaperTrade.query.filter_by(user_id=user_id)\
                .order_by(PaperTrade.trade_date.desc())\
                .limit(10).all()

            return {
                "watchlist": watchlist_tickers[:10],
                "paper_balance": float(account.balance) if account else 100000,
                "recent_trades": [
                    {"ticker": t.ticker, "type": t.trade_type, "shares": float(t.shares)}
                    for t in recent_trades
                ]
            }
        except Exception as e:
            logger.warning(f"Failed to get user context: {e}")
            return {"watchlist": [], "paper_balance": 100000, "recent_trades": []}

    def extract_tickers(self, message: str) -> list:
        """Extract stock tickers from message"""
        # Common patterns: $AAPL, AAPL, "apple stock"
        ticker_pattern = r'\$?([A-Z]{1,5})\b'
        matches = re.findall(ticker_pattern, message.upper())
        
        # Filter out common words
        common_words = {'I', 'A', 'THE', 'AND', 'OR', 'IS', 'IT', 'TO', 'FOR', 'IN', 'ON', 'AT', 'BE', 'AS', 'SO', 'IF', 'UP', 'DO', 'GO', 'CAN', 'AI', 'VS', 'ETF', 'IPO'}
        return [m for m in matches if m not in common_words and len(m) >= 2]

    def chat(self, message: str, user_id: int = None, conversation_history: list = None) -> dict:
        """Process chat message and generate AI response"""
        try:
            # Check for API key first
            if not self.gemini_key:
                return {
                    "response": "AI assistant is not configured. Please contact the administrator to set up the GEMINI_API_KEY.",
                    "error": True
                }
            
            # Import and configure Gemini
            try:
                import google.generativeai as genai
            except ImportError:
                return {
                    "response": "AI service is not available. The required library is not installed.",
                    "error": True
                }

            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Extract tickers from message
            tickers = self.extract_tickers(message)
            
            # Get stock data for mentioned tickers
            stock_data = {}
            for ticker in tickers[:3]:  # Limit to 3 tickers
                data = self.get_stock_context(ticker)
                if data:
                    stock_data[ticker] = data

            # Get user context if authenticated
            user_context = {}
            if user_id:
                user_context = self.get_user_context(user_id)

            # Build context for AI
            context_parts = []
            
            if stock_data:
                context_parts.append("REAL-TIME STOCK DATA:")
                for ticker, data in stock_data.items():
                    price = data.get('price') or 0
                    change_pct = data.get('change_percent') or 0
                    volume = data.get('volume') or 0
                    high = data.get('high') or 0
                    low = data.get('low') or 0
                    context_parts.append(
                        f"- {ticker}: ${price:.2f} ({change_pct:+.2f}%) "
                        f"Volume: {volume:,.0f} High: ${high:.2f} Low: ${low:.2f}"
                    )

            if user_context.get("watchlist"):
                context_parts.append(f"\nUSER'S WATCHLIST: {', '.join(user_context['watchlist'])}")

            if user_context.get("paper_balance"):
                context_parts.append(f"PAPER TRADING BALANCE: ${user_context['paper_balance']:,.2f}")

            context = "\n".join(context_parts)

            # Build conversation history
            history_text = ""
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    history_text += f"{role}: {msg.get('content', '')}\n"

            system_prompt = """You are Qunex AI, an expert stock market assistant for the Qunex Trade platform.

PERSONALITY:
- Professional but friendly
- Data-driven and analytical
- Concise but thorough
- Cautious about predictions (always mention risks)

CAPABILITIES:
- Explain stock market concepts
- Analyze stock performance using provided real-time data
- Discuss trading strategies (scalping, swing, long-term)
- Help with portfolio decisions
- Explain technical indicators (RSI, MACD, etc.)
- Discuss market news and trends

RULES:
1. Always use the real-time data provided when discussing specific stocks
2. Never give specific financial advice - say "consider" or "you might want to research"
3. Always mention that past performance doesn't guarantee future results
4. Keep responses concise (2-3 paragraphs max unless detailed explanation requested)
5. Use bullet points for lists
6. Mention relevant Qunex Trade features when helpful (Screener, Scalping tool, etc.)
7. If you don't have data for a stock, say so and suggest the user check the Market page

FORMAT:
- Use **bold** for key points
- Use bullet points for lists
- Include specific numbers from the provided data
- End with a relevant follow-up question or suggestion"""

            full_prompt = f"""{system_prompt}

{context if context else "No specific stock data available for this query."}

{f"CONVERSATION HISTORY:{chr(10)}{history_text}" if history_text else ""}

USER MESSAGE: {message}

Respond helpfully and concisely:"""

            response = model.generate_content(full_prompt)
            
            # Handle response safely
            if not response or not response.text:
                return {
                    "response": "I couldn't generate a response. Please try rephrasing your question.",
                    "error": True
                }
            
            response_text = response.text.strip()

            # Extract any stock mentions for quick links
            mentioned_stocks = list(stock_data.keys()) if stock_data else tickers[:3]

            return {
                "response": response_text,
                "stocks_mentioned": mentioned_stocks,
                "stock_data": stock_data,
                "timestamp": datetime.now().isoformat(),
                "error": False
            }

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            
            # Provide more helpful error messages
            error_msg = str(e).lower()
            if "api_key" in error_msg or "invalid" in error_msg:
                user_message = "The AI service is temporarily unavailable. Please try again later."
            elif "quota" in error_msg or "rate" in error_msg:
                user_message = "Too many requests. Please wait a moment and try again."
            elif "blocked" in error_msg or "safety" in error_msg:
                user_message = "I couldn't respond to that query. Please try a different question."
            else:
                user_message = "Sorry, I encountered an error processing your request. Please try again."
            
            return {
                "response": user_message,
                "error": True,
                "error_message": str(e)
            }


# Initialize assistant
chat_assistant = StockChatAssistant()


@api_chat.route("/api/chat", methods=["POST"])
@limiter.limit("30 per minute")
def chat():
    """
    AI Chat endpoint - process user message and return AI response
    
    Request body:
    {
        "message": "What do you think about AAPL?",
        "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    }
    """
    data = request.get_json()
    
    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    message = data.get("message", "").strip()
    history = data.get("history", [])

    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)"}), 400

    # Get user ID if authenticated
    user_id = None
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            user_id = current_user.id
    except:
        pass

    result = chat_assistant.chat(message, user_id, history)
    
    if result.get("error") and "error_message" in result:
        return jsonify(result), 500

    return jsonify(result)


@api_chat.route("/api/chat/suggest", methods=["GET"])
def get_suggestions():
    """Get suggested questions based on market context"""
    suggestions = [
        "What's driving the market today?",
        "Explain RSI and how to use it",
        "What are good scalping strategies for beginners?",
        "How do I find stocks with high momentum?",
        "What's the difference between support and resistance?",
        "How do I read candlestick patterns?",
        "What indicators work best for swing trading?",
        "Explain the Fear & Greed Index",
    ]
    
    # Add contextual suggestions based on time
    hour = datetime.now().hour
    if 9 <= hour < 16:  # Market hours (EST approximation)
        suggestions.insert(0, "What stocks are moving the most right now?")
    else:
        suggestions.insert(0, "What should I prepare for tomorrow's market?")

    return jsonify({"suggestions": suggestions[:8]})


@api_chat.route("/api/chat/quick/<ticker>", methods=["GET"])
def quick_analysis(ticker: str):
    """Quick AI analysis for a specific ticker"""
    ticker = ticker.upper().strip()
    
    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker"}), 400

    message = f"Give me a quick analysis of {ticker} stock - current price action, key levels to watch, and overall sentiment."
    
    result = chat_assistant.chat(message)
    
    return jsonify(result)


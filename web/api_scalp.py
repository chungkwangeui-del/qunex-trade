"""
Scalp Trading Analysis API
AI-powered short-term trading signals using EMA 9/21 + VWAP + RSI strategy
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

api_scalp = Blueprint("api_scalp", __name__)


class ScalpAnalyzer:
    """Technical analysis for scalp trading"""

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    def fetch_bars(self, ticker: str, interval: str = "5", limit: int = 100) -> List[Dict]:
        """Fetch candlestick data from Polygon"""
        try:
            # Map interval to Polygon timespan
            timespan_map = {"1": "minute", "5": "minute", "15": "minute"}
            multiplier_map = {"1": 1, "5": 5, "15": 15}

            timespan = timespan_map.get(interval, "minute")
            multiplier = multiplier_map.get(interval, 5)

            # Get data for last 2 days to ensure enough bars
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)

            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {"apiKey": self.polygon_key, "limit": limit, "sort": "desc"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("resultsCount", 0) > 0:
                # Reverse to get oldest first for calculations
                return list(reversed(data.get("results", [])))
            return []

        except Exception as e:
            logger.error(f"Failed to fetch bars for {ticker}: {e}")
            return []

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return 0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA

        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_vwap(self, bars: List[Dict]) -> float:
        """Calculate Volume Weighted Average Price"""
        if not bars:
            return 0

        total_volume = 0
        total_vwap = 0

        for bar in bars:
            typical_price = (bar.get("h", 0) + bar.get("l", 0) + bar.get("c", 0)) / 3
            volume = bar.get("v", 0)
            total_vwap += typical_price * volume
            total_volume += volume

        if total_volume == 0:
            return 0

        return total_vwap / total_volume

    def calculate_macd(self, prices: List[float]) -> Dict:
        """Calculate MACD (12, 26, 9)"""
        if len(prices) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}

        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        macd_line = ema12 - ema26

        # For signal line, we'd need historical MACD values
        # Simplified: use current MACD as approximation
        return {
            "macd": macd_line,
            "signal": macd_line * 0.9,  # Simplified
            "histogram": macd_line * 0.1,
        }

    def analyze(self, ticker: str, interval: str = "5") -> Dict:
        """Perform complete scalp analysis"""
        try:
            # Fetch price data
            bars = self.fetch_bars(ticker, interval)

            if not bars or len(bars) < 30:
                return {"error": f"Insufficient data for {ticker}"}

            # Extract close prices
            closes = [bar.get("c", 0) for bar in bars]
            current_price = closes[-1]
            prev_price = closes[-2] if len(closes) > 1 else current_price

            # Calculate indicators
            ema9 = self.calculate_ema(closes, 9)
            ema21 = self.calculate_ema(closes, 21)
            rsi = self.calculate_rsi(closes, 14)
            vwap = self.calculate_vwap(bars[-50:])  # Use recent bars for VWAP
            macd_data = self.calculate_macd(closes)

            # Get volume info
            current_volume = bars[-1].get("v", 0)
            avg_volume = sum(bar.get("v", 0) for bar in bars[-20:]) / 20 if len(bars) >= 20 else current_volume

            # Determine signal using Triple Confirmation Strategy
            signal, confidence = self._determine_signal(
                current_price, ema9, ema21, vwap, rsi, macd_data, current_volume, avg_volume
            )

            # Calculate entry/exit levels
            entry_price = current_price
            if signal == "LONG":
                stop_loss = min(current_price * 0.995, vwap * 0.998)  # 0.5% or below VWAP
                take_profit = current_price * 1.01  # 1% target
            elif signal == "SHORT":
                stop_loss = max(current_price * 1.005, vwap * 1.002)
                take_profit = current_price * 0.99
            else:
                stop_loss = current_price * 0.995
                take_profit = current_price * 1.005

            # Generate AI analysis
            analysis = self._generate_ai_analysis(
                ticker, signal, confidence, current_price, ema9, ema21, vwap, rsi, macd_data, interval
            )

            change_percent = ((current_price - prev_price) / prev_price * 100) if prev_price else 0

            return {
                "ticker": ticker,
                "price": current_price,
                "change_percent": change_percent,
                "signal": signal,
                "confidence": confidence,
                "indicators": {
                    "ema9": ema9,
                    "ema21": ema21,
                    "vwap": vwap,
                    "rsi": rsi,
                    "macd": macd_data["macd"],
                    "macd_signal": "Bullish" if macd_data["histogram"] > 0 else "Bearish",
                    "volume": current_volume,
                    "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1,
                },
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward": "1:2",
                "analysis": analysis,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Scalp analysis error for {ticker}: {e}")
            return {"error": str(e)}

    def _determine_signal(
        self,
        price: float,
        ema9: float,
        ema21: float,
        vwap: float,
        rsi: float,
        macd: Dict,
        volume: float,
        avg_volume: float,
    ) -> tuple:
        """Determine trading signal using Triple Confirmation Strategy"""
        bullish_signals = 0
        bearish_signals = 0
        total_weight = 0

        # EMA Cross (weight: 30%)
        if ema9 > ema21:
            bullish_signals += 30
        else:
            bearish_signals += 30
        total_weight += 30

        # Price vs VWAP (weight: 25%)
        if price > vwap:
            bullish_signals += 25
        else:
            bearish_signals += 25
        total_weight += 25

        # RSI 50-level (weight: 25%)
        if rsi > 50:
            bullish_signals += 25
        else:
            bearish_signals += 25
        total_weight += 25

        # MACD (weight: 20%)
        if macd["histogram"] > 0:
            bullish_signals += 20
        else:
            bearish_signals += 20
        total_weight += 20

        # Volume confirmation (bonus)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        volume_bonus = min(10, int(volume_ratio * 5)) if volume_ratio > 1.5 else 0

        # Determine signal
        bullish_score = bullish_signals + (volume_bonus if bullish_signals > bearish_signals else 0)
        bearish_score = bearish_signals + (volume_bonus if bearish_signals > bullish_signals else 0)

        if bullish_score >= 75:
            return "LONG", min(95, bullish_score)
        elif bearish_score >= 75:
            return "SHORT", min(95, bearish_score)
        else:
            return "NEUTRAL", max(bullish_score, bearish_score)

    def _generate_ai_analysis(
        self,
        ticker: str,
        signal: str,
        confidence: int,
        price: float,
        ema9: float,
        ema21: float,
        vwap: float,
        rsi: float,
        macd: Dict,
        interval: str,
    ) -> str:
        """Generate AI-powered analysis using Gemini"""
        try:
            import google.generativeai as genai

            if not self.gemini_key:
                return self._generate_fallback_analysis(signal, confidence, price, ema9, ema21, vwap, rsi)

            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""You are an expert scalp trader. Analyze this {interval}-minute chart data for {ticker} and provide a brief, actionable trading analysis.

CURRENT DATA:
- Price: ${price:.2f}
- EMA 9: ${ema9:.2f} {'(above EMA 21 - bullish)' if ema9 > ema21 else '(below EMA 21 - bearish)'}
- EMA 21: ${ema21:.2f}
- VWAP: ${vwap:.2f} {'(price above - bullish)' if price > vwap else '(price below - bearish)'}
- RSI: {rsi:.1f} {'(above 50 - bullish momentum)' if rsi > 50 else '(below 50 - bearish momentum)'}
- MACD Histogram: {'Positive (bullish)' if macd['histogram'] > 0 else 'Negative (bearish)'}

SIGNAL: {signal} (Confidence: {confidence}%)

Provide a 2-3 sentence analysis covering:
1. Current trend direction and strength
2. Key levels to watch
3. Recommended action (if any)

Keep it brief and professional. Use <strong> tags for important points. Do NOT include entry/exit prices as those are shown separately."""

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.warning(f"Gemini analysis failed: {e}")
            return self._generate_fallback_analysis(signal, confidence, price, ema9, ema21, vwap, rsi)

    def _generate_fallback_analysis(
        self, signal: str, confidence: int, price: float, ema9: float, ema21: float, vwap: float, rsi: float
    ) -> str:
        """Generate fallback analysis without AI"""
        trend = "bullish" if ema9 > ema21 else "bearish"
        momentum = "strong" if abs(rsi - 50) > 15 else "moderate"

        if signal == "LONG":
            return f"""<strong>Bullish Setup Detected:</strong> EMA 9 is above EMA 21 with price trading above VWAP at ${vwap:.2f}. RSI at {rsi:.1f} confirms {momentum} upward momentum. <strong>Consider long entries</strong> with stops below VWAP. Watch for rejection at resistance levels."""
        elif signal == "SHORT":
            return f"""<strong>Bearish Setup Detected:</strong> EMA 9 is below EMA 21 with price trading below VWAP at ${vwap:.2f}. RSI at {rsi:.1f} indicates {momentum} downward momentum. <strong>Consider short entries</strong> with stops above VWAP. Watch for support levels."""
        else:
            return f"""<strong>No Clear Signal:</strong> Mixed signals present. EMA cross is {trend} but other indicators are not aligned. Current price is {'above' if price > vwap else 'below'} VWAP (${vwap:.2f}). RSI at {rsi:.1f}. <strong>Wait for confirmation</strong> before entering any position."""


# Initialize analyzer
analyzer = ScalpAnalyzer()


@api_scalp.route("/api/scalp/analyze/<ticker>")
@login_required
def analyze_ticker(ticker: str):
    """Analyze a ticker for scalp trading opportunities"""
    ticker = ticker.upper().strip()
    interval = request.args.get("interval", "5")

    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    result = analyzer.analyze(ticker, interval)

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


@api_scalp.route("/api/scalp/quick/<ticker>")
def quick_analysis(ticker: str):
    """Quick analysis without login (limited info)"""
    ticker = ticker.upper().strip()
    interval = request.args.get("interval", "5")

    if not ticker or len(ticker) > 10:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    result = analyzer.analyze(ticker, interval)

    if "error" in result:
        return jsonify(result), 400

    # Return limited info for non-logged in users
    return jsonify(
        {
            "ticker": result.get("ticker"),
            "price": result.get("price"),
            "signal": result.get("signal"),
            "confidence": result.get("confidence"),
            "message": "Login for full analysis with entry/exit levels",
        }
    )

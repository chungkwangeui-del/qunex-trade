"""
Scalp Trading Analysis API
AI-powered short-term trading signals with candlestick pattern recognition
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import requests

logger = logging.getLogger(__name__)

api_scalp = Blueprint("api_scalp", __name__)


class CandlestickPatterns:
    """Candlestick pattern detection for scalp trading"""

    @staticmethod
    def get_candle_info(bar: Dict) -> Dict:
        """Extract candle components"""
        o, h, l, c = bar.get("o", 0), bar.get("h", 0), bar.get("l", 0), bar.get("c", 0)
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        total_range = h - l if h != l else 0.0001
        is_bullish = c > o
        is_bearish = c < o

        return {
            "open": o, "high": h, "low": l, "close": c,
            "body": body,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "range": total_range,
            "body_percent": (body / total_range * 100) if total_range else 0,
            "is_bullish": is_bullish,
            "is_bearish": is_bearish,
            "is_doji": body < (total_range * 0.1),  # Body < 10% of range
        }

    @staticmethod
    def detect_hammer(candle: Dict) -> bool:
        """Hammer: small body at top, long lower wick (bullish reversal)"""
        if candle["body_percent"] > 35:
            return False
        if candle["lower_wick"] < candle["body"] * 2:
            return False
        if candle["upper_wick"] > candle["body"] * 0.5:
            return False
        return True

    @staticmethod
    def detect_shooting_star(candle: Dict) -> bool:
        """Shooting Star: small body at bottom, long upper wick (bearish reversal)"""
        if candle["body_percent"] > 35:
            return False
        if candle["upper_wick"] < candle["body"] * 2:
            return False
        if candle["lower_wick"] > candle["body"] * 0.5:
            return False
        return True

    @staticmethod
    def detect_engulfing(prev: Dict, curr: Dict) -> Optional[str]:
        """Engulfing pattern: current candle completely engulfs previous"""
        if prev["is_bearish"] and curr["is_bullish"]:
            if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
                if curr["body"] > prev["body"] * 1.2:
                    return "bullish_engulfing"
        if prev["is_bullish"] and curr["is_bearish"]:
            if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
                if curr["body"] > prev["body"] * 1.2:
                    return "bearish_engulfing"
        return None

    @staticmethod
    def detect_doji(candle: Dict) -> bool:
        """Doji: open ≈ close (indecision)"""
        return candle["is_doji"]

    @staticmethod
    def detect_marubozu(candle: Dict) -> Optional[str]:
        """Marubozu: strong momentum candle with no/tiny wicks"""
        if candle["body_percent"] < 80:
            return None
        if candle["upper_wick"] > candle["body"] * 0.05:
            return None
        if candle["lower_wick"] > candle["body"] * 0.05:
            return None
        return "bullish_marubozu" if candle["is_bullish"] else "bearish_marubozu"

    @staticmethod
    def detect_pin_bar(candle: Dict) -> Optional[str]:
        """Pin Bar: long wick rejection (strong reversal signal)"""
        if candle["body_percent"] > 30:
            return None
        # Bullish pin bar (long lower wick)
        if candle["lower_wick"] > candle["range"] * 0.6:
            return "bullish_pin_bar"
        # Bearish pin bar (long upper wick)
        if candle["upper_wick"] > candle["range"] * 0.6:
            return "bearish_pin_bar"
        return None

    @staticmethod
    def detect_inside_bar(prev: Dict, curr: Dict) -> bool:
        """Inside Bar: current candle within previous range (consolidation)"""
        return curr["high"] < prev["high"] and curr["low"] > prev["low"]

    @classmethod
    def analyze_patterns(cls, bars: List[Dict]) -> Dict:
        """Analyze last few candles for patterns"""
        if len(bars) < 3:
            return {"patterns": [], "bias": "neutral", "strength": 0}

        patterns = []
        bullish_score = 0
        bearish_score = 0

        # Get recent candles
        curr = cls.get_candle_info(bars[-1])
        prev = cls.get_candle_info(bars[-2])
        prev2 = cls.get_candle_info(bars[-3])

        # Check current candle patterns
        if cls.detect_hammer(curr):
            patterns.append({"name": "Hammer", "type": "bullish", "strength": 70})
            bullish_score += 70

        if cls.detect_shooting_star(curr):
            patterns.append({"name": "Shooting Star", "type": "bearish", "strength": 70})
            bearish_score += 70

        if curr["is_doji"]:
            patterns.append({"name": "Doji", "type": "neutral", "strength": 40})

        marubozu = cls.detect_marubozu(curr)
        if marubozu:
            if "bullish" in marubozu:
                patterns.append({"name": "Bullish Marubozu", "type": "bullish", "strength": 80})
                bullish_score += 80
            else:
                patterns.append({"name": "Bearish Marubozu", "type": "bearish", "strength": 80})
                bearish_score += 80

        pin_bar = cls.detect_pin_bar(curr)
        if pin_bar:
            if "bullish" in pin_bar:
                patterns.append({"name": "Bullish Pin Bar", "type": "bullish", "strength": 75})
                bullish_score += 75
            else:
                patterns.append({"name": "Bearish Pin Bar", "type": "bearish", "strength": 75})
                bearish_score += 75

        # Check two-candle patterns
        engulfing = cls.detect_engulfing(prev, curr)
        if engulfing:
            if "bullish" in engulfing:
                patterns.append({"name": "Bullish Engulfing", "type": "bullish", "strength": 85})
                bullish_score += 85
            else:
                patterns.append({"name": "Bearish Engulfing", "type": "bearish", "strength": 85})
                bearish_score += 85

        if cls.detect_inside_bar(prev, curr):
            patterns.append({"name": "Inside Bar", "type": "neutral", "strength": 30})

        # Three-candle pattern: Morning/Evening Star
        if prev["is_doji"] and prev2["is_bearish"] and curr["is_bullish"]:
            if curr["close"] > (prev2["open"] + prev2["close"]) / 2:
                patterns.append({"name": "Morning Star", "type": "bullish", "strength": 90})
                bullish_score += 90

        if prev["is_doji"] and prev2["is_bullish"] and curr["is_bearish"]:
            if curr["close"] < (prev2["open"] + prev2["close"]) / 2:
                patterns.append({"name": "Evening Star", "type": "bearish", "strength": 90})
                bearish_score += 90

        # Determine overall bias
        if bullish_score > bearish_score + 20:
            bias = "bullish"
            strength = min(100, bullish_score)
        elif bearish_score > bullish_score + 20:
            bias = "bearish"
            strength = min(100, bearish_score)
        else:
            bias = "neutral"
            strength = max(bullish_score, bearish_score)

        return {
            "patterns": patterns,
            "bias": bias,
            "strength": strength,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "current_candle": {
                "type": "bullish" if curr["is_bullish"] else ("bearish" if curr["is_bearish"] else "doji"),
                "body_percent": round(curr["body_percent"], 1),
            }
        }


class ScalpAnalyzer:
    """Technical analysis for scalp trading"""

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.candle_patterns = CandlestickPatterns()

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

            # Detect candlestick patterns
            candle_analysis = CandlestickPatterns.analyze_patterns(bars)

            # Get volume info
            current_volume = bars[-1].get("v", 0)
            avg_volume = sum(bar.get("v", 0) for bar in bars[-20:]) / 20 if len(bars) >= 20 else current_volume

            # Determine signal using candlestick + indicators
            signal, confidence = self._determine_signal(
                current_price, ema9, ema21, vwap, rsi, macd_data,
                current_volume, avg_volume, candle_analysis
            )

            # Calculate entry/exit levels based on candle structure
            last_bar = bars[-1]
            candle_low = last_bar.get("l", current_price * 0.995)
            candle_high = last_bar.get("h", current_price * 1.005)

            entry_price = current_price
            if signal == "LONG":
                stop_loss = min(candle_low * 0.998, vwap * 0.998)
                take_profit = current_price + (current_price - stop_loss) * 2  # 1:2 R:R
            elif signal == "SHORT":
                stop_loss = max(candle_high * 1.002, vwap * 1.002)
                take_profit = current_price - (stop_loss - current_price) * 2
            else:
                stop_loss = current_price * 0.995
                take_profit = current_price * 1.005

            # Generate AI analysis with candlestick patterns
            analysis = self._generate_ai_analysis(
                ticker, signal, confidence, current_price, ema9, ema21,
                vwap, rsi, macd_data, interval, candle_analysis
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
                "candlestick": candle_analysis,
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
        candle_analysis: Dict = None,
    ) -> tuple:
        """Determine trading signal with candlestick patterns as primary driver"""
        bullish_signals = 0
        bearish_signals = 0

        # CANDLESTICK PATTERNS (weight: 40%) - Primary driver for scalping
        if candle_analysis:
            candle_bias = candle_analysis.get("bias", "neutral")
            candle_strength = candle_analysis.get("strength", 0)

            if candle_bias == "bullish":
                bullish_signals += min(40, int(candle_strength * 0.45))
            elif candle_bias == "bearish":
                bearish_signals += min(40, int(candle_strength * 0.45))

        # EMA Cross (weight: 20%)
        if ema9 > ema21:
            bullish_signals += 20
        else:
            bearish_signals += 20

        # Price vs VWAP (weight: 20%)
        if price > vwap:
            bullish_signals += 20
        else:
            bearish_signals += 20

        # RSI 50-level (weight: 10%)
        if rsi > 50:
            bullish_signals += 10
        else:
            bearish_signals += 10

        # MACD (weight: 10%)
        if macd["histogram"] > 0:
            bullish_signals += 10
        else:
            bearish_signals += 10

        # Volume confirmation (bonus up to 15%)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        if volume_ratio > 1.5:
            volume_bonus = min(15, int(volume_ratio * 5))
            if bullish_signals > bearish_signals:
                bullish_signals += volume_bonus
            else:
                bearish_signals += volume_bonus

        # Determine signal - candlestick patterns can override with strong signals
        if candle_analysis:
            patterns = candle_analysis.get("patterns", [])
            has_strong_pattern = any(p["strength"] >= 80 for p in patterns)

            if has_strong_pattern:
                # Strong candlestick pattern present
                if bullish_signals >= 60:
                    return "LONG", min(95, bullish_signals + 10)
                elif bearish_signals >= 60:
                    return "SHORT", min(95, bearish_signals + 10)

        # Standard threshold
        if bullish_signals >= 70:
            return "LONG", min(95, bullish_signals)
        elif bearish_signals >= 70:
            return "SHORT", min(95, bearish_signals)
        else:
            return "NEUTRAL", max(bullish_signals, bearish_signals)

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
        candle_analysis: Dict = None,
    ) -> str:
        """Generate AI-powered analysis using Gemini"""
        try:
            import google.generativeai as genai

            if not self.gemini_key:
                return self._generate_fallback_analysis(
                    signal, confidence, price, ema9, ema21, vwap, rsi, candle_analysis
                )

            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Build pattern string
            pattern_str = "None detected"
            if candle_analysis and candle_analysis.get("patterns"):
                patterns = candle_analysis["patterns"]
                pattern_str = ", ".join([f"{p['name']} ({p['type']})" for p in patterns[:3]])

            candle_type = "neutral"
            if candle_analysis:
                candle_type = candle_analysis.get("current_candle", {}).get("type", "neutral")

            prompt = f"""You are an expert scalp trader specializing in candlestick patterns. Analyze this {interval}-minute chart for {ticker}.

CANDLESTICK PATTERNS DETECTED:
{pattern_str}
Current Candle: {candle_type}
Pattern Bias: {candle_analysis.get('bias', 'neutral') if candle_analysis else 'neutral'}

SUPPORTING INDICATORS:
- Price: ${price:.2f} vs VWAP ${vwap:.2f} ({'above' if price > vwap else 'below'})
- EMA 9/21: {'Bullish cross' if ema9 > ema21 else 'Bearish cross'}
- RSI: {rsi:.1f}

SIGNAL: {signal} (Confidence: {confidence}%)

Provide a 2-3 sentence analysis focusing on:
1. What the candlestick pattern(s) indicate
2. Whether to enter, wait, or avoid
3. Key price level to watch

Be concise. Use <strong> tags for key points. Focus on price action, not indicators."""

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.warning(f"Gemini analysis failed: {e}")
            return self._generate_fallback_analysis(
                signal, confidence, price, ema9, ema21, vwap, rsi, candle_analysis
            )

    def _generate_fallback_analysis(
        self,
        signal: str,
        confidence: int,
        price: float,
        ema9: float,
        ema21: float,
        vwap: float,
        rsi: float,
        candle_analysis: Dict = None,
    ) -> str:
        """Generate fallback analysis without AI"""
        # Build pattern description
        pattern_text = ""
        if candle_analysis and candle_analysis.get("patterns"):
            patterns = candle_analysis["patterns"]
            if patterns:
                pattern_names = [p["name"] for p in patterns[:2]]
                pattern_text = f" Detected patterns: <strong>{', '.join(pattern_names)}</strong>."

        if signal == "LONG":
            return f"""<strong>Bullish Setup:</strong>{pattern_text} Price at ${price:.2f} is {'above' if price > vwap else 'near'} VWAP (${vwap:.2f}). Candlestick structure suggests upward momentum. <strong>Look for long entry</strong> with stop below recent swing low."""
        elif signal == "SHORT":
            return f"""<strong>Bearish Setup:</strong>{pattern_text} Price at ${price:.2f} is {'below' if price < vwap else 'near'} VWAP (${vwap:.2f}). Candlestick structure suggests selling pressure. <strong>Look for short entry</strong> with stop above recent swing high."""
        else:
            bias = candle_analysis.get("bias", "neutral") if candle_analysis else "neutral"
            return f"""<strong>No Clear Setup:</strong>{pattern_text if pattern_text else ' No significant patterns detected.'} Price consolidating around ${price:.2f}. Candle bias is {bias}. <strong>Wait for a clear pattern</strong> before entering."""


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

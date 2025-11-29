"""
Scalp Trading Analysis API
Professional candlestick + volume based scalping signals

Strategy Based on Research:
- Candlestick Patterns: 75% weight (primary driver)
- Volume Confirmation: 15% weight (validation)
- VWAP as S/R Level: 10% weight (institutional reference)

Key Findings Applied:
- Pin Bar at support = 65.2% win rate (IJSRED study)
- Volume decreases during consolidation, spikes before breakout
- Risk/Reward minimum 1:2 or 1:3
- Stop loss at pattern invalidation point
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

api_scalp = Blueprint("api_scalp", __name__)


class CandlestickPatterns:
    """Professional candlestick pattern detection for scalp trading"""

    @staticmethod
    def get_candle_info(bar: Dict) -> Dict:
        """Extract candle components with detailed metrics"""
        o, h, l, c = bar.get("o", 0), bar.get("h", 0), bar.get("l", 0), bar.get("c", 0)
        v = bar.get("v", 0)
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        total_range = h - l if h != l else 0.0001
        is_bullish = c > o
        is_bearish = c < o

        return {
            "open": o, "high": h, "low": l, "close": c,
            "volume": v,
            "body": body,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "range": total_range,
            "body_percent": (body / total_range * 100) if total_range else 0,
            "upper_wick_percent": (upper_wick / total_range * 100) if total_range else 0,
            "lower_wick_percent": (lower_wick / total_range * 100) if total_range else 0,
            "is_bullish": is_bullish,
            "is_bearish": is_bearish,
            "is_doji": body < (total_range * 0.1),
        }

    @staticmethod
    def detect_hammer(candle: Dict) -> Optional[Dict]:
        """
        Hammer: Bullish reversal at support
        - Small body at top (< 35% of range)
        - Long lower wick (> 2x body, > 60% of range)
        - Minimal upper wick (< 10% of range)
        Win Rate: ~65% when at support level
        """
        if candle["body_percent"] > 35:
            return None
        if candle["lower_wick"] < candle["body"] * 2:
            return None
        if candle["lower_wick_percent"] < 60:
            return None
        if candle["upper_wick_percent"] > 10:
            return None

        return {
            "name": "Hammer",
            "type": "bullish",
            "strength": 75,
            "entry_logic": "Enter on close above hammer high",
            "stop_logic": "Stop below hammer low (wick rejection point)",
            "target_logic": "Target 2x risk distance from entry",
            "invalidation": candle["low"],  # Stop goes here
            "confirmation": candle["high"],  # Entry triggers here
        }

    @staticmethod
    def detect_inverted_hammer(candle: Dict) -> Optional[Dict]:
        """
        Inverted Hammer: Potential bullish reversal
        - Small body at bottom
        - Long upper wick showing buyers testing higher
        - Minimal lower wick
        """
        if candle["body_percent"] > 35:
            return None
        if candle["upper_wick"] < candle["body"] * 2:
            return None
        if candle["upper_wick_percent"] < 60:
            return None
        if candle["lower_wick_percent"] > 10:
            return None

        return {
            "name": "Inverted Hammer",
            "type": "bullish",
            "strength": 65,
            "entry_logic": "Enter on break above upper wick",
            "stop_logic": "Stop below candle low",
            "target_logic": "Target 2x risk distance",
            "invalidation": candle["low"],
            "confirmation": candle["high"],
        }

    @staticmethod
    def detect_shooting_star(candle: Dict) -> Optional[Dict]:
        """
        Shooting Star: Bearish reversal at resistance
        - Small body at bottom (< 35% of range)
        - Long upper wick (> 2x body, > 60% of range)
        - Minimal lower wick
        """
        if candle["body_percent"] > 35:
            return None
        if candle["upper_wick"] < candle["body"] * 2:
            return None
        if candle["upper_wick_percent"] < 60:
            return None
        if candle["lower_wick_percent"] > 10:
            return None

        return {
            "name": "Shooting Star",
            "type": "bearish",
            "strength": 75,
            "entry_logic": "Enter on break below shooting star low",
            "stop_logic": "Stop above shooting star high (rejection point)",
            "target_logic": "Target 2x risk distance",
            "invalidation": candle["high"],
            "confirmation": candle["low"],
        }

    @staticmethod
    def detect_engulfing(prev: Dict, curr: Dict) -> Optional[Dict]:
        """
        Engulfing: Strong reversal pattern
        - Current candle completely engulfs previous body
        - Shows strong momentum shift
        Win Rate: ~70% with volume confirmation
        """
        # Bullish Engulfing
        if prev["is_bearish"] and curr["is_bullish"]:
            if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
                if curr["body"] > prev["body"] * 1.2:
                    return {
                        "name": "Bullish Engulfing",
                        "type": "bullish",
                        "strength": 85,
                        "entry_logic": "Enter immediately or on minor pullback",
                        "stop_logic": "Stop below engulfing candle low",
                        "target_logic": "Target 2-3x risk distance",
                        "invalidation": curr["low"],
                        "confirmation": curr["close"],
                    }

        # Bearish Engulfing
        if prev["is_bullish"] and curr["is_bearish"]:
            if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
                if curr["body"] > prev["body"] * 1.2:
                    return {
                        "name": "Bearish Engulfing",
                        "type": "bearish",
                        "strength": 85,
                        "entry_logic": "Enter immediately or on minor bounce",
                        "stop_logic": "Stop above engulfing candle high",
                        "target_logic": "Target 2-3x risk distance",
                        "invalidation": curr["high"],
                        "confirmation": curr["close"],
                    }
        return None

    @staticmethod
    def detect_pin_bar(candle: Dict) -> Optional[Dict]:
        """
        Pin Bar: Strong rejection pattern (highest probability)
        - Body < 30% of range
        - One wick > 60% of range (rejection wick)
        - Other wick minimal
        Win Rate: 65.2% at support/resistance (IJSRED study)
        """
        if candle["body_percent"] > 30:
            return None

        # Bullish Pin Bar (long lower wick = rejection of lower prices)
        if candle["lower_wick_percent"] > 60 and candle["upper_wick_percent"] < 20:
            return {
                "name": "Bullish Pin Bar",
                "type": "bullish",
                "strength": 80,
                "entry_logic": "Enter on break above pin bar high",
                "stop_logic": "Stop below pin bar low (the rejection point)",
                "target_logic": "Target 2x the wick length",
                "invalidation": candle["low"],
                "confirmation": candle["high"],
                "rejection_size": candle["lower_wick"],
            }

        # Bearish Pin Bar (long upper wick = rejection of higher prices)
        if candle["upper_wick_percent"] > 60 and candle["lower_wick_percent"] < 20:
            return {
                "name": "Bearish Pin Bar",
                "type": "bearish",
                "strength": 80,
                "entry_logic": "Enter on break below pin bar low",
                "stop_logic": "Stop above pin bar high (the rejection point)",
                "target_logic": "Target 2x the wick length",
                "invalidation": candle["high"],
                "confirmation": candle["low"],
                "rejection_size": candle["upper_wick"],
            }
        return None

    @staticmethod
    def detect_marubozu(candle: Dict) -> Optional[Dict]:
        """
        Marubozu: Strong momentum candle
        - Body > 85% of range
        - No/tiny wicks showing full control
        """
        if candle["body_percent"] < 85:
            return None
        if candle["upper_wick_percent"] > 7.5 or candle["lower_wick_percent"] > 7.5:
            return None

        if candle["is_bullish"]:
            return {
                "name": "Bullish Marubozu",
                "type": "bullish",
                "strength": 70,
                "entry_logic": "Enter on pullback to 50% of candle",
                "stop_logic": "Stop below marubozu low",
                "target_logic": "Target 1.5-2x candle range",
                "invalidation": candle["low"],
                "confirmation": candle["close"],
            }
        else:
            return {
                "name": "Bearish Marubozu",
                "type": "bearish",
                "strength": 70,
                "entry_logic": "Enter on bounce to 50% of candle",
                "stop_logic": "Stop above marubozu high",
                "target_logic": "Target 1.5-2x candle range",
                "invalidation": candle["high"],
                "confirmation": candle["close"],
            }

    @staticmethod
    def detect_doji(candle: Dict) -> Optional[Dict]:
        """
        Doji: Indecision - wait for confirmation
        - Body < 10% of range
        - Indicates potential reversal if at key level
        """
        if not candle["is_doji"]:
            return None

        # Dragonfly Doji (long lower wick - bullish)
        if candle["lower_wick_percent"] > 60:
            return {
                "name": "Dragonfly Doji",
                "type": "bullish",
                "strength": 60,
                "entry_logic": "Wait for next candle confirmation",
                "stop_logic": "Stop below doji low",
                "target_logic": "Target based on next candle structure",
                "invalidation": candle["low"],
                "confirmation": candle["high"],
            }

        # Gravestone Doji (long upper wick - bearish)
        if candle["upper_wick_percent"] > 60:
            return {
                "name": "Gravestone Doji",
                "type": "bearish",
                "strength": 60,
                "entry_logic": "Wait for next candle confirmation",
                "stop_logic": "Stop above doji high",
                "target_logic": "Target based on next candle structure",
                "invalidation": candle["high"],
                "confirmation": candle["low"],
            }

        # Standard Doji
        return {
            "name": "Doji",
            "type": "neutral",
            "strength": 40,
            "entry_logic": "Wait for direction confirmation",
            "stop_logic": "Based on breakout direction",
            "target_logic": "Based on breakout candle",
            "invalidation": None,
            "confirmation": None,
        }

    @staticmethod
    def detect_inside_bar(prev: Dict, curr: Dict) -> Optional[Dict]:
        """
        Inside Bar: Consolidation before breakout
        - Current candle completely within previous range
        - Trade the breakout direction
        """
        if curr["high"] >= prev["high"] or curr["low"] <= prev["low"]:
            return None

        return {
            "name": "Inside Bar",
            "type": "neutral",
            "strength": 55,
            "entry_logic": "Enter on breakout of mother bar (previous candle)",
            "stop_logic": "Stop on opposite side of mother bar",
            "target_logic": "Target mother bar range projected from breakout",
            "invalidation": prev["low"] if curr["close"] > (prev["high"] + prev["low"]) / 2 else prev["high"],
            "confirmation": prev["high"] if curr["close"] > (prev["high"] + prev["low"]) / 2 else prev["low"],
            "mother_bar_high": prev["high"],
            "mother_bar_low": prev["low"],
        }

    @classmethod
    def analyze_patterns(cls, bars: List[Dict]) -> Dict:
        """Analyze recent candles for actionable patterns"""
        if len(bars) < 3:
            return {"patterns": [], "bias": "neutral", "strength": 0, "primary_pattern": None}

        detected_patterns = []
        bullish_score = 0
        bearish_score = 0

        # Get recent candles
        curr = cls.get_candle_info(bars[-1])
        prev = cls.get_candle_info(bars[-2])
        prev2 = cls.get_candle_info(bars[-3])

        # Check single candle patterns on current candle
        single_patterns = [
            cls.detect_hammer(curr),
            cls.detect_inverted_hammer(curr),
            cls.detect_shooting_star(curr),
            cls.detect_pin_bar(curr),
            cls.detect_marubozu(curr),
            cls.detect_doji(curr),
        ]

        for pattern in single_patterns:
            if pattern:
                detected_patterns.append(pattern)
                if pattern["type"] == "bullish":
                    bullish_score += pattern["strength"]
                elif pattern["type"] == "bearish":
                    bearish_score += pattern["strength"]

        # Check two-candle patterns
        engulfing = cls.detect_engulfing(prev, curr)
        if engulfing:
            detected_patterns.append(engulfing)
            if engulfing["type"] == "bullish":
                bullish_score += engulfing["strength"]
            else:
                bearish_score += engulfing["strength"]

        inside_bar = cls.detect_inside_bar(prev, curr)
        if inside_bar:
            detected_patterns.append(inside_bar)

        # Three-candle pattern: Morning/Evening Star
        if prev["is_doji"] and prev2["is_bearish"] and curr["is_bullish"]:
            if curr["close"] > (prev2["open"] + prev2["close"]) / 2:
                pattern = {
                    "name": "Morning Star",
                    "type": "bullish",
                    "strength": 90,
                    "entry_logic": "Enter on current candle or pullback",
                    "stop_logic": "Stop below the doji low",
                    "target_logic": "Target previous swing high",
                    "invalidation": prev["low"],
                    "confirmation": curr["close"],
                }
                detected_patterns.append(pattern)
                bullish_score += 90

        if prev["is_doji"] and prev2["is_bullish"] and curr["is_bearish"]:
            if curr["close"] < (prev2["open"] + prev2["close"]) / 2:
                pattern = {
                    "name": "Evening Star",
                    "type": "bearish",
                    "strength": 90,
                    "entry_logic": "Enter on current candle or bounce",
                    "stop_logic": "Stop above the doji high",
                    "target_logic": "Target previous swing low",
                    "invalidation": prev["high"],
                    "confirmation": curr["close"],
                }
                detected_patterns.append(pattern)
                bearish_score += 90

        # Sort by strength and get primary pattern
        detected_patterns.sort(key=lambda x: x["strength"], reverse=True)
        primary_pattern = detected_patterns[0] if detected_patterns else None

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
            "patterns": detected_patterns,
            "primary_pattern": primary_pattern,
            "bias": bias,
            "strength": strength,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "current_candle": {
                "type": "bullish" if curr["is_bullish"] else ("bearish" if curr["is_bearish"] else "doji"),
                "body_percent": round(curr["body_percent"], 1),
                "volume": curr["volume"],
            }
        }


class VolumeAnalyzer:
    """Volume analysis for trade confirmation"""

    @staticmethod
    def analyze_volume(bars: List[Dict]) -> Dict:
        """Analyze volume patterns for confirmation signals"""
        if len(bars) < 20:
            return {
                "current_volume": 0,
                "avg_volume": 0,
                "volume_ratio": 1.0,
                "spike_detected": False,
                "volume_trend": "neutral",
                "confirmation_strength": 0,
            }

        volumes = [bar.get("v", 0) for bar in bars]
        current_volume = volumes[-1]
        avg_volume = sum(volumes[-20:]) / 20
        recent_avg = sum(volumes[-5:]) / 5
        older_avg = sum(volumes[-20:-5]) / 15 if len(volumes) >= 20 else avg_volume

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Detect volume spike (key for scalping confirmation)
        spike_detected = volume_ratio >= 1.5
        strong_spike = volume_ratio >= 2.0

        # Volume trend (increasing volume = stronger move)
        if recent_avg > older_avg * 1.2:
            volume_trend = "increasing"
        elif recent_avg < older_avg * 0.8:
            volume_trend = "decreasing"
        else:
            volume_trend = "neutral"

        # Calculate confirmation strength (0-100)
        confirmation_strength = 0
        if spike_detected:
            confirmation_strength = min(100, int(volume_ratio * 30))
        if strong_spike:
            confirmation_strength = min(100, confirmation_strength + 20)
        if volume_trend == "increasing":
            confirmation_strength = min(100, confirmation_strength + 15)

        return {
            "current_volume": current_volume,
            "avg_volume": avg_volume,
            "volume_ratio": round(volume_ratio, 2),
            "spike_detected": spike_detected,
            "strong_spike": strong_spike,
            "volume_trend": volume_trend,
            "confirmation_strength": confirmation_strength,
        }


class SupportResistance:
    """Support and Resistance level detection based on price action"""

    @staticmethod
    def find_swing_points(bars: List[Dict], lookback: int = 5) -> Dict:
        """Find swing highs and lows for S/R levels"""
        if len(bars) < lookback * 2 + 1:
            return {"swing_highs": [], "swing_lows": [], "nearest_support": None, "nearest_resistance": None}

        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(bars) - lookback):
            high = bars[i].get("h", 0)
            low = bars[i].get("l", 0)

            # Check if this is a swing high
            is_swing_high = all(
                high > bars[i - j].get("h", 0) and high > bars[i + j].get("h", 0)
                for j in range(1, lookback + 1)
            )
            if is_swing_high:
                swing_highs.append({
                    "price": high,
                    "index": i,
                    "touches": 1,
                })

            # Check if this is a swing low
            is_swing_low = all(
                low < bars[i - j].get("l", float("inf")) and low < bars[i + j].get("l", float("inf"))
                for j in range(1, lookback + 1)
            )
            if is_swing_low:
                swing_lows.append({
                    "price": low,
                    "index": i,
                    "touches": 1,
                })

        # Cluster nearby levels (within 0.5%)
        swing_highs = SupportResistance._cluster_levels(swing_highs)
        swing_lows = SupportResistance._cluster_levels(swing_lows)

        # Find nearest levels to current price
        current_price = bars[-1].get("c", 0)

        nearest_resistance = None
        for sh in sorted(swing_highs, key=lambda x: x["price"]):
            if sh["price"] > current_price:
                nearest_resistance = sh
                break

        nearest_support = None
        for sl in sorted(swing_lows, key=lambda x: x["price"], reverse=True):
            if sl["price"] < current_price:
                nearest_support = sl
                break

        return {
            "swing_highs": swing_highs[-5:],  # Last 5 resistance levels
            "swing_lows": swing_lows[-5:],    # Last 5 support levels
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }

    @staticmethod
    def _cluster_levels(levels: List[Dict], threshold: float = 0.005) -> List[Dict]:
        """Cluster nearby price levels"""
        if not levels:
            return []

        clustered = []
        levels = sorted(levels, key=lambda x: x["price"])

        current_cluster = [levels[0]]
        for level in levels[1:]:
            if (level["price"] - current_cluster[-1]["price"]) / current_cluster[-1]["price"] < threshold:
                current_cluster.append(level)
            else:
                # Average the cluster
                avg_price = sum(l["price"] for l in current_cluster) / len(current_cluster)
                clustered.append({
                    "price": avg_price,
                    "touches": len(current_cluster),
                    "strength": min(100, len(current_cluster) * 25),
                })
                current_cluster = [level]

        # Don't forget the last cluster
        if current_cluster:
            avg_price = sum(l["price"] for l in current_cluster) / len(current_cluster)
            clustered.append({
                "price": avg_price,
                "touches": len(current_cluster),
                "strength": min(100, len(current_cluster) * 25),
            })

        return clustered


class ScalpAnalyzer:
    """
    Professional Scalp Trading Analyzer

    Signal Weighting:
    - Candlestick Patterns: 75% (primary driver)
    - Volume Confirmation: 15% (validation)
    - VWAP as S/R Level: 10% (institutional reference)

    NO EMA/RSI/MACD in signal calculation (lagging indicators)
    """

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.candle_patterns = CandlestickPatterns()
        self.volume_analyzer = VolumeAnalyzer()
        self.sr_analyzer = SupportResistance()

    def fetch_bars(self, ticker: str, interval: str = "5", limit: int = 100) -> List[Dict]:
        """Fetch candlestick data from Polygon"""
        try:
            timespan_map = {"1": "minute", "5": "minute", "15": "minute"}
            multiplier_map = {"1": 1, "5": 5, "15": 15}

            timespan = timespan_map.get(interval, "minute")
            multiplier = multiplier_map.get(interval, 5)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)

            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {"apiKey": self.polygon_key, "limit": limit, "sort": "desc"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("resultsCount", 0) > 0:
                return list(reversed(data.get("results", [])))
            return []

        except Exception as e:
            logger.error(f"Failed to fetch bars for {ticker}: {e}")
            return []

    def calculate_vwap(self, bars: List[Dict]) -> float:
        """Calculate VWAP (used as institutional S/R level, not indicator)"""
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

    def analyze(self, ticker: str, interval: str = "5") -> Dict:
        """
        Perform candlestick + volume focused scalp analysis

        Returns comprehensive analysis with:
        - Primary candlestick pattern with entry/stop/target logic
        - Volume confirmation
        - Support/Resistance levels
        - Clear reasoning for every recommendation
        """
        try:
            bars = self.fetch_bars(ticker, interval)

            if not bars or len(bars) < 30:
                return {"error": f"Insufficient data for {ticker}. Ensure market is open."}

            closes = [bar.get("c", 0) for bar in bars]
            current_price = closes[-1]
            prev_price = closes[-2] if len(closes) > 1 else current_price

            # Core Analysis (Candlestick + Volume based)
            candle_analysis = CandlestickPatterns.analyze_patterns(bars)
            volume_analysis = VolumeAnalyzer.analyze_volume(bars)
            sr_levels = SupportResistance.find_swing_points(bars)
            vwap = self.calculate_vwap(bars[-50:])

            # Determine signal using candlestick + volume only (NO lagging indicators)
            signal_result = self._determine_signal(
                current_price, vwap, candle_analysis, volume_analysis, sr_levels
            )

            # Calculate entry/stop/target with clear reasoning
            trade_setup = self._calculate_trade_setup(
                current_price, candle_analysis, sr_levels, vwap, signal_result["signal"]
            )

            # Generate analysis with clear reasoning
            analysis = self._generate_analysis(
                ticker, signal_result, candle_analysis, volume_analysis,
                sr_levels, vwap, current_price, interval
            )

            change_percent = ((current_price - prev_price) / prev_price * 100) if prev_price else 0

            return {
                "ticker": ticker,
                "price": current_price,
                "change_percent": round(change_percent, 2),
                "signal": signal_result["signal"],
                "confidence": signal_result["confidence"],
                "signal_reasoning": signal_result["reasoning"],
                "candlestick": {
                    "patterns": candle_analysis["patterns"][:3],  # Top 3 patterns
                    "primary_pattern": candle_analysis["primary_pattern"],
                    "bias": candle_analysis["bias"],
                    "pattern_strength": candle_analysis["strength"],
                },
                "volume": {
                    "ratio": volume_analysis["volume_ratio"],
                    "spike_detected": volume_analysis["spike_detected"],
                    "confirmation_strength": volume_analysis["confirmation_strength"],
                    "trend": volume_analysis["volume_trend"],
                },
                "levels": {
                    "vwap": round(vwap, 2),
                    "nearest_support": sr_levels["nearest_support"]["price"] if sr_levels["nearest_support"] else None,
                    "nearest_resistance": sr_levels["nearest_resistance"]["price"] if sr_levels["nearest_resistance"] else None,
                    "support_strength": sr_levels["nearest_support"]["strength"] if sr_levels["nearest_support"] else 0,
                    "resistance_strength": sr_levels["nearest_resistance"]["strength"] if sr_levels["nearest_resistance"] else 0,
                },
                "trade_setup": trade_setup,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Scalp analysis error for {ticker}: {e}")
            return {"error": str(e)}

    def _determine_signal(
        self,
        price: float,
        vwap: float,
        candle_analysis: Dict,
        volume_analysis: Dict,
        sr_levels: Dict,
    ) -> Dict:
        """
        Determine signal using ONLY candlestick + volume + VWAP level

        Weighting:
        - Candlestick Patterns: 75%
        - Volume Confirmation: 15%
        - VWAP as S/R Level: 10%
        """
        bullish_score = 0
        bearish_score = 0
        reasoning = []

        # === CANDLESTICK PATTERNS: 75% ===
        candle_bias = candle_analysis.get("bias", "neutral")
        candle_strength = candle_analysis.get("strength", 0)
        primary_pattern = candle_analysis.get("primary_pattern")

        if candle_bias == "bullish":
            pattern_score = int(candle_strength * 0.75)
            bullish_score += pattern_score
            if primary_pattern:
                reasoning.append(f"{primary_pattern['name']} detected (+{pattern_score} bullish)")
        elif candle_bias == "bearish":
            pattern_score = int(candle_strength * 0.75)
            bearish_score += pattern_score
            if primary_pattern:
                reasoning.append(f"{primary_pattern['name']} detected (+{pattern_score} bearish)")
        else:
            reasoning.append("No clear candlestick pattern")

        # === VOLUME CONFIRMATION: 15% ===
        volume_strength = volume_analysis.get("confirmation_strength", 0)
        spike_detected = volume_analysis.get("spike_detected", False)

        if spike_detected:
            volume_score = min(15, int(volume_strength * 0.15))
            if bullish_score > bearish_score:
                bullish_score += volume_score
                reasoning.append(f"Volume spike confirms bullish move (+{volume_score})")
            elif bearish_score > bullish_score:
                bearish_score += volume_score
                reasoning.append(f"Volume spike confirms bearish move (+{volume_score})")
        else:
            reasoning.append("No volume confirmation (wait for spike)")

        # === VWAP AS S/R LEVEL: 10% ===
        vwap_distance_percent = abs(price - vwap) / vwap * 100 if vwap > 0 else 0

        # Check if price is at VWAP level (within 0.3%)
        at_vwap = vwap_distance_percent < 0.3

        if price > vwap:
            bullish_score += 10
            if at_vwap:
                reasoning.append("Price bouncing off VWAP support (+10 bullish)")
            else:
                reasoning.append(f"Price above VWAP ${vwap:.2f} (+10 bullish)")
        else:
            bearish_score += 10
            if at_vwap:
                reasoning.append("Price rejected at VWAP resistance (+10 bearish)")
            else:
                reasoning.append(f"Price below VWAP ${vwap:.2f} (+10 bearish)")

        # === SUPPORT/RESISTANCE CONTEXT (bonus) ===
        support = sr_levels.get("nearest_support")
        resistance = sr_levels.get("nearest_resistance")

        if support and abs(price - support["price"]) / price < 0.005:
            if candle_bias == "bullish":
                bullish_score += 10
                reasoning.append(f"Bullish pattern at support ${support['price']:.2f} (+10)")

        if resistance and abs(price - resistance["price"]) / price < 0.005:
            if candle_bias == "bearish":
                bearish_score += 10
                reasoning.append(f"Bearish pattern at resistance ${resistance['price']:.2f} (+10)")

        # === DETERMINE SIGNAL ===
        # Require minimum 60 points AND a clear candlestick pattern
        has_pattern = primary_pattern is not None and primary_pattern.get("strength", 0) >= 60

        if bullish_score >= 60 and has_pattern and candle_bias == "bullish":
            signal = "LONG"
            confidence = min(95, bullish_score)
        elif bearish_score >= 60 and has_pattern and candle_bias == "bearish":
            signal = "SHORT"
            confidence = min(95, bearish_score)
        else:
            signal = "WAIT"
            confidence = max(bullish_score, bearish_score)
            if not has_pattern:
                reasoning.append("No strong pattern - wait for setup")

        return {
            "signal": signal,
            "confidence": confidence,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "reasoning": reasoning,
        }

    def _calculate_trade_setup(
        self,
        current_price: float,
        candle_analysis: Dict,
        sr_levels: Dict,
        vwap: float,
        signal: str,
    ) -> Dict:
        """Calculate entry/stop/target with clear reasoning based on candlestick structure"""

        primary_pattern = candle_analysis.get("primary_pattern")
        support = sr_levels.get("nearest_support")
        resistance = sr_levels.get("nearest_resistance")

        if signal == "LONG" and primary_pattern:
            # Entry: Pattern confirmation price or current price
            entry = primary_pattern.get("confirmation", current_price)

            # Stop Loss: Pattern invalidation point (below the rejection wick)
            invalidation = primary_pattern.get("invalidation", current_price * 0.995)
            stop_loss = invalidation * 0.998  # Slight buffer below invalidation

            # Risk calculation
            risk = entry - stop_loss

            # Target: 2:1 Risk/Reward minimum
            take_profit = entry + (risk * 2)

            # If we have resistance, use it as target if closer
            if resistance and resistance["price"] < take_profit:
                take_profit = resistance["price"]
                rr_ratio = (take_profit - entry) / risk if risk > 0 else 2
            else:
                rr_ratio = 2.0

            return {
                "entry_price": round(entry, 4),
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "risk_reward": f"1:{rr_ratio:.1f}",
                "entry_reasoning": primary_pattern.get("entry_logic", "Enter on pattern confirmation"),
                "stop_reasoning": primary_pattern.get("stop_logic", "Stop below pattern low"),
                "target_reasoning": primary_pattern.get("target_logic", "Target 2x risk"),
                "invalidation_price": round(invalidation, 4),
            }

        elif signal == "SHORT" and primary_pattern:
            entry = primary_pattern.get("confirmation", current_price)
            invalidation = primary_pattern.get("invalidation", current_price * 1.005)
            stop_loss = invalidation * 1.002

            risk = stop_loss - entry
            take_profit = entry - (risk * 2)

            if support and support["price"] > take_profit:
                take_profit = support["price"]
                rr_ratio = (entry - take_profit) / risk if risk > 0 else 2
            else:
                rr_ratio = 2.0

            return {
                "entry_price": round(entry, 4),
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "risk_reward": f"1:{rr_ratio:.1f}",
                "entry_reasoning": primary_pattern.get("entry_logic", "Enter on pattern confirmation"),
                "stop_reasoning": primary_pattern.get("stop_logic", "Stop above pattern high"),
                "target_reasoning": primary_pattern.get("target_logic", "Target 2x risk"),
                "invalidation_price": round(invalidation, 4),
            }

        else:
            # No trade - waiting for setup
            return {
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "risk_reward": "N/A",
                "entry_reasoning": "Wait for clear candlestick pattern with volume confirmation",
                "stop_reasoning": "N/A",
                "target_reasoning": "N/A",
                "invalidation_price": None,
            }

    def _generate_analysis(
        self,
        ticker: str,
        signal_result: Dict,
        candle_analysis: Dict,
        volume_analysis: Dict,
        sr_levels: Dict,
        vwap: float,
        current_price: float,
        interval: str,
    ) -> str:
        """Generate analysis with AI or fallback"""
        try:
            import google.generativeai as genai

            if not self.gemini_key:
                return self._generate_fallback_analysis(
                    signal_result, candle_analysis, volume_analysis, sr_levels, vwap, current_price
                )

            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            primary = candle_analysis.get("primary_pattern")
            pattern_info = f"{primary['name']} (Strength: {primary['strength']})" if primary else "None"

            prompt = f"""You are a professional scalp trader. Analyze this setup for {ticker} on {interval}-minute chart.

CANDLESTICK PATTERN:
- Primary Pattern: {pattern_info}
- Pattern Bias: {candle_analysis.get('bias', 'neutral')}
- Entry Logic: {primary.get('entry_logic', 'N/A') if primary else 'N/A'}
- Stop Logic: {primary.get('stop_logic', 'N/A') if primary else 'N/A'}

VOLUME:
- Volume Ratio: {volume_analysis['volume_ratio']}x average
- Spike Detected: {'Yes' if volume_analysis['spike_detected'] else 'No'}
- Volume Trend: {volume_analysis['volume_trend']}

PRICE LEVELS:
- Current Price: ${current_price:.2f}
- VWAP: ${vwap:.2f}
- Nearest Support: ${sr_levels['nearest_support']['price']:.2f if sr_levels.get('nearest_support') else 'N/A'}
- Nearest Resistance: ${sr_levels['nearest_resistance']['price']:.2f if sr_levels.get('nearest_resistance') else 'N/A'}

SIGNAL: {signal_result['signal']} (Confidence: {signal_result['confidence']}%)

Provide a 2-3 sentence analysis:
1. What the candlestick pattern tells us
2. Whether volume confirms the move
3. The key price level to watch

Be direct. Use <strong> tags for key points. Focus ONLY on candlesticks and volume."""

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.warning(f"Gemini analysis failed: {e}")
            return self._generate_fallback_analysis(
                signal_result, candle_analysis, volume_analysis, sr_levels, vwap, current_price
            )

    def _generate_fallback_analysis(
        self,
        signal_result: Dict,
        candle_analysis: Dict,
        volume_analysis: Dict,
        sr_levels: Dict,
        vwap: float,
        current_price: float,
    ) -> str:
        """Generate analysis without AI"""
        signal = signal_result["signal"]
        primary = candle_analysis.get("primary_pattern")
        volume_confirmed = volume_analysis.get("spike_detected", False)

        if signal == "LONG" and primary:
            vol_text = "with volume confirmation" if volume_confirmed else "waiting for volume spike"
            return f"""<strong>{primary['name']} detected</strong> - bullish reversal pattern {vol_text}.
            {primary.get('entry_logic', 'Enter on confirmation')}.
            <strong>Stop below ${primary.get('invalidation', current_price * 0.995):.2f}</strong> (pattern invalidation).
            Target 2:1 reward at VWAP ${vwap:.2f} or next resistance."""

        elif signal == "SHORT" and primary:
            vol_text = "with volume confirmation" if volume_confirmed else "waiting for volume spike"
            return f"""<strong>{primary['name']} detected</strong> - bearish reversal pattern {vol_text}.
            {primary.get('entry_logic', 'Enter on confirmation')}.
            <strong>Stop above ${primary.get('invalidation', current_price * 1.005):.2f}</strong> (pattern invalidation).
            Target 2:1 reward at support or VWAP ${vwap:.2f}."""

        else:
            support = sr_levels.get("nearest_support")
            resistance = sr_levels.get("nearest_resistance")
            support_text = f"${support['price']:.2f}" if support else "N/A"
            resistance_text = f"${resistance['price']:.2f}" if resistance else "N/A"

            return f"""<strong>No actionable pattern</strong> - wait for clear candlestick setup with volume spike.
            Current price ${current_price:.2f}, VWAP ${vwap:.2f}.
            Watch for patterns at <strong>support {support_text}</strong> or <strong>resistance {resistance_text}</strong>.
            Volume currently {volume_analysis['volume_ratio']:.1f}x average."""


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

    return jsonify({
        "ticker": result.get("ticker"),
        "price": result.get("price"),
        "signal": result.get("signal"),
        "confidence": result.get("confidence"),
        "primary_pattern": result.get("candlestick", {}).get("primary_pattern", {}).get("name") if result.get("candlestick", {}).get("primary_pattern") else None,
        "message": "Login for full analysis with entry/exit levels and reasoning",
    })

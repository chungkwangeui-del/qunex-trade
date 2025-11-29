"""
Scalp Trading Analysis API
Professional candlestick + volume based scalping signals

Strategy Based on Research + Korean Trader "쉽알" Methods:
- Order Blocks: Engulfing patterns create S/R zones
- FVG (Fair Value Gap): Price gaps that tend to get filled
- Confluence Scoring: Minimum 2 reasons required for entry
- Fakeout/Trap Detection: False breakouts for counter-trend entries
- Volume Spike = Exit Signal (not just confirmation)

Key Principles (7 Video Analysis):
1. Order Block = 장악형 캔들 (Engulfing) creates S/R
2. Double Engulfing (이중 장악형) = VERY STRONG signal
3. FVG = 캔들 사이 갭, price returns to fill
4. Multi-timeframe Confluence = Higher weight
5. Fakeout at channel = Entry opportunity
6. Volume spike = Consider taking profits
7. Minimum 2 confluences required for entry

Supported Markets:
- US Stocks via Polygon.io API
- Crypto via Binance API (BTCUSDT, ETHUSDT, etc.)
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import re

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

        # Standard Doji - indicates indecision, potential reversal
        return {
            "name": "Doji",
            "type": "neutral",
            "strength": 50,
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


class FVGAnalyzer:
    """
    Fair Value Gap (FVG) Detection - 쉽알 Strategy

    FVG = Gap between candles where wicks don't overlap
    - Upward FVG (created during rise) = Support zone when price returns
    - Downward FVG (created during drop) = Resistance zone when price returns

    Key: Price tends to return and fill these gaps
    """

    @staticmethod
    def detect_fvg(bars: List[Dict], min_gap_percent: float = 0.1) -> Dict:
        """
        Detect Fair Value Gaps in price action

        FVG occurs when:
        - 3 consecutive candles
        - Middle candle creates gap where candle 1 high < candle 3 low (bullish FVG)
        - Or candle 1 low > candle 3 high (bearish FVG)
        """
        if len(bars) < 10:
            return {"bullish_fvgs": [], "bearish_fvgs": [], "nearest_fvg": None}

        bullish_fvgs = []  # Support zones (gaps during rise)
        bearish_fvgs = []  # Resistance zones (gaps during drop)

        current_price = bars[-1].get("c", 0)

        for i in range(2, len(bars)):
            candle1 = bars[i - 2]
            candle2 = bars[i - 1]  # Middle candle (the big move)
            candle3 = bars[i]

            c1_high = candle1.get("h", 0)
            c1_low = candle1.get("l", 0)
            c3_high = candle3.get("h", 0)
            c3_low = candle3.get("l", 0)

            # Bullish FVG: Gap below (candle 1 high < candle 3 low)
            # This creates a support zone
            if c1_high < c3_low:
                gap_size = c3_low - c1_high
                gap_percent = (gap_size / c1_high * 100) if c1_high > 0 else 0

                if gap_percent >= min_gap_percent:
                    fvg = {
                        "type": "bullish",
                        "top": c3_low,
                        "bottom": c1_high,
                        "size": gap_size,
                        "size_percent": round(gap_percent, 2),
                        "index": i,
                        "filled": current_price <= c3_low,  # FVG filled if price came back
                        "strength": min(100, int(gap_percent * 20)),
                    }
                    bullish_fvgs.append(fvg)

            # Bearish FVG: Gap above (candle 1 low > candle 3 high)
            # This creates a resistance zone
            if c1_low > c3_high:
                gap_size = c1_low - c3_high
                gap_percent = (gap_size / c3_high * 100) if c3_high > 0 else 0

                if gap_percent >= min_gap_percent:
                    fvg = {
                        "type": "bearish",
                        "top": c1_low,
                        "bottom": c3_high,
                        "size": gap_size,
                        "size_percent": round(gap_percent, 2),
                        "index": i,
                        "filled": current_price >= c3_high,
                        "strength": min(100, int(gap_percent * 20)),
                    }
                    bearish_fvgs.append(fvg)

        # Find nearest unfilled FVG to current price
        nearest_fvg = None
        min_distance = float("inf")

        for fvg in bullish_fvgs + bearish_fvgs:
            if fvg["filled"]:
                continue

            # Calculate distance to FVG zone
            if fvg["type"] == "bullish":
                distance = current_price - fvg["top"]
                if 0 < distance < min_distance:
                    min_distance = distance
                    nearest_fvg = fvg
            else:  # bearish
                distance = fvg["bottom"] - current_price
                if 0 < distance < min_distance:
                    min_distance = distance
                    nearest_fvg = fvg

        # Check if price is currently IN an FVG zone
        at_fvg = None
        for fvg in bullish_fvgs + bearish_fvgs:
            if fvg["bottom"] <= current_price <= fvg["top"]:
                at_fvg = fvg
                break

        return {
            "bullish_fvgs": bullish_fvgs[-5:],  # Last 5 bullish FVGs
            "bearish_fvgs": bearish_fvgs[-5:],  # Last 5 bearish FVGs
            "nearest_fvg": nearest_fvg,
            "at_fvg": at_fvg,
            "total_bullish": len(bullish_fvgs),
            "total_bearish": len(bearish_fvgs),
        }


class OrderBlockAnalyzer:
    """
    Order Block Detection - 쉽알 Strategy (Enhanced)

    Order Block = Engulfing candle pattern
    - Bullish Order Block: Bearish candle engulfed by bullish = Support
    - Bearish Order Block: Bullish candle engulfed by bearish = Resistance

    Double Engulfing (이중 장악형) = MUCH STRONGER signal
    - Pattern: A engulfs B, then C engulfs A
    - The middle candle's body becomes the key S/R zone
    """

    @staticmethod
    def detect_order_blocks(bars: List[Dict]) -> Dict:
        """Detect Order Blocks (engulfing patterns) as S/R zones"""
        if len(bars) < 5:
            return {"bullish_obs": [], "bearish_obs": [], "double_ob": None}

        bullish_obs = []  # Support zones
        bearish_obs = []  # Resistance zones
        double_ob = None  # Double engulfing (strongest)

        current_price = bars[-1].get("c", 0)

        for i in range(1, len(bars)):
            prev = bars[i - 1]
            curr = bars[i]

            prev_open = prev.get("o", 0)
            prev_close = prev.get("c", 0)
            prev_body_top = max(prev_open, prev_close)
            prev_body_bottom = min(prev_open, prev_close)

            curr_open = curr.get("o", 0)
            curr_close = curr.get("c", 0)
            curr_body_top = max(curr_open, curr_close)
            curr_body_bottom = min(curr_open, curr_close)

            prev_is_bullish = prev_close > prev_open
            curr_is_bullish = curr_close > curr_open

            # Bullish Order Block (상승 장악형)
            # Previous bearish candle engulfed by current bullish candle
            if not prev_is_bullish and curr_is_bullish:
                if curr_body_bottom <= prev_body_bottom and curr_body_top >= prev_body_top:
                    ob = {
                        "type": "bullish",
                        "zone_top": prev_body_top,
                        "zone_bottom": prev_body_bottom,
                        "index": i,
                        "strength": 70,
                        "is_double": False,
                    }
                    bullish_obs.append(ob)

            # Bearish Order Block (하락 장악형)
            # Previous bullish candle engulfed by current bearish candle
            if prev_is_bullish and not curr_is_bullish:
                if curr_body_bottom <= prev_body_bottom and curr_body_top >= prev_body_top:
                    ob = {
                        "type": "bearish",
                        "zone_top": prev_body_top,
                        "zone_bottom": prev_body_bottom,
                        "index": i,
                        "strength": 70,
                        "is_double": False,
                    }
                    bearish_obs.append(ob)

        # Detect Double Engulfing (이중 장악형) - VERY STRONG
        # Pattern: A engulfs B, then C engulfs A
        for i in range(2, len(bars)):
            c1 = bars[i - 2]
            c2 = bars[i - 1]
            c3 = bars[i]

            c1_body_top = max(c1.get("o", 0), c1.get("c", 0))
            c1_body_bottom = min(c1.get("o", 0), c1.get("c", 0))
            c2_body_top = max(c2.get("o", 0), c2.get("c", 0))
            c2_body_bottom = min(c2.get("o", 0), c2.get("c", 0))
            c3_body_top = max(c3.get("o", 0), c3.get("c", 0))
            c3_body_bottom = min(c3.get("o", 0), c3.get("c", 0))

            c1_is_bullish = c1.get("c", 0) > c1.get("o", 0)
            c2_is_bullish = c2.get("c", 0) > c2.get("o", 0)
            c3_is_bullish = c3.get("c", 0) > c3.get("o", 0)

            # Bullish Double Engulfing: Bearish engulfs bullish, then bullish engulfs that bearish
            # Result: Strong support at the middle candle's body
            if c1_is_bullish and not c2_is_bullish and c3_is_bullish:
                # Check c2 engulfs c1
                c2_engulfs_c1 = c2_body_bottom <= c1_body_bottom and c2_body_top >= c1_body_top
                # Check c3 engulfs c2
                c3_engulfs_c2 = c3_body_bottom <= c2_body_bottom and c3_body_top >= c2_body_top

                if c2_engulfs_c1 and c3_engulfs_c2:
                    double_ob = {
                        "type": "bullish",
                        "zone_top": c2_body_top,
                        "zone_bottom": c2_body_bottom,
                        "index": i,
                        "strength": 95,  # Very strong!
                        "is_double": True,
                        "description": "이중 장악형 - Very Strong Support",
                    }

            # Bearish Double Engulfing
            if not c1_is_bullish and c2_is_bullish and not c3_is_bullish:
                c2_engulfs_c1 = c2_body_bottom <= c1_body_bottom and c2_body_top >= c1_body_top
                c3_engulfs_c2 = c3_body_bottom <= c2_body_bottom and c3_body_top >= c2_body_top

                if c2_engulfs_c1 and c3_engulfs_c2:
                    double_ob = {
                        "type": "bearish",
                        "zone_top": c2_body_top,
                        "zone_bottom": c2_body_bottom,
                        "index": i,
                        "strength": 95,
                        "is_double": True,
                        "description": "이중 장악형 - Very Strong Resistance",
                    }

        # Find nearest Order Block to current price
        nearest_support_ob = None
        nearest_resistance_ob = None

        for ob in bullish_obs:
            if ob["zone_top"] < current_price:
                if nearest_support_ob is None or ob["zone_top"] > nearest_support_ob["zone_top"]:
                    nearest_support_ob = ob

        for ob in bearish_obs:
            if ob["zone_bottom"] > current_price:
                if nearest_resistance_ob is None or ob["zone_bottom"] < nearest_resistance_ob["zone_bottom"]:
                    nearest_resistance_ob = ob

        # Check if price is at an Order Block
        at_ob = None
        for ob in bullish_obs + bearish_obs:
            if ob["zone_bottom"] <= current_price <= ob["zone_top"]:
                at_ob = ob
                break

        return {
            "bullish_obs": bullish_obs[-5:],
            "bearish_obs": bearish_obs[-5:],
            "double_ob": double_ob,
            "nearest_support_ob": nearest_support_ob,
            "nearest_resistance_ob": nearest_resistance_ob,
            "at_ob": at_ob,
        }


class FakeoutDetector:
    """
    Fakeout & Trap Detection - 쉽알 Strategy

    Fakeout = Single bottom false breakout
    Trap = Double bottom false breakout

    When price breaks a key level but quickly reverses back:
    - The false breakout low/high becomes a clear stop loss point
    - Entry when price re-enters the structure
    """

    @staticmethod
    def detect_fakeout(bars: List[Dict], sr_levels: Dict) -> Dict:
        """Detect potential fakeout/trap patterns"""
        if len(bars) < 10:
            return {"fakeout": None, "trap": None}

        current_price = bars[-1].get("c", 0)
        support = sr_levels.get("nearest_support")
        resistance = sr_levels.get("nearest_resistance")

        fakeout = None
        trap = None

        # Look for fakeout at support (bullish opportunity)
        if support:
            support_price = support.get("price", 0)

            # Check last 10 bars for a break below support that reversed
            broke_support = False
            lowest_break = None
            break_index = None

            for i in range(-10, 0):
                if i >= -len(bars):
                    bar = bars[i]
                    bar_low = bar.get("l", 0)
                    bar_close = bar.get("c", 0)

                    # Check if bar broke below support
                    if bar_low < support_price * 0.998:  # 0.2% buffer
                        broke_support = True
                        if lowest_break is None or bar_low < lowest_break:
                            lowest_break = bar_low
                            break_index = i

            # If we broke support but current price is back above it = Fakeout!
            if broke_support and current_price > support_price:
                fakeout = {
                    "type": "bullish",
                    "description": "Fakeout below support - Bullish opportunity",
                    "false_break_low": lowest_break,
                    "support_level": support_price,
                    "stop_loss": lowest_break * 0.998,  # Stop below the fakeout low
                    "strength": 80,
                    "entry_logic": "Enter LONG, stop below fakeout low",
                }

        # Look for fakeout at resistance (bearish opportunity)
        if resistance:
            resistance_price = resistance.get("price", 0)

            broke_resistance = False
            highest_break = None

            for i in range(-10, 0):
                if i >= -len(bars):
                    bar = bars[i]
                    bar_high = bar.get("h", 0)
                    bar_close = bar.get("c", 0)

                    if bar_high > resistance_price * 1.002:
                        broke_resistance = True
                        if highest_break is None or bar_high > highest_break:
                            highest_break = bar_high

            if broke_resistance and current_price < resistance_price:
                fakeout = {
                    "type": "bearish",
                    "description": "Fakeout above resistance - Bearish opportunity",
                    "false_break_high": highest_break,
                    "resistance_level": resistance_price,
                    "stop_loss": highest_break * 1.002,
                    "strength": 80,
                    "entry_logic": "Enter SHORT, stop above fakeout high",
                }

        # Detect Trap (Double bottom/top fakeout) - Even stronger
        # Look for W or M pattern at support/resistance
        if len(bars) >= 20 and support:
            support_price = support.get("price", 0)
            lows = [bar.get("l", 0) for bar in bars[-20:]]

            # Find two lows near each other below support
            low_points = []
            for i, low in enumerate(lows):
                if low < support_price * 1.005:  # Within 0.5% of support
                    low_points.append((i, low))

            # Check for double bottom (trap)
            if len(low_points) >= 2:
                # Two lows with some distance between them
                first_low = low_points[0]
                for second_low in low_points[1:]:
                    if abs(second_low[0] - first_low[0]) >= 3:  # At least 3 bars apart
                        if abs(second_low[1] - first_low[1]) / support_price < 0.01:  # Similar levels
                            if current_price > support_price:
                                trap = {
                                    "type": "bullish",
                                    "description": "Double Bottom Trap - Strong bullish signal",
                                    "first_low": first_low[1],
                                    "second_low": second_low[1],
                                    "stop_loss": min(first_low[1], second_low[1]) * 0.998,
                                    "strength": 90,
                                    "entry_logic": "Enter LONG on break above neckline",
                                }
                                break

        return {
            "fakeout": fakeout,
            "trap": trap,
        }


class ConfluenceScorer:
    """
    Confluence Scoring System - 쉽알 Strategy

    Key Rule: Minimum 2 confluences required for entry

    Confluences:
    1. Order Block at level
    2. FVG at level
    3. Support/Resistance
    4. Trendline (not implemented in this version)
    5. Candlestick pattern
    6. Volume confirmation
    7. Fakeout/Trap pattern
    """

    @staticmethod
    def calculate_confluence(
        candle_analysis: Dict,
        volume_analysis: Dict,
        fvg_analysis: Dict,
        ob_analysis: Dict,
        fakeout_analysis: Dict,
        sr_levels: Dict,
        current_price: float,
    ) -> Dict:
        """Calculate total confluence score and count reasons"""

        bullish_reasons = []
        bearish_reasons = []

        # 1. Candlestick Pattern
        primary_pattern = candle_analysis.get("primary_pattern")
        if primary_pattern:
            if primary_pattern.get("type") == "bullish":
                bullish_reasons.append({
                    "reason": f"Candlestick: {primary_pattern['name']}",
                    "strength": primary_pattern.get("strength", 50),
                })
            elif primary_pattern.get("type") == "bearish":
                bearish_reasons.append({
                    "reason": f"Candlestick: {primary_pattern['name']}",
                    "strength": primary_pattern.get("strength", 50),
                })

        # 2. Volume Confirmation
        if volume_analysis.get("spike_detected"):
            reason = {
                "reason": f"Volume spike {volume_analysis.get('volume_ratio', 1):.1f}x",
                "strength": volume_analysis.get("confirmation_strength", 50),
            }
            # Volume confirms the direction with more score
            if len(bullish_reasons) > len(bearish_reasons):
                bullish_reasons.append(reason)
            elif len(bearish_reasons) > len(bullish_reasons):
                bearish_reasons.append(reason)

        # 3. At FVG Zone
        at_fvg = fvg_analysis.get("at_fvg")
        if at_fvg:
            if at_fvg["type"] == "bullish":
                bullish_reasons.append({
                    "reason": f"At Bullish FVG zone (${at_fvg['bottom']:.2f}-${at_fvg['top']:.2f})",
                    "strength": at_fvg.get("strength", 60),
                })
            else:
                bearish_reasons.append({
                    "reason": f"At Bearish FVG zone (${at_fvg['bottom']:.2f}-${at_fvg['top']:.2f})",
                    "strength": at_fvg.get("strength", 60),
                })

        # 4. At Order Block
        at_ob = ob_analysis.get("at_ob")
        if at_ob:
            strength = 95 if at_ob.get("is_double") else 70
            if at_ob["type"] == "bullish":
                bullish_reasons.append({
                    "reason": f"At Bullish Order Block" + (" (이중 장악형!)" if at_ob.get("is_double") else ""),
                    "strength": strength,
                })
            else:
                bearish_reasons.append({
                    "reason": f"At Bearish Order Block" + (" (이중 장악형!)" if at_ob.get("is_double") else ""),
                    "strength": strength,
                })

        # 5. Double Order Block (이중 장악형) - Very strong!
        double_ob = ob_analysis.get("double_ob")
        if double_ob:
            if double_ob["type"] == "bullish" and double_ob["zone_top"] >= current_price:
                bullish_reasons.append({
                    "reason": "이중 장악형 Order Block - VERY STRONG",
                    "strength": 95,
                })
            elif double_ob["type"] == "bearish" and double_ob["zone_bottom"] <= current_price:
                bearish_reasons.append({
                    "reason": "이중 장악형 Order Block - VERY STRONG",
                    "strength": 95,
                })

        # 6. Fakeout/Trap
        fakeout = fakeout_analysis.get("fakeout")
        trap = fakeout_analysis.get("trap")

        if trap:
            if trap["type"] == "bullish":
                bullish_reasons.append({
                    "reason": "Double Bottom Trap detected",
                    "strength": trap.get("strength", 90),
                })
            else:
                bearish_reasons.append({
                    "reason": "Double Top Trap detected",
                    "strength": trap.get("strength", 90),
                })
        elif fakeout:
            if fakeout["type"] == "bullish":
                bullish_reasons.append({
                    "reason": "Fakeout below support",
                    "strength": fakeout.get("strength", 80),
                })
            else:
                bearish_reasons.append({
                    "reason": "Fakeout above resistance",
                    "strength": fakeout.get("strength", 80),
                })

        # 7. Near Support/Resistance with pattern
        support = sr_levels.get("nearest_support")
        resistance = sr_levels.get("nearest_resistance")

        if support and abs(current_price - support["price"]) / current_price < 0.01:
            if candle_analysis.get("bias") == "bullish":
                bullish_reasons.append({
                    "reason": f"Bullish pattern at support ${support['price']:.2f}",
                    "strength": 65,
                })

        if resistance and abs(current_price - resistance["price"]) / current_price < 0.01:
            if candle_analysis.get("bias") == "bearish":
                bearish_reasons.append({
                    "reason": f"Bearish pattern at resistance ${resistance['price']:.2f}",
                    "strength": 65,
                })

        # Calculate total scores
        bullish_score = sum(r["strength"] for r in bullish_reasons)
        bearish_score = sum(r["strength"] for r in bearish_reasons)

        # Determine direction
        if len(bullish_reasons) >= 2 and bullish_score > bearish_score:
            direction = "bullish"
            confidence = min(95, bullish_score)
            reasons = bullish_reasons
        elif len(bearish_reasons) >= 2 and bearish_score > bullish_score:
            direction = "bearish"
            confidence = min(95, bearish_score)
            reasons = bearish_reasons
        else:
            direction = "neutral"
            confidence = max(bullish_score, bearish_score) if bullish_reasons or bearish_reasons else 0
            reasons = bullish_reasons + bearish_reasons

        # Check minimum 2 confluences rule
        has_enough_confluence = (
            (direction == "bullish" and len(bullish_reasons) >= 2) or
            (direction == "bearish" and len(bearish_reasons) >= 2)
        )

        return {
            "direction": direction,
            "bullish_reasons": bullish_reasons,
            "bearish_reasons": bearish_reasons,
            "bullish_count": len(bullish_reasons),
            "bearish_count": len(bearish_reasons),
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "confidence": confidence,
            "has_enough_confluence": has_enough_confluence,
            "min_confluence_met": has_enough_confluence,
            "total_reasons": len(bullish_reasons) + len(bearish_reasons),
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

    Supported Markets:
    - US Stocks via Polygon.io
    - Crypto via Binance (no API key required for public data)
    """

    # Common crypto trading pairs
    CRYPTO_PATTERNS = [
        r"^[A-Z]+USDT$",  # BTCUSDT, ETHUSDT, etc.
        r"^[A-Z]+BUSD$",  # BTCBUSD, ETHBUSD, etc.
        r"^[A-Z]+BTC$",   # ETHBTC, ADABTC, etc.
        r"^[A-Z]+ETH$",   # ADAETH, etc.
        r"^[A-Z]+BNB$",   # ADABNB, etc.
    ]

    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.candle_patterns = CandlestickPatterns()
        self.volume_analyzer = VolumeAnalyzer()
        self.sr_analyzer = SupportResistance()
        # New analyzers based on 쉽알 strategy
        self.fvg_analyzer = FVGAnalyzer()
        self.ob_analyzer = OrderBlockAnalyzer()
        self.fakeout_detector = FakeoutDetector()
        self.confluence_scorer = ConfluenceScorer()

    def is_crypto(self, ticker: str) -> bool:
        """
        Detect if ticker is a crypto pair (BTCUSDT, ETHUSDT, etc.)

        Returns True for crypto pairs, False for stocks
        """
        ticker = ticker.upper().strip()
        for pattern in self.CRYPTO_PATTERNS:
            if re.match(pattern, ticker):
                return True
        return False

    def fetch_bars_binance(self, symbol: str, interval: str = "5", limit: int = 100) -> List[Dict]:
        """
        Fetch candlestick data from Binance API

        Uses Binance.US for US users, falls back to Binance.com
        Binance interval format: 1m, 5m, 15m, 1h, 4h, 1d
        No API key required for public market data
        """
        # Map our interval format to Binance format
        interval_map = {"1": "1m", "5": "5m", "15": "15m", "60": "1h", "240": "4h"}
        binance_interval = interval_map.get(interval, "5m")

        # Try Binance.US first (for US users), then fall back to Binance.com
        endpoints = [
            "https://api.binance.us/api/v3/klines",
            "https://api.binance.com/api/v3/klines",
        ]

        for url in endpoints:
            try:
                params = {
                    "symbol": symbol.upper(),
                    "interval": binance_interval,
                    "limit": limit,
                }

                response = requests.get(url, params=params, timeout=10)

                # Skip to next endpoint if geo-restricted (451)
                if response.status_code == 451:
                    logger.warning(f"Binance endpoint geo-restricted: {url}")
                    continue

                response.raise_for_status()
                data = response.json()

                # Validate response is a list (klines data)
                if not isinstance(data, list):
                    logger.warning(f"Unexpected Binance response format: {data}")
                    continue

                # Convert Binance format to our standard format
                # Binance returns: [open_time, open, high, low, close, volume, ...]
                bars = []
                for kline in data:
                    bars.append({
                        "t": kline[0],  # Open time (timestamp)
                        "o": float(kline[1]),  # Open
                        "h": float(kline[2]),  # High
                        "l": float(kline[3]),  # Low
                        "c": float(kline[4]),  # Close
                        "v": float(kline[5]),  # Volume
                    })

                logger.info(f"Successfully fetched {len(bars)} bars from {url}")
                return bars

            except Exception as e:
                logger.warning(f"Failed to fetch from {url}: {e}")
                continue

        logger.error(f"All Binance endpoints failed for {symbol}")
        return []

    def fetch_bars_polygon(self, ticker: str, interval: str = "5", limit: int = 100) -> List[Dict]:
        """Fetch candlestick data from Polygon (for US stocks)"""
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
            logger.error(f"Failed to fetch Polygon bars for {ticker}: {e}")
            return []

    def fetch_bars(self, ticker: str, interval: str = "5", limit: int = 100) -> List[Dict]:
        """
        Fetch candlestick data - automatically routes to correct API

        - Crypto pairs (BTCUSDT, etc.) -> Binance API
        - US Stocks -> Polygon API
        """
        ticker = ticker.upper().strip()

        if self.is_crypto(ticker):
            logger.info(f"Fetching {ticker} from Binance (crypto detected)")
            return self.fetch_bars_binance(ticker, interval, limit)
        else:
            logger.info(f"Fetching {ticker} from Polygon (stock)")
            return self.fetch_bars_polygon(ticker, interval, limit)

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

        Supports both stocks (via Polygon) and crypto (via Binance)
        """
        try:
            ticker = ticker.upper().strip()
            is_crypto = self.is_crypto(ticker)
            bars = self.fetch_bars(ticker, interval)

            if not bars or len(bars) < 30:
                market_type = "crypto" if is_crypto else "stock"
                return {"error": f"Insufficient data for {ticker}. Ensure {market_type} market is open."}

            closes = [bar.get("c", 0) for bar in bars]
            current_price = closes[-1]
            prev_price = closes[-2] if len(closes) > 1 else current_price

            # Core Analysis (Candlestick + Volume based)
            candle_analysis = CandlestickPatterns.analyze_patterns(bars)
            volume_analysis = VolumeAnalyzer.analyze_volume(bars)
            sr_levels = SupportResistance.find_swing_points(bars)
            vwap = self.calculate_vwap(bars[-50:])

            # NEW: Advanced Analysis (쉽알 Strategy)
            fvg_analysis = FVGAnalyzer.detect_fvg(bars)
            ob_analysis = OrderBlockAnalyzer.detect_order_blocks(bars)
            fakeout_analysis = FakeoutDetector.detect_fakeout(bars, sr_levels)

            # NEW: Confluence Scoring (최소 2개 근거 필요)
            confluence = ConfluenceScorer.calculate_confluence(
                candle_analysis, volume_analysis, fvg_analysis,
                ob_analysis, fakeout_analysis, sr_levels, current_price
            )

            # Determine signal using confluence-based system
            signal_result = self._determine_signal_v2(
                current_price, vwap, candle_analysis, volume_analysis,
                sr_levels, fvg_analysis, ob_analysis, fakeout_analysis, confluence
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

            # Check for volume spike exit warning
            volume_exit_warning = None
            if volume_analysis.get("strong_spike") and signal_result["signal"] != "WAIT":
                volume_exit_warning = "⚠️ Volume spike detected - Consider taking profits (거래량 급증 = 익절 시그널)"

            return {
                "ticker": ticker,
                "asset_type": "crypto" if is_crypto else "stock",
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
                    "exit_warning": volume_exit_warning,  # NEW: 거래량 급증 = 익절 시그널
                },
                "levels": {
                    "vwap": round(vwap, 2),
                    "nearest_support": sr_levels["nearest_support"]["price"] if sr_levels["nearest_support"] else None,
                    "nearest_resistance": sr_levels["nearest_resistance"]["price"] if sr_levels["nearest_resistance"] else None,
                    "support_strength": sr_levels["nearest_support"]["strength"] if sr_levels["nearest_support"] else 0,
                    "resistance_strength": sr_levels["nearest_resistance"]["strength"] if sr_levels["nearest_resistance"] else 0,
                },
                # NEW: Advanced Analysis (쉽알 Strategy)
                "fvg": {
                    "at_fvg": fvg_analysis.get("at_fvg"),
                    "nearest_fvg": fvg_analysis.get("nearest_fvg"),
                    "bullish_count": fvg_analysis.get("total_bullish", 0),
                    "bearish_count": fvg_analysis.get("total_bearish", 0),
                },
                "order_blocks": {
                    "at_ob": ob_analysis.get("at_ob"),
                    "double_ob": ob_analysis.get("double_ob"),
                    "nearest_support_ob": ob_analysis.get("nearest_support_ob"),
                    "nearest_resistance_ob": ob_analysis.get("nearest_resistance_ob"),
                },
                "fakeout": fakeout_analysis,
                "confluence": {
                    "direction": confluence["direction"],
                    "bullish_reasons": confluence["bullish_reasons"],
                    "bearish_reasons": confluence["bearish_reasons"],
                    "bullish_count": confluence["bullish_count"],
                    "bearish_count": confluence["bearish_count"],
                    "min_confluence_met": confluence["min_confluence_met"],
                    "total_score": max(confluence["bullish_score"], confluence["bearish_score"]),
                },
                "trade_setup": trade_setup,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Scalp analysis error for {ticker}: {e}")
            return {"error": str(e)}

    def _determine_signal_v2(
        self,
        price: float,
        vwap: float,
        candle_analysis: Dict,
        volume_analysis: Dict,
        sr_levels: Dict,
        fvg_analysis: Dict,
        ob_analysis: Dict,
        fakeout_analysis: Dict,
        confluence: Dict,
    ) -> Dict:
        """
        NEW Signal Determination using Confluence Scoring (쉽알 Strategy)

        Key Rules:
        1. Minimum 2 confluences required for entry
        2. Order Block + FVG overlap = Very strong
        3. Double Engulfing (이중 장악형) = Highest priority
        4. Fakeout/Trap = Good entry with clear stop
        5. Volume spike during position = Exit signal
        """
        reasoning = []

        # Get confluence data
        bullish_count = confluence["bullish_count"]
        bearish_count = confluence["bearish_count"]
        bullish_score = confluence["bullish_score"]
        bearish_score = confluence["bearish_score"]
        has_enough = confluence["has_enough_confluence"]

        # Add all reasons to reasoning
        for r in confluence["bullish_reasons"]:
            reasoning.append(f"🟢 {r['reason']} (+{r['strength']})")
        for r in confluence["bearish_reasons"]:
            reasoning.append(f"🔴 {r['reason']} (+{r['strength']})")

        # Check for double engulfing (이중 장악형) - Override everything
        double_ob = ob_analysis.get("double_ob")
        if double_ob:
            if double_ob["type"] == "bullish":
                reasoning.insert(0, "⭐ 이중 장악형 (Double Engulfing) - VERY STRONG SUPPORT")
                return {
                    "signal": "LONG",
                    "confidence": 90,
                    "bullish_score": max(bullish_score, 90),
                    "bearish_score": bearish_score,
                    "reasoning": reasoning,
                }
            elif double_ob["type"] == "bearish":
                reasoning.insert(0, "⭐ 이중 장악형 (Double Engulfing) - VERY STRONG RESISTANCE")
                return {
                    "signal": "SHORT",
                    "confidence": 90,
                    "bullish_score": bullish_score,
                    "bearish_score": max(bearish_score, 90),
                    "reasoning": reasoning,
                }

        # Check for fakeout/trap - Strong signal with clear stop
        trap = fakeout_analysis.get("trap")
        fakeout = fakeout_analysis.get("fakeout")

        if trap:
            if trap["type"] == "bullish":
                reasoning.insert(0, f"🎯 Double Bottom Trap - Entry LONG, Stop ${trap['stop_loss']:.2f}")
                return {
                    "signal": "LONG",
                    "confidence": min(85, bullish_score + 20),
                    "bullish_score": bullish_score,
                    "bearish_score": bearish_score,
                    "reasoning": reasoning,
                }
            else:
                reasoning.insert(0, f"🎯 Double Top Trap - Entry SHORT, Stop ${trap['stop_loss']:.2f}")
                return {
                    "signal": "SHORT",
                    "confidence": min(85, bearish_score + 20),
                    "bullish_score": bullish_score,
                    "bearish_score": bearish_score,
                    "reasoning": reasoning,
                }

        # Standard confluence-based signal
        # Rule: Minimum 2 confluences required (최소 2개 근거 필요!)
        if has_enough:
            if bullish_count >= 2 and bullish_score > bearish_score:
                signal = "LONG"
                confidence = min(95, bullish_score)
                reasoning.insert(0, f"✅ {bullish_count} bullish confluences detected (최소 2개 충족)")
            elif bearish_count >= 2 and bearish_score > bullish_score:
                signal = "SHORT"
                confidence = min(95, bearish_score)
                reasoning.insert(0, f"✅ {bearish_count} bearish confluences detected (최소 2개 충족)")
            else:
                signal = "WAIT"
                confidence = max(bullish_score, bearish_score)
                reasoning.insert(0, "⏳ Mixed signals - wait for clearer setup")
        else:
            signal = "WAIT"
            confidence = max(bullish_score, bearish_score, 10)
            if bullish_count == 1 or bearish_count == 1:
                reasoning.insert(0, f"⚠️ Only {max(bullish_count, bearish_count)} confluence - Need 2+ (근거 1개만 있음, 2개 이상 필요)")
            else:
                reasoning.insert(0, "❌ No clear confluences - wait for setup")

        # Add VWAP context
        if price > vwap:
            reasoning.append(f"📊 Price above VWAP ${vwap:.2f} (bullish bias)")
        else:
            reasoning.append(f"📊 Price below VWAP ${vwap:.2f} (bearish bias)")

        return {
            "signal": signal,
            "confidence": confidence,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "reasoning": reasoning,
        }

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
        volume_trend = volume_analysis.get("volume_trend", "neutral")
        volume_ratio = volume_analysis.get("volume_ratio", 1.0)

        if spike_detected:
            volume_score = min(15, int(volume_strength * 0.15))
            if bullish_score > bearish_score:
                bullish_score += volume_score
                reasoning.append(f"Volume spike confirms bullish move (+{volume_score})")
            elif bearish_score > bullish_score:
                bearish_score += volume_score
                reasoning.append(f"Volume spike confirms bearish move (+{volume_score})")
        elif volume_trend == "increasing" or volume_ratio >= 1.2:
            # Give partial credit for increasing volume or above average
            partial_score = 8 if volume_ratio >= 1.2 else 5
            if bullish_score > bearish_score:
                bullish_score += partial_score
                reasoning.append(f"Volume {volume_ratio:.1f}x average (+{partial_score})")
            elif bearish_score > bullish_score:
                bearish_score += partial_score
                reasoning.append(f"Volume {volume_ratio:.1f}x average (+{partial_score})")
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
        # Require minimum 45 points AND a candlestick pattern (lowered from 60)
        has_pattern = primary_pattern is not None and primary_pattern.get("strength", 0) >= 40

        if bullish_score >= 45 and has_pattern and candle_bias == "bullish":
            signal = "LONG"
            confidence = min(95, bullish_score)
        elif bearish_score >= 45 and has_pattern and candle_bias == "bearish":
            signal = "SHORT"
            confidence = min(95, bearish_score)
        elif bullish_score >= 35 or bearish_score >= 35:
            # Show potential setup even if not strong enough
            signal = "WAIT"
            confidence = max(bullish_score, bearish_score)
            reasoning.append("Potential setup forming - wait for confirmation")
        else:
            signal = "WAIT"
            confidence = max(10, max(bullish_score, bearish_score))
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

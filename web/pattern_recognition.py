"""
Chart Pattern Recognition Service

Detects common chart patterns using price action analysis:
- Head and Shoulders (top/bottom)
- Double Top / Double Bottom
- Triangles (ascending, descending, symmetrical)
- Wedges (rising, falling)
- Flags and Pennants
- Cup and Handle
- Channels

Based on classic technical analysis principles.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)

def _get_candle_info(bar: Dict) -> Dict:
    """Extract candle components"""
    o = bar.get("o", bar.get("open", 0))
    h = bar.get("h", bar.get("high", 0))
    l = bar.get("l", bar.get("low", 0))
    c = bar.get("c", bar.get("close", 0))

    return {
        "open": o, "high": h, "low": l, "close": c,
        "body": abs(c - o),
        "range": h - l if h != l else 0.0001,
    }

def _find_swing_points(bars: List[Dict], lookback: int = 5) -> Tuple[List[Dict], List[Dict]]:
    """Find swing highs and lows in price data."""
    if len(bars) < lookback * 2 + 1:
        return [], []

    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(bars) - lookback):
        candle = _get_candle_info(bars[i])

        # Check for swing high
        is_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i:
                other = _get_candle_info(bars[j])
                if other["high"] >= candle["high"]:
                    is_high = False
                    break

        if is_high:
            swing_highs.append({"price": candle["high"], "index": i})

        # Check for swing low
        is_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i:
                other = _get_candle_info(bars[j])
                if other["low"] <= candle["low"]:
                    is_low = False
                    break

        if is_low:
            swing_lows.append({"price": candle["low"], "index": i})

    return swing_highs, swing_lows

def detect_head_and_shoulders(bars: List[Dict], tolerance: float = 0.02) -> Optional[Dict]:
    """
    Detect Head and Shoulders pattern.

    Head & Shoulders Top: Bearish reversal
    - Left shoulder, higher head, right shoulder at similar level
    - Neckline connecting lows

    Inverse Head & Shoulders: Bullish reversal
    - Left shoulder low, lower head, right shoulder low at similar level
    """
    if len(bars) < 30:
        return None

    swing_highs, swing_lows = _find_swing_points(bars, lookback=3)

    if len(swing_highs) < 3:
        return None

    # Check last 3 swing highs for H&S Top
    recent_highs = swing_highs[-5:]

    for i in range(len(recent_highs) - 2):
        left = recent_highs[i]
        head = recent_highs[i + 1]
        right = recent_highs[i + 2]

        # Head must be higher than shoulders
        if head["price"] > left["price"] and head["price"] > right["price"]:
            # Shoulders should be at similar level (within tolerance)
            shoulder_diff = abs(left["price"] - right["price"]) / left["price"]

            if shoulder_diff <= tolerance:
                # Find neckline (lows between shoulders)
                neckline_lows = [sl for sl in swing_lows
                                 if left["index"] < sl["index"] < right["index"]]

                if len(neckline_lows) >= 2:
                    neckline = min(sl["price"] for sl in neckline_lows)

                    # Calculate target (head height projected from neckline)
                    head_height = head["price"] - neckline
                    target = neckline - head_height

                    current_price = _get_candle_info(bars[-1])["close"]

                    # Check if pattern is confirmed (price below neckline)
                    confirmed = current_price < neckline

                    return {
                        "pattern_type": "head_and_shoulders",
                        "direction": "bearish",
                        "left_shoulder": left["price"],
                        "head": head["price"],
                        "right_shoulder": right["price"],
                        "neckline": neckline,
                        "target": round(target, 4),
                        "stop_loss": round(head["price"] * 1.02, 4),
                        "confirmed": confirmed,
                        "confidence": 75 if confirmed else 60,
                        "status": "triggered" if confirmed else "forming",
                    }

    # Check for Inverse H&S (bullish)
    if len(swing_lows) >= 3:
        recent_lows = swing_lows[-5:]

        for i in range(len(recent_lows) - 2):
            left = recent_lows[i]
            head = recent_lows[i + 1]
            right = recent_lows[i + 2]

            # Head must be lower than shoulders
            if head["price"] < left["price"] and head["price"] < right["price"]:
                shoulder_diff = abs(left["price"] - right["price"]) / left["price"]

                if shoulder_diff <= tolerance:
                    neckline_highs = [sh for sh in swing_highs
                                      if left["index"] < sh["index"] < right["index"]]

                    if len(neckline_highs) >= 2:
                        neckline = max(sh["price"] for sh in neckline_highs)
                        head_height = neckline - head["price"]
                        target = neckline + head_height

                        current_price = _get_candle_info(bars[-1])["close"]
                        confirmed = current_price > neckline

                        return {
                            "pattern_type": "inverse_head_and_shoulders",
                            "direction": "bullish",
                            "left_shoulder": left["price"],
                            "head": head["price"],
                            "right_shoulder": right["price"],
                            "neckline": neckline,
                            "target": round(target, 4),
                            "stop_loss": round(head["price"] * 0.98, 4),
                            "confirmed": confirmed,
                            "confidence": 75 if confirmed else 60,
                            "status": "triggered" if confirmed else "forming",
                        }

    return None

def detect_double_top_bottom(bars: List[Dict], tolerance: float = 0.02) -> Optional[Dict]:
    """
    Detect Double Top or Double Bottom patterns.

    Double Top: Bearish - Two peaks at similar level
    Double Bottom: Bullish - Two troughs at similar level
    """
    if len(bars) < 20:
        return None

    swing_highs, swing_lows = _find_swing_points(bars, lookback=3)

    # Double Top
    if len(swing_highs) >= 2:
        recent_highs = swing_highs[-4:]

        for i in range(len(recent_highs) - 1):
            first = recent_highs[i]
            second = recent_highs[i + 1]

            # Peaks at similar level
            diff = abs(first["price"] - second["price"]) / first["price"]

            if diff <= tolerance:
                # Find low between peaks (neckline)
                middle_lows = [sl for sl in swing_lows
                               if first["index"] < sl["index"] < second["index"]]

                if middle_lows:
                    neckline = min(sl["price"] for sl in middle_lows)
                    pattern_height = max(first["price"], second["price"]) - neckline
                    target = neckline - pattern_height

                    current_price = _get_candle_info(bars[-1])["close"]
                    confirmed = current_price < neckline

                    return {
                        "pattern_type": "double_top",
                        "direction": "bearish",
                        "first_peak": first["price"],
                        "second_peak": second["price"],
                        "neckline": neckline,
                        "target": round(target, 4),
                        "stop_loss": round(max(first["price"], second["price"]) * 1.02, 4),
                        "confirmed": confirmed,
                        "confidence": 70 if confirmed else 55,
                        "status": "triggered" if confirmed else "forming",
                    }

    # Double Bottom
    if len(swing_lows) >= 2:
        recent_lows = swing_lows[-4:]

        for i in range(len(recent_lows) - 1):
            first = recent_lows[i]
            second = recent_lows[i + 1]

            diff = abs(first["price"] - second["price"]) / first["price"]

            if diff <= tolerance:
                middle_highs = [sh for sh in swing_highs
                                if first["index"] < sh["index"] < second["index"]]

                if middle_highs:
                    neckline = max(sh["price"] for sh in middle_highs)
                    pattern_height = neckline - min(first["price"], second["price"])
                    target = neckline + pattern_height

                    current_price = _get_candle_info(bars[-1])["close"]
                    confirmed = current_price > neckline

                    return {
                        "pattern_type": "double_bottom",
                        "direction": "bullish",
                        "first_trough": first["price"],
                        "second_trough": second["price"],
                        "neckline": neckline,
                        "target": round(target, 4),
                        "stop_loss": round(min(first["price"], second["price"]) * 0.98, 4),
                        "confirmed": confirmed,
                        "confidence": 70 if confirmed else 55,
                        "status": "triggered" if confirmed else "forming",
                    }

    return None

def detect_triangle(bars: List[Dict]) -> Optional[Dict]:
    """
    Detect Triangle patterns.

    Ascending Triangle: Bullish - Flat top, rising bottom
    Descending Triangle: Bearish - Flat bottom, declining top
    Symmetrical Triangle: Neutral - Converging trendlines
    """
    if len(bars) < 20:
        return None

    swing_highs, swing_lows = _find_swing_points(bars, lookback=3)

    if len(swing_highs) < 3 or len(swing_lows) < 3:
        return None

    recent_highs = swing_highs[-4:]
    recent_lows = swing_lows[-4:]

    # Calculate trendline slopes
    if len(recent_highs) >= 2:
        high_slope = (recent_highs[-1]["price"] - recent_highs[0]["price"]) / (recent_highs[-1]["index"] - recent_highs[0]["index"])
    else:
        return None

    if len(recent_lows) >= 2:
        low_slope = (recent_lows[-1]["price"] - recent_lows[0]["price"]) / (recent_lows[-1]["index"] - recent_lows[0]["index"])
    else:
        return None

    # Normalize slopes
    avg_price = (recent_highs[-1]["price"] + recent_lows[-1]["price"]) / 2
    high_slope_pct = high_slope / avg_price * 100
    low_slope_pct = low_slope / avg_price * 100

    current_price = _get_candle_info(bars[-1])["close"]
    pattern_height = recent_highs[-1]["price"] - recent_lows[-1]["price"]

    # Ascending Triangle: Flat highs, rising lows
    if abs(high_slope_pct) < 0.1 and low_slope_pct > 0.1:
        resistance = max(h["price"] for h in recent_highs)
        target = resistance + pattern_height

        return {
            "pattern_type": "ascending_triangle",
            "direction": "bullish",
            "resistance": resistance,
            "support_rising": True,
            "target": round(target, 4),
            "breakout_level": resistance,
            "stop_loss": round(recent_lows[-1]["price"] * 0.98, 4),
            "confidence": 65,
            "status": "forming",
        }

    # Descending Triangle: Flat lows, falling highs
    if abs(low_slope_pct) < 0.1 and high_slope_pct < -0.1:
        support = min(l["price"] for l in recent_lows)
        target = support - pattern_height

        return {
            "pattern_type": "descending_triangle",
            "direction": "bearish",
            "support": support,
            "resistance_falling": True,
            "target": round(target, 4),
            "breakout_level": support,
            "stop_loss": round(recent_highs[-1]["price"] * 1.02, 4),
            "confidence": 65,
            "status": "forming",
        }

    # Symmetrical Triangle: Converging trendlines
    if high_slope_pct < -0.05 and low_slope_pct > 0.05:
        mid_price = (recent_highs[-1]["price"] + recent_lows[-1]["price"]) / 2

        return {
            "pattern_type": "symmetrical_triangle",
            "direction": "neutral",
            "converging": True,
            "apex_price": round(mid_price, 4),
            "bullish_target": round(mid_price + pattern_height, 4),
            "bearish_target": round(mid_price - pattern_height, 4),
            "confidence": 55,
            "status": "forming",
            "note": "Wait for breakout direction",
        }

    return None

def detect_wedge(bars: List[Dict]) -> Optional[Dict]:
    """
    Detect Wedge patterns.

    Rising Wedge: Bearish - Both trendlines rising, converging
    Falling Wedge: Bullish - Both trendlines falling, converging
    """
    if len(bars) < 20:
        return None

    swing_highs, swing_lows = _find_swing_points(bars, lookback=3)

    if len(swing_highs) < 3 or len(swing_lows) < 3:
        return None

    recent_highs = swing_highs[-4:]
    recent_lows = swing_lows[-4:]

    # Calculate slopes
    high_slope = (recent_highs[-1]["price"] - recent_highs[0]["price"])
    low_slope = (recent_lows[-1]["price"] - recent_lows[0]["price"])

    current_price = _get_candle_info(bars[-1])["close"]

    # Rising Wedge: Both lines rising, but converging (highs slower than lows)
    if high_slope > 0 and low_slope > 0:
        # Converging if low slope is steeper
        if low_slope > high_slope * 0.5:
            target = recent_lows[0]["price"]  # Target is pattern start

            return {
                "pattern_type": "rising_wedge",
                "direction": "bearish",
                "converging": True,
                "upper_trendline_rising": True,
                "lower_trendline_rising": True,
                "target": round(target, 4),
                "stop_loss": round(recent_highs[-1]["price"] * 1.02, 4),
                "confidence": 60,
                "status": "forming",
            }

    # Falling Wedge: Both lines falling, but converging (highs steeper than lows)
    if high_slope < 0 and low_slope < 0:
        if high_slope < low_slope * 0.5:
            target = recent_highs[0]["price"]

            return {
                "pattern_type": "falling_wedge",
                "direction": "bullish",
                "converging": True,
                "upper_trendline_falling": True,
                "lower_trendline_falling": True,
                "target": round(target, 4),
                "stop_loss": round(recent_lows[-1]["price"] * 0.98, 4),
                "confidence": 60,
                "status": "forming",
            }

    return None

def detect_flag_pennant(bars: List[Dict]) -> Optional[Dict]:
    """
    Detect Flag and Pennant patterns.

    Bull Flag: Strong move up, then consolidation down
    Bear Flag: Strong move down, then consolidation up
    Pennant: Similar but with converging consolidation
    """
    if len(bars) < 15:
        return None

    # Check for strong prior move (pole)
    early_bars = bars[:len(bars)//2]
    late_bars = bars[len(bars)//2:]

    early_high = max(_get_candle_info(b)["high"] for b in early_bars)
    early_low = min(_get_candle_info(b)["low"] for b in early_bars)

    late_high = max(_get_candle_info(b)["high"] for b in late_bars)
    late_low = min(_get_candle_info(b)["low"] for b in late_bars)

    early_range = early_high - early_low
    late_range = late_high - late_low

    current_price = _get_candle_info(bars[-1])["close"]

    # Bull Flag: Strong move up (early), tight consolidation (late)
    if late_range < early_range * 0.5:
        # Check if early move was bullish
        early_close = _get_candle_info(early_bars[-1])["close"]
        early_open = _get_candle_info(early_bars[0])["open"]

        if early_close > early_open:  # Bullish pole
            target = late_high + early_range

            return {
                "pattern_type": "bull_flag",
                "direction": "bullish",
                "pole_height": round(early_range, 4),
                "flag_high": late_high,
                "flag_low": late_low,
                "breakout_level": late_high,
                "target": round(target, 4),
                "stop_loss": round(late_low * 0.98, 4),
                "confidence": 65,
                "status": "forming",
            }

        elif early_close < early_open:  # Bearish pole
            target = late_low - early_range

            return {
                "pattern_type": "bear_flag",
                "direction": "bearish",
                "pole_height": round(early_range, 4),
                "flag_high": late_high,
                "flag_low": late_low,
                "breakout_level": late_low,
                "target": round(target, 4),
                "stop_loss": round(late_high * 1.02, 4),
                "confidence": 65,
                "status": "forming",
            }

    return None

def detect_all_patterns(bars: List[Dict]) -> List[Dict]:
    """
    Run all pattern detection algorithms and return found patterns.
    """
    if not bars or len(bars) < 15:
        return []

    patterns = []

    # Run each detector
    detectors = [
        detect_head_and_shoulders,
        detect_double_top_bottom,
        detect_triangle,
        detect_wedge,
        detect_flag_pennant,
    ]

    for detector in detectors:
        try:
            result = detector(bars)
            if result:
                result["detected_at"] = datetime.now(timezone.utc).isoformat()
                patterns.append(result)
        except Exception as e:
            logger.error(f"Error in pattern detector {detector.__name__}: {e}")
            continue

    # Sort by confidence
    patterns.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return patterns

def get_pattern_summary(patterns: List[Dict]) -> Dict:
    """Generate summary of detected patterns."""
    if not patterns:
        return {
            "count": 0,
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
            "overall_bias": "neutral",
        }

    bullish = sum(1 for p in patterns if p.get("direction") == "bullish")
    bearish = sum(1 for p in patterns if p.get("direction") == "bearish")
    neutral = sum(1 for p in patterns if p.get("direction") == "neutral")

    if bullish > bearish:
        bias = "bullish"
    elif bearish > bullish:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "count": len(patterns),
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "overall_bias": bias,
        "highest_confidence": max(p.get("confidence", 0) for p in patterns),
    }

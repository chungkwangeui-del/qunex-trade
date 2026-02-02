"""
쉽알 Strategy - Day Trading Signal Service (Fixed Version)

Based on Korean trader "쉽알" methodology:
1. Order Blocks (장악형) - Engulfing patterns create S/R zones
2. FVG (Fair Value Gap) - Price gaps that get filled
3. Minimum 2 Confluences required for entry
4. Fakeout/Trap detection for counter-trend entries
5. Volume spike = EXIT signal (not entry confirmation)

Key Rules:
- 최소 2개 근거 필요 (Minimum 2 confluences)
- 장악형 + FVG = Strong entry zone
- 이중 장악형 = Very strong signal
- Entry at Order Block or FVG zone
- Stop below/above the zone
- TP at ACTUAL S/R levels (not fixed R:R) ← FIXED!
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from statistics import mean
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

def _get_candle_info(bar: Dict) -> Dict:
    """Extract candle components"""
    o = bar.get("o", bar.get("open", 0))
    h = bar.get("h", bar.get("high", 0))
    l = bar.get("l", bar.get("low", 0))
    c = bar.get("c", bar.get("close", 0))
    v = bar.get("v", bar.get("volume", 0))

    body = abs(c - o)
    total_range = h - l if h != l else 0.0001

    return {
        "open": o, "high": h, "low": l, "close": c, "volume": v,
        "body": body,
        "body_top": max(o, c),
        "body_bottom": min(o, c),
        "range": total_range,
        "body_percent": (body / total_range * 100) if total_range else 0,
        "is_bullish": c > o,
        "is_bearish": c < o,
    }

def _detect_swing_levels(bars: List[Dict], lookback: int = 5) -> Dict:
    """
    Detect Swing Highs and Swing Lows

    Swing High: Candle high is higher than N candles on both sides
    Swing Low: Candle low is lower than N candles on both sides

    These are key S/R levels for TP targeting!
    """
    if len(bars) < lookback * 2 + 1:
        return {"swing_highs": [], "swing_lows": []}

    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(bars) - lookback):
        candle = _get_candle_info(bars[i])

        # Check for Swing High
        is_swing_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i:
                other = _get_candle_info(bars[j])
                if other["high"] >= candle["high"]:
                    is_swing_high = False
                    break

        if is_swing_high:
            swing_highs.append({
                "price": candle["high"],
                "index": i,
                "type": "resistance",
                "strength": 70 + min(30, lookback * 5)  # More lookback = stronger
            })

        # Check for Swing Low
        is_swing_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i:
                other = _get_candle_info(bars[j])
                if other["low"] <= candle["low"]:
                    is_swing_low = False
                    break

        if is_swing_low:
            swing_lows.append({
                "price": candle["low"],
                "index": i,
                "type": "support",
                "strength": 70 + min(30, lookback * 5)
            })

    return {
        "swing_highs": swing_highs,
        "swing_lows": swing_lows
    }

def _detect_order_blocks(bars: List[Dict], lookback: int = 30) -> Dict:
    """
    Detect Order Blocks (장악형 캔들)

    Order Block = Engulfing pattern creates S/R zone
    - Bullish OB: Bearish candle engulfed by bullish = Support zone
    - Bearish OB: Bullish candle engulfed by bearish = Resistance zone
    """
    if len(bars) < 5:
        return {"bullish": [], "bearish": [], "double_ob": None}

    bullish_obs = []
    bearish_obs = []
    double_ob = None

    recent_bars = bars[-lookback:] if len(bars) > lookback else bars

    for i in range(1, len(recent_bars)):
        prev = _get_candle_info(recent_bars[i - 1])
        curr = _get_candle_info(recent_bars[i])

        # Bullish Engulfing (상승 장악형) -> Support zone
        if prev["is_bearish"] and curr["is_bullish"]:
            if curr["body_bottom"] <= prev["body_bottom"] and curr["body_top"] >= prev["body_top"]:
                if curr["body"] > prev["body"] * 1.1:  # Must be significantly larger
                    ob = {
                        "zone_top": prev["body_top"],
                        "zone_bottom": prev["body_bottom"],
                        "zone_mid": (prev["body_top"] + prev["body_bottom"]) / 2,
                        "strength": 70 + min(30, int(curr["body"] / prev["body"] * 10)),
                        "candle_idx": len(bars) - lookback + i if len(bars) > lookback else i,
                        "type": "support"
                    }
                    bullish_obs.append(ob)

        # Bearish Engulfing (하락 장악형) -> Resistance zone
        if prev["is_bullish"] and curr["is_bearish"]:
            if curr["body_bottom"] <= prev["body_bottom"] and curr["body_top"] >= prev["body_top"]:
                if curr["body"] > prev["body"] * 1.1:
                    ob = {
                        "zone_top": prev["body_top"],
                        "zone_bottom": prev["body_bottom"],
                        "zone_mid": (prev["body_top"] + prev["body_bottom"]) / 2,
                        "strength": 70 + min(30, int(curr["body"] / prev["body"] * 10)),
                        "candle_idx": len(bars) - lookback + i if len(bars) > lookback else i,
                        "type": "resistance"
                    }
                    bearish_obs.append(ob)

    # Detect Double Engulfing (이중 장악형) - VERY STRONG
    for i in range(2, len(recent_bars)):
        c1 = _get_candle_info(recent_bars[i - 2])
        c2 = _get_candle_info(recent_bars[i - 1])
        c3 = _get_candle_info(recent_bars[i])

        # Bullish Double: Bearish engulfs Bullish, then Bullish engulfs that Bearish
        if c1["is_bullish"] and c2["is_bearish"] and c3["is_bullish"]:
            c2_engulfs_c1 = c2["body_bottom"] <= c1["body_bottom"] and c2["body_top"] >= c1["body_top"]
            c3_engulfs_c2 = c3["body_bottom"] <= c2["body_bottom"] and c3["body_top"] >= c2["body_top"]
            if c2_engulfs_c1 and c3_engulfs_c2:
                double_ob = {
                    "type": "bullish",
                    "zone_top": c2["body_top"],
                    "zone_bottom": c2["body_bottom"],
                    "zone_mid": (c2["body_top"] + c2["body_bottom"]) / 2,
                    "strength": 95,
                    "description": "이중 장악형 - Very Strong Support"
                }

        # Bearish Double
        if c1["is_bearish"] and c2["is_bullish"] and c3["is_bearish"]:
            c2_engulfs_c1 = c2["body_bottom"] <= c1["body_bottom"] and c2["body_top"] >= c1["body_top"]
            c3_engulfs_c2 = c3["body_bottom"] <= c2["body_bottom"] and c3["body_top"] >= c2["body_top"]
            if c2_engulfs_c1 and c3_engulfs_c2:
                double_ob = {
                    "type": "bearish",
                    "zone_top": c2["body_top"],
                    "zone_bottom": c2["body_bottom"],
                    "zone_mid": (c2["body_top"] + c2["body_bottom"]) / 2,
                    "strength": 95,
                    "description": "이중 장악형 - Very Strong Resistance"
                }

    return {
        "bullish": bullish_obs[-5:],  # Keep last 5
        "bearish": bearish_obs[-5:],
        "double_ob": double_ob
    }

def _detect_fvg(bars: List[Dict], min_gap_percent: float = 0.15) -> Dict:
    """
    Detect Fair Value Gaps (FVG)

    FVG = Gap between candles where wicks don't overlap
    - Bullish FVG (gap up): Support zone when price returns
    - Bearish FVG (gap down): Resistance zone when price returns
    """
    if len(bars) < 10:
        return {"bullish": [], "bearish": []}

    bullish_fvgs = []
    bearish_fvgs = []

    for i in range(2, len(bars)):
        c1 = _get_candle_info(bars[i - 2])
        c3 = _get_candle_info(bars[i])

        # Bullish FVG: Candle 1 high < Candle 3 low (gap up)
        if c1["high"] < c3["low"]:
            gap_size = c3["low"] - c1["high"]
            gap_percent = (gap_size / c1["high"]) * 100 if c1["high"] > 0 else 0
            if gap_percent >= min_gap_percent:
                fvg = {
                    "zone_top": c3["low"],
                    "zone_bottom": c1["high"],
                    "zone_mid": (c3["low"] + c1["high"]) / 2,
                    "size_percent": round(gap_percent, 2),
                    "strength": min(100, 60 + int(gap_percent * 20)),
                    "type": "support"
                }
                bullish_fvgs.append(fvg)

        # Bearish FVG: Candle 1 low > Candle 3 high (gap down)
        if c1["low"] > c3["high"]:
            gap_size = c1["low"] - c3["high"]
            gap_percent = (gap_size / c3["high"]) * 100 if c3["high"] > 0 else 0
            if gap_percent >= min_gap_percent:
                fvg = {
                    "zone_top": c1["low"],
                    "zone_bottom": c3["high"],
                    "zone_mid": (c1["low"] + c3["high"]) / 2,
                    "size_percent": round(gap_percent, 2),
                    "strength": min(100, 60 + int(gap_percent * 20)),
                    "type": "resistance"
                }
                bearish_fvgs.append(fvg)

    return {
        "bullish": bullish_fvgs[-5:],
        "bearish": bearish_fvgs[-5:]
    }

def _detect_fakeout(bars: List[Dict], lookback: int = 20) -> Optional[Dict]:
    """
    Detect Fakeout (헛돌파)

    Fakeout = Price breaks a level but quickly reverses back
    - Good entry opportunity in opposite direction
    """
    if len(bars) < lookback:
        return None

    recent = bars[-lookback:]
    highs = [_get_candle_info(b)["high"] for b in recent[:-3]]
    lows = [_get_candle_info(b)["low"] for b in recent[:-3]]

    if not highs or not lows:
        return None

    resistance = max(highs)
    support = min(lows)

    last_3 = [_get_candle_info(b) for b in bars[-3:]]
    current = last_3[-1]

    # Bullish Fakeout: Broke below support but closed back above
    for candle in last_3[:-1]:
        if candle["low"] < support * 0.998:  # Broke support
            if current["close"] > support:  # But closed back above
                return {
                    "type": "bullish",
                    "description": "Fakeout below support - LONG opportunity",
                    "false_break": candle["low"],
                    "level": support,
                    "stop_loss": candle["low"] * 0.998,
                    "strength": 80,
                }

    # Bearish Fakeout: Broke above resistance but closed back below
    for candle in last_3[:-1]:
        if candle["high"] > resistance * 1.002:
            if current["close"] < resistance:
                return {
                    "type": "bearish",
                    "description": "Fakeout above resistance - SHORT opportunity",
                    "false_break": candle["high"],
                    "level": resistance,
                    "stop_loss": candle["high"] * 1.002,
                    "strength": 80,
                }

    return None

def _check_at_zone(price: float, zones: List[Dict], tolerance_pct: float = 0.3) -> Optional[Dict]:
    """Check if price is at/near a zone"""
    for zone in zones:
        zone_size = zone["zone_top"] - zone["zone_bottom"]
        extended_top = zone["zone_top"] + zone_size * (tolerance_pct / 100)
        extended_bottom = zone["zone_bottom"] - zone_size * (tolerance_pct / 100)

        if extended_bottom <= price <= extended_top:
            return zone
    return None

def _get_vwap(bars: List[Dict]) -> Optional[float]:
    """Calculate VWAP"""
    if len(bars) < 5:
        return None

    cumulative_tp_vol = 0
    cumulative_vol = 0

    for bar in bars:
        info = _get_candle_info(bar)
        typical_price = (info["high"] + info["low"] + info["close"]) / 3
        volume = info["volume"]
        cumulative_tp_vol += typical_price * volume
        cumulative_vol += volume

    return cumulative_tp_vol / cumulative_vol if cumulative_vol > 0 else None

def _analyze_volume(bars: List[Dict]) -> Dict:
    """Analyze volume for exit signals"""
    if len(bars) < 20:
        return {"ratio": 1.0, "spike": False, "exit_warning": None}

    volumes = [_get_candle_info(b)["volume"] for b in bars]
    current_vol = volumes[-1]
    avg_vol = mean(volumes[-20:])

    ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
    spike = ratio >= 2.0

    exit_warning = None
    if spike:
        exit_warning = f"Volume spike {ratio:.1f}x - Consider taking profits (쉽알: 거래량 급증 = 익절)"

    return {
        "ratio": round(ratio, 2),
        "spike": spike,
        "exit_warning": exit_warning
    }

def _build_sr_levels(
    current_price: float,
    order_blocks: Dict,
    fvgs: Dict,
    swing_levels: Dict
) -> Dict:
    """
    Build comprehensive S/R level list from all sources

    Returns:
        - supports: List of support levels BELOW current price (sorted descending - nearest first)
        - resistances: List of resistance levels ABOVE current price (sorted ascending - nearest first)
    """
    supports = []
    resistances = []

    # Add Swing Lows as support
    for sl in swing_levels["swing_lows"]:
        if sl["price"] < current_price:
            supports.append({
                "price": sl["price"],
                "type": "swing_low",
                "strength": sl["strength"]
            })

    # Add Swing Highs as resistance
    for sh in swing_levels["swing_highs"]:
        if sh["price"] > current_price:
            resistances.append({
                "price": sh["price"],
                "type": "swing_high",
                "strength": sh["strength"]
            })

    # Add Bullish Order Blocks as support (below price)
    for ob in order_blocks["bullish"]:
        if ob["zone_mid"] < current_price:
            supports.append({
                "price": ob["zone_mid"],
                "zone_top": ob["zone_top"],
                "zone_bottom": ob["zone_bottom"],
                "type": "order_block",
                "strength": ob["strength"]
            })

    # Add Bearish Order Blocks as resistance (above price)
    for ob in order_blocks["bearish"]:
        if ob["zone_mid"] > current_price:
            resistances.append({
                "price": ob["zone_mid"],
                "zone_top": ob["zone_top"],
                "zone_bottom": ob["zone_bottom"],
                "type": "order_block",
                "strength": ob["strength"]
            })

    # Add Bullish FVGs as support
    for fvg in fvgs["bullish"]:
        if fvg["zone_mid"] < current_price:
            supports.append({
                "price": fvg["zone_mid"],
                "zone_top": fvg["zone_top"],
                "zone_bottom": fvg["zone_bottom"],
                "type": "fvg",
                "strength": fvg["strength"]
            })

    # Add Bearish FVGs as resistance
    for fvg in fvgs["bearish"]:
        if fvg["zone_mid"] > current_price:
            resistances.append({
                "price": fvg["zone_mid"],
                "zone_top": fvg["zone_top"],
                "zone_bottom": fvg["zone_bottom"],
                "type": "fvg",
                "strength": fvg["strength"]
            })

    # Double OB is very strong
    if order_blocks["double_ob"]:
        dob = order_blocks["double_ob"]
        level = {
            "price": dob["zone_mid"],
            "zone_top": dob["zone_top"],
            "zone_bottom": dob["zone_bottom"],
            "type": "double_order_block",
            "strength": dob["strength"]
        }
        if dob["type"] == "bullish" and dob["zone_mid"] < current_price:
            supports.append(level)
        elif dob["type"] == "bearish" and dob["zone_mid"] > current_price:
            resistances.append(level)

    # Sort: supports descending (nearest first), resistances ascending (nearest first)
    supports = sorted(supports, key=lambda x: x["price"], reverse=True)
    resistances = sorted(resistances, key=lambda x: x["price"])

    # Remove duplicates (levels within 0.2% of each other)
    def remove_duplicates(levels):
        if not levels:
            return []
        result = [levels[0]]
        for level in levels[1:]:
            last_price = result[-1]["price"]
            if abs(level["price"] - last_price) / last_price > 0.002:  # 0.2% threshold
                result.append(level)
        return result

    supports = remove_duplicates(supports)
    resistances = remove_duplicates(resistances)

    return {
        "supports": supports,
        "resistances": resistances
    }

def _calculate_confluence(
    current_price: float,
    order_blocks: Dict,
    fvgs: Dict,
    fakeout: Optional[Dict],
    vwap: Optional[float],
    last_candle: Dict
) -> Dict:
    """
    Calculate confluence score - 쉽알 핵심: 최소 2개 근거 필요
    """
    bullish_reasons = []
    bearish_reasons = []

    # 1. At Bullish Order Block (Support)
    at_bullish_ob = _check_at_zone(current_price, order_blocks["bullish"])
    if at_bullish_ob:
        bullish_reasons.append({
            "reason": f"At Bullish Order Block (장악형 지지)",
            "strength": at_bullish_ob["strength"],
            "zone": at_bullish_ob
        })

    # 2. At Bearish Order Block (Resistance)
    at_bearish_ob = _check_at_zone(current_price, order_blocks["bearish"])
    if at_bearish_ob:
        bearish_reasons.append({
            "reason": f"At Bearish Order Block (장악형 저항)",
            "strength": at_bearish_ob["strength"],
            "zone": at_bearish_ob
        })

    # 3. Double Order Block (이중 장악형) - Very Strong!
    if order_blocks["double_ob"]:
        dob = order_blocks["double_ob"]
        if dob["zone_bottom"] <= current_price <= dob["zone_top"]:
            if dob["type"] == "bullish":
                bullish_reasons.append({
                    "reason": "이중 장악형 - Very Strong Support!",
                    "strength": 95,
                    "zone": dob
                })
            else:
                bearish_reasons.append({
                    "reason": "이중 장악형 - Very Strong Resistance!",
                    "strength": 95,
                    "zone": dob
                })

    # 4. At Bullish FVG (Support)
    at_bullish_fvg = _check_at_zone(current_price, fvgs["bullish"])
    if at_bullish_fvg:
        bullish_reasons.append({
            "reason": f"At Bullish FVG zone ({at_bullish_fvg['size_percent']}% gap)",
            "strength": at_bullish_fvg["strength"],
            "zone": at_bullish_fvg
        })

    # 5. At Bearish FVG (Resistance)
    at_bearish_fvg = _check_at_zone(current_price, fvgs["bearish"])
    if at_bearish_fvg:
        bearish_reasons.append({
            "reason": f"At Bearish FVG zone ({at_bearish_fvg['size_percent']}% gap)",
            "strength": at_bearish_fvg["strength"],
            "zone": at_bearish_fvg
        })

    # 6. Fakeout signal
    if fakeout:
        if fakeout["type"] == "bullish":
            bullish_reasons.append({
                "reason": fakeout["description"],
                "strength": fakeout["strength"],
                "fakeout": fakeout
            })
        else:
            bearish_reasons.append({
                "reason": fakeout["description"],
                "strength": fakeout["strength"],
                "fakeout": fakeout
            })

    # 7. VWAP confluence
    if vwap:
        vwap_dist_pct = abs(current_price - vwap) / vwap * 100
        if vwap_dist_pct < 0.3:  # Within 0.3% of VWAP
            if current_price > vwap and last_candle["is_bullish"]:
                bullish_reasons.append({
                    "reason": "Bouncing off VWAP (above)",
                    "strength": 60
                })
            elif current_price < vwap and last_candle["is_bearish"]:
                bearish_reasons.append({
                    "reason": "Rejected at VWAP (below)",
                    "strength": 60
                })

    # 8. Candlestick pattern confirmation
    if last_candle["body_percent"] > 60:  # Strong candle
        if last_candle["is_bullish"]:
            bullish_reasons.append({
                "reason": f"Strong bullish candle ({last_candle['body_percent']:.0f}% body)",
                "strength": 55
            })
        else:
            bearish_reasons.append({
                "reason": f"Strong bearish candle ({last_candle['body_percent']:.0f}% body)",
                "strength": 55
            })

    # Calculate totals
    bullish_count = len(bullish_reasons)
    bearish_count = len(bearish_reasons)
    bullish_score = sum(r["strength"] for r in bullish_reasons)
    bearish_score = sum(r["strength"] for r in bearish_reasons)

    # Determine direction
    direction = "neutral"
    if bullish_count >= 2 and bullish_score > bearish_score:
        direction = "bullish"
    elif bearish_count >= 2 and bearish_score > bullish_score:
        direction = "bearish"

    # Check minimum confluence (쉽알: 최소 2개 근거)
    min_met = (direction == "bullish" and bullish_count >= 2) or \
              (direction == "bearish" and bearish_count >= 2)

    return {
        "direction": direction,
        "min_confluence_met": min_met,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "bullish_reasons": bullish_reasons,
        "bearish_reasons": bearish_reasons,
    }

def generate_scalp_signal(
    candles: List[Dict[str, Any]],
    risk_reward: float = 2.0  # Minimum R:R requirement (not for TP calc)
) -> Optional[Dict[str, Any]]:
    """
    Generate scalp signal using 쉽알 Strategy (FIXED)

    Requirements:
    - Minimum 2 confluences for entry
    - Entry at Order Block or FVG zone
    - Clear stop loss below/above zone
    - TP at ACTUAL S/R levels (not fixed R:R!)
    """
    if not candles or len(candles) < 30:
        return None

    # Normalize candle keys
    normalized = []
    for c in candles:
        normalized.append({
            "o": c.get("o", c.get("open", 0)),
            "h": c.get("h", c.get("high", 0)),
            "l": c.get("l", c.get("low", 0)),
            "c": c.get("c", c.get("close", 0)),
            "v": c.get("v", c.get("volume", 0)),
        })
    candles = normalized

    current_candle = _get_candle_info(candles[-1])
    current_price = current_candle["close"]

    # Detect all zones
    order_blocks = _detect_order_blocks(candles)
    fvgs = _detect_fvg(candles)
    swing_levels = _detect_swing_levels(candles, lookback=5)
    fakeout = _detect_fakeout(candles)
    vwap = _get_vwap(candles)
    volume_info = _analyze_volume(candles)

    # Build S/R levels from all sources
    sr_levels = _build_sr_levels(current_price, order_blocks, fvgs, swing_levels)

    # Calculate confluence
    confluence = _calculate_confluence(
        current_price, order_blocks, fvgs, fakeout, vwap, current_candle
    )

    # No signal if minimum confluence not met
    if not confluence["min_confluence_met"]:
        return {
            "signal": "WAIT",
            "direction": confluence["direction"],
            "confluence": confluence,
            "reason": ["최소 2개 근거 필요 - 현재 조건 미충족"],
            "volume": volume_info,
            "vwap": round(vwap, 4) if vwap else None,
            "sr_levels": sr_levels,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Generate signal based on direction
    direction = confluence["direction"]
    reasons = confluence["bullish_reasons"] if direction == "bullish" else confluence["bearish_reasons"]

    # Find entry and stop based on zone
    entry = current_price
    stop = None
    zone_used = None

    if direction == "bullish":
        # LONG: Stop below nearest support
        for reason in reasons:
            if "zone" in reason:
                zone_used = reason["zone"]
                stop = zone_used.get("zone_bottom", zone_used.get("zone_mid", current_price)) * 0.998
                break
            elif "fakeout" in reason:
                stop = reason["fakeout"]["stop_loss"]
                break

        if stop is None:
            # Use nearest support level
            if sr_levels["supports"]:
                stop = sr_levels["supports"][0]["price"] * 0.998
            else:
                # Fallback: recent swing low
                recent_lows = [_get_candle_info(c)["low"] for c in candles[-10:]]
                stop = min(recent_lows) * 0.998

        # TP at resistance levels (actual S/R, not fixed R:R!)
        risk = abs(entry - stop)

        if sr_levels["resistances"]:
            # Use actual resistance levels as TP targets
            tp1 = sr_levels["resistances"][0]["price"] if len(sr_levels["resistances"]) > 0 else None
            tp2 = sr_levels["resistances"][1]["price"] if len(sr_levels["resistances"]) > 1 else None
            tp3 = sr_levels["resistances"][2]["price"] if len(sr_levels["resistances"]) > 2 else None

            # Ensure minimum R:R is met for TP1
            min_tp1 = entry + risk * risk_reward
            if tp1 and tp1 < min_tp1:
                # If first resistance doesn't meet R:R, use calculated value
                tp1 = min_tp1
        else:
            # Fallback: calculated R:R targets
            tp1 = entry + risk * risk_reward
            tp2 = entry + risk * (risk_reward + 1)
            tp3 = entry + risk * (risk_reward + 2)

        # Fill in missing TPs
        if tp1 and not tp2:
            tp2 = tp1 * 1.015  # 1.5% above TP1
        if tp2 and not tp3:
            tp3 = tp2 * 1.015  # 1.5% above TP2

    else:  # bearish / SHORT
        # SHORT: Stop above nearest resistance
        for reason in reasons:
            if "zone" in reason:
                zone_used = reason["zone"]
                stop = zone_used.get("zone_top", zone_used.get("zone_mid", current_price)) * 1.002
                break
            elif "fakeout" in reason:
                stop = reason["fakeout"]["stop_loss"]
                break

        if stop is None:
            # Use nearest resistance level
            if sr_levels["resistances"]:
                stop = sr_levels["resistances"][0]["price"] * 1.002
            else:
                # Fallback: recent swing high
                recent_highs = [_get_candle_info(c)["high"] for c in candles[-10:]]
                stop = max(recent_highs) * 1.002

        # TP at support levels (actual S/R, not fixed R:R!)
        risk = abs(entry - stop)

        if sr_levels["supports"]:
            # Use actual support levels as TP targets
            tp1 = sr_levels["supports"][0]["price"] if len(sr_levels["supports"]) > 0 else None
            tp2 = sr_levels["supports"][1]["price"] if len(sr_levels["supports"]) > 1 else None
            tp3 = sr_levels["supports"][2]["price"] if len(sr_levels["supports"]) > 2 else None

            # Ensure minimum R:R is met for TP1
            max_tp1 = entry - risk * risk_reward
            if tp1 and tp1 > max_tp1:
                # If first support doesn't meet R:R, use calculated value
                tp1 = max_tp1
        else:
            # Fallback: calculated R:R targets
            tp1 = entry - risk * risk_reward
            tp2 = entry - risk * (risk_reward + 1)
            tp3 = entry - risk * (risk_reward + 2)

        # Fill in missing TPs
        if tp1 and not tp2:
            tp2 = tp1 * 0.985  # 1.5% below TP1
        if tp2 and not tp3:
            tp3 = tp2 * 0.985  # 1.5% below TP2

    # Validate we have valid levels
    if stop is None or tp1 is None:
        return None

    risk = abs(entry - stop)
    if risk <= 0:
        return None

    # Calculate actual R:R for each TP
    actual_rr1 = abs(tp1 - entry) / risk if risk > 0 else 0
    actual_rr2 = abs(tp2 - entry) / risk if tp2 and risk > 0 else 0
    actual_rr3 = abs(tp3 - entry) / risk if tp3 and risk > 0 else 0

    # Build reason strings
    reason_strs = [r["reason"] for r in reasons]

    # Calculate confidence
    total_score = confluence["bullish_score"] if direction == "bullish" else confluence["bearish_score"]
    confidence = min(95, total_score // 2)

    # Add volume exit warning if applicable
    if volume_info["exit_warning"]:
        reason_strs.append(f"⚠️ {volume_info['exit_warning']}")

    # Add TP level info to reasons
    if sr_levels["resistances"] if direction == "bullish" else sr_levels["supports"]:
        target_levels = sr_levels["resistances"] if direction == "bullish" else sr_levels["supports"]
        if target_levels:
            tp_type = target_levels[0].get("type", "level")
            reason_strs.append(f"TP targets at actual {tp_type} levels")

    return {
        "signal": "LONG" if direction == "bullish" else "SHORT",
        "direction": direction,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "tp1": round(tp1, 4) if tp1 else None,
        "tp2": round(tp2, 4) if tp2 else None,
        "tp3": round(tp3, 4) if tp3 else None,
        "r_multiple": {
            "tp1": round(actual_rr1, 2),
            "tp2": round(actual_rr2, 2),
            "tp3": round(actual_rr3, 2),
        },
        "confidence": confidence,
        "reason": reason_strs,
        "confluence": confluence,
        "volume": volume_info,
        "vwap": round(vwap, 4) if vwap else None,
        "sr_levels": {
            "supports": [{"price": round(s["price"], 4), "type": s["type"]} for s in sr_levels["supports"][:5]],
            "resistances": [{"price": round(r["price"], 4), "type": r["type"]} for r in sr_levels["resistances"][:5]],
        },
        "order_blocks": {
            "bullish_count": len(order_blocks["bullish"]),
            "bearish_count": len(order_blocks["bearish"]),
            "double_ob": order_blocks["double_ob"],
        },
        "fvg": {
            "bullish_count": len(fvgs["bullish"]),
            "bearish_count": len(fvgs["bearish"]),
        },
        "fakeout": fakeout,
        "levels": {
            "vwap": round(vwap, 4) if vwap else None,
            "nearest_support": sr_levels["supports"][0]["price"] if sr_levels["supports"] else None,
            "nearest_resistance": sr_levels["resistances"][0]["price"] if sr_levels["resistances"] else None,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

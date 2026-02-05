"""
ICT/SMC Swing Trading Service

Based on Inner Circle Trader (ICT) methodology by Michael J. Huddleston.
Designed for Swing Trading (holding period: days to weeks).

Key Concepts Implemented:
1. Market Structure - BOS (Break of Structure), CHoCH (Change of Character)
2. Liquidity - BSL (Buy Side), SSL (Sell Side), Liquidity Sweeps
3. Order Blocks - Institutional order zones
4. Breaker Blocks - Failed order blocks that become S/R
5. Fair Value Gaps (FVG) - Price imbalances
6. Premium/Discount Zones - Above/below 50% equilibrium
7. OTE (Optimal Trade Entry) - 62%-79% Fibonacci retracement
8. Kill Zones - High probability trading hours
9. Multi-Timeframe Analysis - Daily bias → 4H structure → 1H entry

Sources:
- https://innercircletrader.net/
- https://www.writofinance.com/guide-to-smc-and-ict/
- https://tradingfinder.com/education/forex/
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from statistics import mean
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

# =============================================================================
# CANDLE UTILITIES
# =============================================================================

def _get_candle_info(bar: Dict) -> Dict:
    """Extract candle components with body analysis"""
    o = bar.get("o", bar.get("open", 0))
    h = bar.get("h", bar.get("high", 0))
    l = bar.get("l", bar.get("low", 0))
    c = bar.get("c", bar.get("close", 0))
    v = bar.get("v", bar.get("volume", 0))
    t = bar.get("t", bar.get("timestamp", bar.get("time", None)))

    body = abs(c - o)
    total_range = h - l if h != l else 0.0001
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    return {
        "open": o, "high": h, "low": l, "close": c, "volume": v,
        "timestamp": t,
        "body": body,
        "body_top": max(o, c),
        "body_bottom": min(o, c),
        "range": total_range,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_percent": (body / total_range * 100) if total_range else 0,
        "is_bullish": c > o,
        "is_bearish": c < o,
        "is_doji": body < total_range * 0.1,  # Body < 10% of range
    }

def _normalize_candles(candles: List[Dict]) -> List[Dict]:
    """Normalize candle keys to standard format"""
    normalized = []
    for c in candles:
        normalized.append({
            "o": c.get("o", c.get("open", 0)),
            "h": c.get("h", c.get("high", 0)),
            "l": c.get("l", c.get("low", 0)),
            "c": c.get("c", c.get("close", 0)),
            "v": c.get("v", c.get("volume", 0)),
            "t": c.get("t", c.get("timestamp", c.get("time", None))),
        })
    return normalized

# =============================================================================
# MARKET STRUCTURE - BOS & CHoCH
# =============================================================================

def _find_swing_points(bars: List[Dict], lookback: int = 5) -> Dict:
    """
    Find Swing Highs and Swing Lows for market structure analysis.

    Swing High: Candle with highest high among N candles on both sides
    Swing Low: Candle with lowest low among N candles on both sides
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
                "timestamp": candle.get("timestamp"),
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
                "timestamp": candle.get("timestamp"),
            })

    return {
        "swing_highs": swing_highs,
        "swing_lows": swing_lows
    }

def _detect_market_structure(bars: List[Dict], lookback: int = 5) -> Dict:
    """
    Detect Market Structure: BOS (Break of Structure) and CHoCH (Change of Character)

    BOS = Trend continuation (HH in uptrend, LL in downtrend)
    CHoCH = Trend reversal (LL in uptrend, HH in downtrend)

    Returns current trend and recent structure breaks.
    """
    swing_points = _find_swing_points(bars, lookback)
    swing_highs = swing_points["swing_highs"]
    swing_lows = swing_points["swing_lows"]

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {
            "trend": "neutral",
            "bos": None,
            "choch": None,
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            # Provide zeroed structure counts so downstream consumers never KeyError
            "hh_count": 0,
            "hl_count": 0,
            "lh_count": 0,
            "ll_count": 0,
            "last_hh": None,
            "last_ll": None,
            "last_hl": None,
            "last_lh": None,
        }

    # Analyze recent swing points
    recent_highs = swing_highs[-4:] if len(swing_highs) >= 4 else swing_highs
    recent_lows = swing_lows[-4:] if len(swing_lows) >= 4 else swing_lows

    # Determine trend from swing structure
    hh_count = 0  # Higher Highs
    hl_count = 0  # Higher Lows
    lh_count = 0  # Lower Highs
    ll_count = 0  # Lower Lows

    for i in range(1, len(recent_highs)):
        if recent_highs[i]["price"] > recent_highs[i-1]["price"]:
            hh_count += 1
        else:
            lh_count += 1

    for i in range(1, len(recent_lows)):
        if recent_lows[i]["price"] > recent_lows[i-1]["price"]:
            hl_count += 1
        else:
            ll_count += 1

    # Determine current trend
    if hh_count >= 1 and hl_count >= 1:
        trend = "bullish"  # Uptrend: HH + HL
    elif ll_count >= 1 and lh_count >= 1:
        trend = "bearish"  # Downtrend: LL + LH
    else:
        trend = "neutral"

    # Detect BOS and CHoCH
    bos = None
    choch = None
    current_price = _get_candle_info(bars[-1])["close"]

    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        last_swing_high = recent_highs[-1]["price"]
        prev_swing_high = recent_highs[-2]["price"]
        last_swing_low = recent_lows[-1]["price"]
        prev_swing_low = recent_lows[-2]["price"]

        # BOS Detection
        if trend == "bullish":
            if current_price > last_swing_high:
                bos = {
                    "type": "bullish",
                    "level": last_swing_high,
                    "description": "BOS - Price broke above swing high (trend continuation)"
                }
            elif current_price < last_swing_low:
                choch = {
                    "type": "bearish",
                    "level": last_swing_low,
                    "description": "CHoCH - Price broke below swing low (potential reversal)"
                }

        elif trend == "bearish":
            if current_price < last_swing_low:
                bos = {
                    "type": "bearish",
                    "level": last_swing_low,
                    "description": "BOS - Price broke below swing low (trend continuation)"
                }
            elif current_price > last_swing_high:
                choch = {
                    "type": "bullish",
                    "level": last_swing_high,
                    "description": "CHoCH - Price broke above swing high (potential reversal)"
                }

    return {
        "trend": trend,
        "bos": bos,
        "choch": choch,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "hh_count": hh_count,
        "hl_count": hl_count,
        "lh_count": lh_count,
        "ll_count": ll_count,
    }

# =============================================================================
# LIQUIDITY - BSL, SSL & SWEEPS
# =============================================================================

def _detect_liquidity_zones(bars: List[Dict], lookback: int = 20) -> Dict:
    """
    Detect Buy Side Liquidity (BSL) and Sell Side Liquidity (SSL) zones.

    BSL: Stop losses above resistance (equal highs, swing highs)
    SSL: Stop losses below support (equal lows, swing lows)

    Liquidity pools form at:
    - Equal highs/lows (EQH/EQL)
    - Swing highs/lows
    - Previous day/week highs/lows
    """
    if len(bars) < lookback:
        return {"bsl": [], "ssl": [], "sweeps": []}

    recent_bars = bars[-lookback:]
    bsl_zones = []
    ssl_zones = []

    # Find swing highs as BSL
    swing_points = _find_swing_points(recent_bars, lookback=3)

    for sh in swing_points["swing_highs"]:
        bsl_zones.append({
            "price": sh["price"],
            "type": "swing_high",
            "strength": 70,
        })

    for sl in swing_points["swing_lows"]:
        ssl_zones.append({
            "price": sl["price"],
            "type": "swing_low",
            "strength": 70,
        })

    # Detect Equal Highs (EQH) - Strong BSL
    highs = [_get_candle_info(b)["high"] for b in recent_bars]
    for i in range(len(highs) - 1):
        for j in range(i + 1, len(highs)):
            # Within 0.1% = equal highs
            if abs(highs[i] - highs[j]) / highs[i] < 0.001:
                bsl_zones.append({
                    "price": (highs[i] + highs[j]) / 2,
                    "type": "equal_highs",
                    "strength": 85,  # EQH is stronger
                })
                break

    # Detect Equal Lows (EQL) - Strong SSL
    lows = [_get_candle_info(b)["low"] for b in recent_bars]
    for i in range(len(lows) - 1):
        for j in range(i + 1, len(lows)):
            if abs(lows[i] - lows[j]) / lows[i] < 0.001:
                ssl_zones.append({
                    "price": (lows[i] + lows[j]) / 2,
                    "type": "equal_lows",
                    "strength": 85,
                })
                break

    # Detect liquidity sweeps in recent candles
    sweeps = _detect_liquidity_sweeps(bars, bsl_zones, ssl_zones)

    return {
        "bsl": sorted(bsl_zones, key=lambda x: x["price"]),
        "ssl": sorted(ssl_zones, key=lambda x: x["price"], reverse=True),
        "sweeps": sweeps,
    }

def _detect_liquidity_sweeps(
    bars: List[Dict],
    bsl_zones: List[Dict],
    ssl_zones: List[Dict]
) -> List[Dict]:
    """
    Detect Liquidity Sweeps - Price takes out liquidity then reverses.

    Bullish Sweep: Price breaks below SSL, then closes above
    Bearish Sweep: Price breaks above BSL, then closes below

    Liquidity sweeps are HIGH PROBABILITY reversal signals.
    """
    sweeps = []
    if len(bars) < 5:
        return sweeps

    last_candles = [_get_candle_info(b) for b in bars[-5:]]
    current = last_candles[-1]

    # Check for bullish sweep (SSL taken then recovered)
    for ssl in ssl_zones:
        for candle in last_candles[:-1]:
            # Wick went below SSL
            if candle["low"] < ssl["price"] * 0.998:
                # But current closed above
                if current["close"] > ssl["price"]:
                    sweeps.append({
                        "type": "bullish",
                        "level": ssl["price"],
                        "description": f"Liquidity sweep below {ssl['type']} - LONG setup",
                        "strength": ssl["strength"] + 10,
                    })
                    break

    # Check for bearish sweep (BSL taken then rejected)
    for bsl in bsl_zones:
        for candle in last_candles[:-1]:
            if candle["high"] > bsl["price"] * 1.002:
                if current["close"] < bsl["price"]:
                    sweeps.append({
                        "type": "bearish",
                        "level": bsl["price"],
                        "description": f"Liquidity sweep above {bsl['type']} - SHORT setup",
                        "strength": bsl["strength"] + 10,
                    })
                    break

    return sweeps

# =============================================================================
# ORDER BLOCKS & BREAKER BLOCKS
# =============================================================================

def _detect_order_blocks(bars: List[Dict], lookback: int = 30) -> Dict:
    """
    Detect ICT Order Blocks - Institutional order zones.

    Bullish OB: Last bearish candle before impulsive bullish move
    Bearish OB: Last bullish candle before impulsive bearish move

    Valid OB requirements:
    - Must precede displacement (strong move)
    - Should have BOS or CHoCH following
    """
    if len(bars) < 10:
        return {"bullish": [], "bearish": [], "breakers": []}

    bullish_obs = []
    bearish_obs = []
    recent_bars = bars[-lookback:] if len(bars) > lookback else bars

    for i in range(2, len(recent_bars) - 1):
        prev = _get_candle_info(recent_bars[i - 1])
        curr = _get_candle_info(recent_bars[i])
        next_candle = _get_candle_info(recent_bars[i + 1])

        # Bullish Order Block: Bearish candle before bullish displacement
        if prev["is_bearish"] and curr["is_bullish"]:
            # Check for displacement (strong move)
            if curr["body"] > prev["body"] * 1.5 and curr["body_percent"] > 60:
                # Next candle should continue upward
                if next_candle["close"] > curr["close"]:
                    ob = {
                        "zone_top": prev["body_top"],
                        "zone_bottom": prev["low"],  # Include wick for OB
                        "zone_mid": (prev["body_top"] + prev["low"]) / 2,
                        "strength": 75 + min(25, int(curr["body_percent"] / 4)),
                        "index": i - 1,
                        "valid": True,
                    }
                    bullish_obs.append(ob)

        # Bearish Order Block: Bullish candle before bearish displacement
        if prev["is_bullish"] and curr["is_bearish"]:
            if curr["body"] > prev["body"] * 1.5 and curr["body_percent"] > 60:
                if next_candle["close"] < curr["close"]:
                    ob = {
                        "zone_top": prev["high"],  # Include wick for OB
                        "zone_bottom": prev["body_bottom"],
                        "zone_mid": (prev["high"] + prev["body_bottom"]) / 2,
                        "strength": 75 + min(25, int(curr["body_percent"] / 4)),
                        "index": i - 1,
                        "valid": True,
                    }
                    bearish_obs.append(ob)

    # Detect Breaker Blocks (failed Order Blocks)
    breakers = _detect_breaker_blocks(bars, bullish_obs, bearish_obs)

    # Mark invalidated OBs
    current_price = _get_candle_info(bars[-1])["close"]
    for ob in bullish_obs:
        if current_price < ob["zone_bottom"]:
            ob["valid"] = False
    for ob in bearish_obs:
        if current_price > ob["zone_top"]:
            ob["valid"] = False

    return {
        "bullish": [ob for ob in bullish_obs if ob["valid"]][-5:],
        "bearish": [ob for ob in bearish_obs if ob["valid"]][-5:],
        "breakers": breakers,
    }

def _detect_breaker_blocks(
    bars: List[Dict],
    bullish_obs: List[Dict],
    bearish_obs: List[Dict]
) -> List[Dict]:
    """
    Detect Breaker Blocks - Failed Order Blocks that become S/R.

    Bullish Breaker: Bearish OB that got broken, now acts as support
    Bearish Breaker: Bullish OB that got broken, now acts as resistance
    """
    breakers = []
    current_price = _get_candle_info(bars[-1])["close"]

    # Check for broken bearish OBs becoming bullish breakers
    for ob in bearish_obs:
        # Price broke above bearish OB (invalidated)
        if current_price > ob["zone_top"]:
            # Now this zone acts as support
            breakers.append({
                "type": "bullish",
                "zone_top": ob["zone_top"],
                "zone_bottom": ob["zone_bottom"],
                "zone_mid": ob["zone_mid"],
                "strength": ob["strength"],
                "description": "Bullish Breaker - Failed bearish OB now support",
            })

    # Check for broken bullish OBs becoming bearish breakers
    for ob in bullish_obs:
        if current_price < ob["zone_bottom"]:
            breakers.append({
                "type": "bearish",
                "zone_top": ob["zone_top"],
                "zone_bottom": ob["zone_bottom"],
                "zone_mid": ob["zone_mid"],
                "strength": ob["strength"],
                "description": "Bearish Breaker - Failed bullish OB now resistance",
            })

    return breakers[-3:]  # Keep last 3

# =============================================================================
# FAIR VALUE GAPS (FVG)
# =============================================================================

def _detect_fvg(bars: List[Dict], min_gap_percent: float = 0.1) -> Dict:
    """
    Detect Fair Value Gaps (FVG) - Price imbalances.

    FVG forms when candle 1's wick doesn't overlap with candle 3's wick.

    Bullish FVG: C1 high < C3 low (gap up) - Support zone
    Bearish FVG: C1 low > C3 high (gap down) - Resistance zone

    Price tends to return to "fill" these gaps.
    """
    if len(bars) < 10:
        return {"bullish": [], "bearish": []}

    bullish_fvgs = []
    bearish_fvgs = []

    for i in range(2, len(bars)):
        c1 = _get_candle_info(bars[i - 2])
        c2 = _get_candle_info(bars[i - 1])  # The impulsive candle
        c3 = _get_candle_info(bars[i])

        # Bullish FVG: Gap up (C1 high < C3 low)
        if c1["high"] < c3["low"]:
            gap_size = c3["low"] - c1["high"]
            gap_percent = (gap_size / c1["high"]) * 100 if c1["high"] > 0 else 0

            if gap_percent >= min_gap_percent:
                # Check if C2 was impulsive (displacement)
                if c2["is_bullish"] and c2["body_percent"] > 50:
                    fvg = {
                        "zone_top": c3["low"],
                        "zone_bottom": c1["high"],
                        "zone_mid": (c3["low"] + c1["high"]) / 2,  # Consequent Encroachment
                        "size_percent": round(gap_percent, 2),
                        "strength": min(100, 65 + int(gap_percent * 15)),
                        "filled": False,
                        "index": i,
                    }
                    bullish_fvgs.append(fvg)

        # Bearish FVG: Gap down (C1 low > C3 high)
        if c1["low"] > c3["high"]:
            gap_size = c1["low"] - c3["high"]
            gap_percent = (gap_size / c3["high"]) * 100 if c3["high"] > 0 else 0

            if gap_percent >= min_gap_percent:
                if c2["is_bearish"] and c2["body_percent"] > 50:
                    fvg = {
                        "zone_top": c1["low"],
                        "zone_bottom": c3["high"],
                        "zone_mid": (c1["low"] + c3["high"]) / 2,
                        "size_percent": round(gap_percent, 2),
                        "strength": min(100, 65 + int(gap_percent * 15)),
                        "filled": False,
                        "index": i,
                    }
                    bearish_fvgs.append(fvg)

    # Check if FVGs are filled
    current_price = _get_candle_info(bars[-1])["close"]

    for fvg in bullish_fvgs:
        # FVG is filled if price traded through the zone
        if current_price < fvg["zone_bottom"]:
            fvg["filled"] = True

    for fvg in bearish_fvgs:
        if current_price > fvg["zone_top"]:
            fvg["filled"] = True

    return {
        "bullish": [f for f in bullish_fvgs if not f["filled"]][-5:],
        "bearish": [f for f in bearish_fvgs if not f["filled"]][-5:],
    }

# =============================================================================
# PREMIUM/DISCOUNT & OTE (OPTIMAL TRADE ENTRY)
# =============================================================================

def _calculate_premium_discount(bars: List[Dict], lookback: int = 50) -> Dict:
    """
    Calculate Premium and Discount zones using recent range.

    Premium Zone: Above 50% of range (expensive - look for shorts)
    Discount Zone: Below 50% of range (cheap - look for longs)

    Equilibrium: The 50% level
    """
    if len(bars) < lookback:
        lookback = len(bars)

    recent = bars[-lookback:]

    highest = max(_get_candle_info(b)["high"] for b in recent)
    lowest = min(_get_candle_info(b)["low"] for b in recent)
    range_size = highest - lowest

    if range_size == 0:
        return {"premium_zone": None, "discount_zone": None, "equilibrium": None}

    equilibrium = lowest + (range_size * 0.5)

    # OTE Zone: 62% - 79% retracement
    # For bullish: discount area between 0.62 and 0.79 from high
    # For bearish: premium area between 0.62 and 0.79 from low

    ote_bullish_top = highest - (range_size * 0.62)  # 62% retracement
    ote_bullish_bottom = highest - (range_size * 0.79)  # 79% retracement
    ote_bearish_top = lowest + (range_size * 0.79)
    ote_bearish_bottom = lowest + (range_size * 0.62)

    current_price = _get_candle_info(bars[-1])["close"]

    # Determine if price is in premium or discount
    price_position = (current_price - lowest) / range_size if range_size > 0 else 0.5

    zone = "premium" if price_position > 0.5 else "discount"
    in_ote = False
    ote_type = None

    # Check if in OTE zone
    if ote_bullish_bottom <= current_price <= ote_bullish_top:
        in_ote = True
        ote_type = "bullish"  # Good for longs
    elif ote_bearish_bottom <= current_price <= ote_bearish_top:
        in_ote = True
        ote_type = "bearish"  # Good for shorts

    return {
        "highest": round(highest, 4),
        "lowest": round(lowest, 4),
        "equilibrium": round(equilibrium, 4),
        "premium_zone": {
            "top": round(highest, 4),
            "bottom": round(equilibrium, 4),
        },
        "discount_zone": {
            "top": round(equilibrium, 4),
            "bottom": round(lowest, 4),
        },
        "ote_bullish": {
            "top": round(ote_bullish_top, 4),
            "bottom": round(ote_bullish_bottom, 4),
            "mid": round((ote_bullish_top + ote_bullish_bottom) / 2, 4),  # 70.5% level
        },
        "ote_bearish": {
            "top": round(ote_bearish_top, 4),
            "bottom": round(ote_bearish_bottom, 4),
            "mid": round((ote_bearish_top + ote_bearish_bottom) / 2, 4),
        },
        "current_zone": zone,
        "price_position": round(price_position * 100, 1),  # Percentage in range
        "in_ote": in_ote,
        "ote_type": ote_type,
    }

# =============================================================================
# KILL ZONES
# =============================================================================

def _check_kill_zone() -> Dict:
    """
    Check current time against ICT Kill Zones (New York Time).

    Kill Zones are optimal trading hours with highest institutional activity:
    - Asian: 7PM - 10PM EST
    - London: 2AM - 5AM EST (highest probability)
    - New York: 7AM - 10AM EST (highest volatility)
    - London Close: 10AM - 12PM EST
    """
    now = datetime.now(timezone.utc)

    # Convert to EST (UTC-5, ignoring DST for simplicity)
    est_hour = (now.hour - 5) % 24

    kill_zones = {
        "asian": {"start": 19, "end": 22, "name": "Asian", "volatility": "low"},
        "london": {"start": 2, "end": 5, "name": "London", "volatility": "high"},
        "new_york": {"start": 7, "end": 10, "name": "New York", "volatility": "highest"},
        "london_close": {"start": 10, "end": 12, "name": "London Close", "volatility": "medium"},
    }

    current_zone = None
    for zone_id, zone in kill_zones.items():
        if zone["start"] <= est_hour < zone["end"]:
            current_zone = {
                "name": zone["name"],
                "volatility": zone["volatility"],
                "optimal_for_entry": zone_id in ["london", "new_york"],
            }
            break

    return {
        "est_hour": est_hour,
        "current_kill_zone": current_zone,
        "in_optimal_zone": current_zone is not None and current_zone.get("optimal_for_entry", False),
        "kill_zones": kill_zones,
    }

# =============================================================================
# CONFLUENCE SCORING
# =============================================================================

def _calculate_confluence(
    current_price: float,
    market_structure: Dict,
    liquidity: Dict,
    order_blocks: Dict,
    fvgs: Dict,
    premium_discount: Dict,
) -> Dict:
    """
    Calculate ICT Confluence Score.

    High probability setups require multiple confluences:
    1. Market structure alignment (trend + BOS/CHoCH)
    2. Liquidity sweep
    3. At Order Block or FVG
    4. In OTE zone (discount for longs, premium for shorts)
    5. During Kill Zone
    """
    bullish_reasons = []
    bearish_reasons = []

    # 1. Market Structure
    if market_structure["trend"] == "bullish":
        bullish_reasons.append({
            "reason": "Bullish market structure (HH + HL)",
            "strength": 60,
        })
        if market_structure["bos"] and market_structure["bos"]["type"] == "bullish":
            bullish_reasons.append({
                "reason": market_structure["bos"]["description"],
                "strength": 75,
            })
    elif market_structure["trend"] == "bearish":
        bearish_reasons.append({
            "reason": "Bearish market structure (LH + LL)",
            "strength": 60,
        })
        if market_structure["bos"] and market_structure["bos"]["type"] == "bearish":
            bearish_reasons.append({
                "reason": market_structure["bos"]["description"],
                "strength": 75,
            })

    # CHoCH signals potential reversal
    if market_structure["choch"]:
        choch = market_structure["choch"]
        if choch["type"] == "bullish":
            bullish_reasons.append({
                "reason": choch["description"],
                "strength": 80,
            })
        else:
            bearish_reasons.append({
                "reason": choch["description"],
                "strength": 80,
            })

    # 2. Liquidity Sweeps (HIGH PROBABILITY!)
    for sweep in liquidity["sweeps"]:
        if sweep["type"] == "bullish":
            bullish_reasons.append({
                "reason": sweep["description"],
                "strength": sweep["strength"],
            })
        else:
            bearish_reasons.append({
                "reason": sweep["description"],
                "strength": sweep["strength"],
            })

    # 3. At Order Block
    for ob in order_blocks["bullish"]:
        if ob["zone_bottom"] <= current_price <= ob["zone_top"]:
            bullish_reasons.append({
                "reason": "At Bullish Order Block (institutional demand)",
                "strength": ob["strength"],
                "zone": ob,
            })

    for ob in order_blocks["bearish"]:
        if ob["zone_bottom"] <= current_price <= ob["zone_top"]:
            bearish_reasons.append({
                "reason": "At Bearish Order Block (institutional supply)",
                "strength": ob["strength"],
                "zone": ob,
            })

    # Breaker Blocks
    for bb in order_blocks["breakers"]:
        if bb["zone_bottom"] <= current_price <= bb["zone_top"]:
            if bb["type"] == "bullish":
                bullish_reasons.append({
                    "reason": bb["description"],
                    "strength": bb["strength"],
                    "zone": bb,
                })
            else:
                bearish_reasons.append({
                    "reason": bb["description"],
                    "strength": bb["strength"],
                    "zone": bb,
                })

    # 4. At FVG
    for fvg in fvgs["bullish"]:
        if fvg["zone_bottom"] <= current_price <= fvg["zone_top"]:
            bullish_reasons.append({
                "reason": f"At Bullish FVG ({fvg['size_percent']}% gap)",
                "strength": fvg["strength"],
                "zone": fvg,
            })

    for fvg in fvgs["bearish"]:
        if fvg["zone_bottom"] <= current_price <= fvg["zone_top"]:
            bearish_reasons.append({
                "reason": f"At Bearish FVG ({fvg['size_percent']}% gap)",
                "strength": fvg["strength"],
                "zone": fvg,
            })

    # 5. Premium/Discount Zone
    if premium_discount["in_ote"]:
        if premium_discount["ote_type"] == "bullish":
            bullish_reasons.append({
                "reason": "In OTE zone (discount) - Optimal for longs",
                "strength": 70,
            })
        else:
            bearish_reasons.append({
                "reason": "In OTE zone (premium) - Optimal for shorts",
                "strength": 70,
            })
    elif premium_discount["current_zone"] == "discount":
        bullish_reasons.append({
            "reason": f"Price in Discount zone ({premium_discount['price_position']:.0f}%)",
            "strength": 55,
        })
    elif premium_discount["current_zone"] == "premium":
        bearish_reasons.append({
            "reason": f"Price in Premium zone ({premium_discount['price_position']:.0f}%)",
            "strength": 55,
        })

    # Calculate scores
    bullish_score = sum(r["strength"] for r in bullish_reasons)
    bearish_score = sum(r["strength"] for r in bearish_reasons)

    # Determine direction
    direction = "neutral"
    if len(bullish_reasons) >= 2 and bullish_score > bearish_score:
        direction = "bullish"
    elif len(bearish_reasons) >= 2 and bearish_score > bullish_score:
        direction = "bearish"

    return {
        "direction": direction,
        "bullish_count": len(bullish_reasons),
        "bearish_count": len(bearish_reasons),
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "bullish_reasons": bullish_reasons,
        "bearish_reasons": bearish_reasons,
        "min_confluence_met": (direction == "bullish" and len(bullish_reasons) >= 2) or \
                             (direction == "bearish" and len(bearish_reasons) >= 2),
    }

# =============================================================================
# MAIN SIGNAL GENERATOR
# =============================================================================

def generate_swing_signal(
    candles: List[Dict[str, Any]],
    timeframe: str = "4H",  # Default to 4H for swing trading
) -> Optional[Dict[str, Any]]:
    """
    Generate ICT/SMC Swing Trading Signal.

    Requirements for entry:
    1. Clear market structure (trend identified)
    2. Minimum 2 confluences
    3. Preferably in Kill Zone
    4. Entry at OB, FVG, or OTE zone

    Args:
        candles: OHLCV candle data
        timeframe: Chart timeframe (1H, 4H, D)

    Returns:
        Signal dictionary with entry, stop, targets
    """
    if not candles or len(candles) < 50:
        return None

    # Normalize candles
    candles = _normalize_candles(candles)

    current_candle = _get_candle_info(candles[-1])
    current_price = current_candle["close"]

    # Check if price data is valid
    if current_price == 0 or current_price is None:
        return {
            "signal": "ERROR",
            "error": "Price data unavailable. The market may be closed or API quota exceeded.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Analyze all ICT concepts
    market_structure = _detect_market_structure(candles, lookback=5)
    liquidity = _detect_liquidity_zones(candles, lookback=30)
    order_blocks = _detect_order_blocks(candles, lookback=50)
    fvgs = _detect_fvg(candles)
    premium_discount = _calculate_premium_discount(candles, lookback=50)
    kill_zone = _check_kill_zone()

    # Calculate confluence
    confluence = _calculate_confluence(
        current_price,
        market_structure,
        liquidity,
        order_blocks,
        fvgs,
        premium_discount,
    )

    # No signal if minimum confluence not met
    if not confluence["min_confluence_met"]:
        # Calculate a low confidence score for WAIT signals
        total_score = max(confluence["bullish_score"], confluence["bearish_score"])
        confluence_count = max(confluence["bullish_count"], confluence["bearish_count"])
        wait_confidence = min(40, (total_score // 4) + (confluence_count * 3))

        return {
            "signal": "WAIT",
            "direction": confluence["direction"],
            "timeframe": timeframe,
            "confidence": wait_confidence,  # Include confidence for WAIT signals
            "entry": None,
            "stop": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "confluence": {
                "count": confluence_count,
                "score": total_score,
                "details": confluence,
            },
            "reason": ["Minimum 2 confluences required - conditions not met"],
            "market_structure": {
                "trend": market_structure["trend"],
                "bos": market_structure["bos"],
                "choch": market_structure["choch"],
                "hh_count": market_structure.get("hh_count", 0),
                "hl_count": market_structure.get("hl_count", 0),
                "lh_count": market_structure.get("lh_count", 0),
                "ll_count": market_structure.get("ll_count", 0),
            },
            "liquidity": {
                "bsl_count": len(liquidity["bsl"]),
                "ssl_count": len(liquidity["ssl"]),
                "sweeps": liquidity["sweeps"],
            },
            "order_blocks": {
                "bullish_count": len(order_blocks["bullish"]),
                "bearish_count": len(order_blocks["bearish"]),
                "breaker_count": len(order_blocks["breakers"]),
            },
            "fvg": {
                "bullish_count": len(fvgs["bullish"]),
                "bearish_count": len(fvgs["bearish"]),
            },
            "premium_discount": premium_discount,
            "kill_zone": kill_zone,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Generate signal
    direction = confluence["direction"]
    reasons = confluence["bullish_reasons"] if direction == "bullish" else confluence["bearish_reasons"]

    # Find entry zone and set stop loss
    entry = current_price
    stop = None
    zone_used = None

    # Build S/R levels for targets
    swing_highs = market_structure["swing_highs"]
    swing_lows = market_structure["swing_lows"]

    if direction == "bullish":
        # Entry at OB, FVG, or OTE
        for reason in reasons:
            if "zone" in reason:
                zone_used = reason["zone"]
                stop = zone_used.get("zone_bottom", zone_used.get("zone_mid", current_price)) * 0.995
                break

        if stop is None:
            # Use nearest swing low or SSL
            if liquidity["ssl"]:
                stop = liquidity["ssl"][0]["price"] * 0.995
            elif swing_lows:
                stop = swing_lows[-1]["price"] * 0.995
            else:
                recent_lows = [_get_candle_info(c)["low"] for c in candles[-20:]]
                stop = min(recent_lows) * 0.995

        # Targets at swing highs and BSL
        targets = []
        for sh in sorted(swing_highs, key=lambda x: x["price"]):
            if sh["price"] > current_price:
                targets.append(sh["price"])
        for bsl in liquidity["bsl"]:
            if bsl["price"] > current_price:
                targets.append(bsl["price"])

        targets = sorted(set(targets))[:3]

    else:  # bearish
        for reason in reasons:
            if "zone" in reason:
                zone_used = reason["zone"]
                stop = zone_used.get("zone_top", zone_used.get("zone_mid", current_price)) * 1.005
                break

        if stop is None:
            if liquidity["bsl"]:
                stop = liquidity["bsl"][-1]["price"] * 1.005
            elif swing_highs:
                stop = swing_highs[-1]["price"] * 1.005
            else:
                recent_highs = [_get_candle_info(c)["high"] for c in candles[-20:]]
                stop = max(recent_highs) * 1.005

        targets = []
        for sl in sorted(swing_lows, key=lambda x: x["price"], reverse=True):
            if sl["price"] < current_price:
                targets.append(sl["price"])
        for ssl in liquidity["ssl"]:
            if ssl["price"] < current_price:
                targets.append(ssl["price"])

        targets = sorted(set(targets), reverse=True)[:3]

    # Ensure we have targets
    risk = abs(entry - stop)
    if not targets:
        if direction == "bullish":
            targets = [entry + risk * 2, entry + risk * 3, entry + risk * 4]
        else:
            targets = [entry - risk * 2, entry - risk * 3, entry - risk * 4]

    tp1 = targets[0] if len(targets) > 0 else None
    tp2 = targets[1] if len(targets) > 1 else (tp1 * 1.02 if tp1 and direction == "bullish" else tp1 * 0.98 if tp1 else None)
    tp3 = targets[2] if len(targets) > 2 else (tp2 * 1.02 if tp2 and direction == "bullish" else tp2 * 0.98 if tp2 else None)

    # Calculate R multiples
    r_tp1 = abs(tp1 - entry) / risk if tp1 and risk > 0 else 0
    r_tp2 = abs(tp2 - entry) / risk if tp2 and risk > 0 else 0
    r_tp3 = abs(tp3 - entry) / risk if tp3 and risk > 0 else 0

    # Build reason strings
    reason_strs = [r["reason"] for r in reasons[:5]]

    # Add Kill Zone info
    if kill_zone["in_optimal_zone"]:
        reason_strs.append(f"In {kill_zone['current_kill_zone']['name']} Kill Zone ✓")

    # Confidence based on confluence score and count
    total_score = confluence["bullish_score"] if direction == "bullish" else confluence["bearish_score"]
    confluence_count = confluence["bullish_count"] if direction == "bullish" else confluence["bearish_count"]
    confidence = min(95, (total_score // 3) + (confluence_count * 5))

    return {
        "signal": "LONG" if direction == "bullish" else "SHORT",
        "direction": direction,
        "timeframe": timeframe,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "tp1": round(tp1, 4) if tp1 else None,
        "tp2": round(tp2, 4) if tp2 else None,
        "tp3": round(tp3, 4) if tp3 else None,
        "r_multiple": {
            "tp1": round(r_tp1, 2),
            "tp2": round(r_tp2, 2),
            "tp3": round(r_tp3, 2),
        },
        "confidence": confidence,
        "reason": reason_strs,
        "confluence": {
            "count": confluence_count,
            "score": total_score,
            "details": confluence,
        },
        "market_structure": {
            "trend": market_structure["trend"],
            "bos": market_structure["bos"],
            "choch": market_structure["choch"],
            "hh_count": market_structure["hh_count"],
            "hl_count": market_structure["hl_count"],
            "lh_count": market_structure["lh_count"],
            "ll_count": market_structure["ll_count"],
        },
        "liquidity": {
            "bsl_count": len(liquidity["bsl"]),
            "ssl_count": len(liquidity["ssl"]),
            "sweeps": liquidity["sweeps"],
        },
        "order_blocks": {
            "bullish_count": len(order_blocks["bullish"]),
            "bearish_count": len(order_blocks["bearish"]),
            "breaker_count": len(order_blocks["breakers"]),
        },
        "fvg": {
            "bullish_count": len(fvgs["bullish"]),
            "bearish_count": len(fvgs["bearish"]),
        },
        "premium_discount": premium_discount,
        "kill_zone": kill_zone,
        "levels": {
            "equilibrium": premium_discount["equilibrium"],
            "ote_zone": premium_discount["ote_bullish"] if direction == "bullish" else premium_discount["ote_bearish"],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

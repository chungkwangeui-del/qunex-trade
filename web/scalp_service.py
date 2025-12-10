"""
Scalp/Day-trade signal service.
Calculates entry, stop, and TP1 from intraday data with transparent rules.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from statistics import mean


def _find_swings(values: List[float], lookback: int = 3) -> Dict[str, List[Dict[str, float]]]:
    """Find swing highs/lows indices with simple lookback window."""
    highs = []
    lows = []
    for i in range(lookback, len(values) - lookback):
        window_prev = values[i - lookback : i]
        window_next = values[i + 1 : i + 1 + lookback]
        val = values[i]
        if val > max(window_prev) and val > max(window_next):
            highs.append({"price": val, "idx": i})
        if val < min(window_prev) and val < min(window_next):
            lows.append({"price": val, "idx": i})
    return {"highs": highs, "lows": lows}


def _cluster_levels(levels: List[Dict[str, float]], pct: float = 0.005) -> List[Dict[str, float]]:
    """Cluster nearby price levels within pct band; returns averaged levels with strength."""
    if not levels:
        return []
    levels = sorted(levels, key=lambda x: x["price"])
    clusters: List[List[Dict[str, float]]] = []
    current = [levels[0]]
    for lvl in levels[1:]:
        if abs(lvl["price"] - current[-1]["price"]) / current[-1]["price"] <= pct:
            current.append(lvl)
        else:
            clusters.append(current)
            current = [lvl]
    clusters.append(current)

    result = []
    for cl in clusters:
        avg_price = sum(l["price"] for l in cl) / len(cl)
        strength = len(cl)
        result.append({"price": avg_price, "touches": strength, "strength": min(5, strength)})
    return result


def _swing_sr(highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, Optional[Dict[str, float]]]:
    """Compute nearest support/resistance from swing clusters."""
    swings = _find_swings(closes, lookback=3)
    swing_highs = _cluster_levels(swings["highs"], pct=0.005)
    swing_lows = _cluster_levels(swings["lows"], pct=0.005)

    current = closes[-1]
    nearest_res = None
    for sh in swing_highs:
        if sh["price"] > current:
            if nearest_res is None or sh["price"] < nearest_res["price"]:
                nearest_res = sh

    nearest_sup = None
    for sl in swing_lows:
        if sl["price"] < current:
            if nearest_sup is None or sl["price"] > nearest_sup["price"]:
                nearest_sup = sl

    return {
        "support": nearest_sup,
        "resistance": nearest_res,
        "swing_highs": swing_highs[-5:],
        "swing_lows": swing_lows[-5:],
    }


def _ema(values: List[float], period: int) -> Optional[float]:
    if not values or len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _rsi(values: List[float], period: int = 14) -> Optional[float]:
    if len(values) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    if len(gains) < period or len(losses) < period:
        return None
    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _recent_high_low(closes: List[float], lookback: int = 20):
    if len(closes) < lookback:
        return None, None
    window = closes[-lookback:]
    return max(window), min(window)


def _confidence_score(ema20: float, ema50: float, rsi: float, vol_ratio: float) -> int:
    """Lightweight confidence heuristic (0-100) as a pseudo-ML filter."""
    score = 0
    # Trend strength
    trend_gap = ema20 - ema50
    if trend_gap > 0:
        score += min(35, trend_gap / ema50 * 2000)  # scaled
    # Momentum
    if rsi >= 60:
        score += 25
    elif rsi >= 55:
        score += 15
    # Volume
    if vol_ratio >= 2.0:
        score += 25
    elif vol_ratio >= 1.5:
        score += 15
    # Floor/ceiling
    return int(max(0, min(100, score)))


def generate_scalp_signal(
    candles: List[Dict[str, Any]], risk_reward: float = 2.0
) -> Optional[Dict[str, Any]]:
    """
    Generate scalp signal from candles (assumes ascending time).
    candles items: {timestamp, open, high, low, close, volume}
    """
    if not candles or len(candles) < 50:
        return None

    closes = [c["close"] for c in candles if c.get("close") is not None]
    highs = [c["high"] for c in candles if c.get("high") is not None]
    lows = [c["low"] for c in candles if c.get("low") is not None]
    vols = [c.get("volume", 0) for c in candles]

    if len(closes) < 50:
        return None

    ema20 = _ema(closes[-50:], 20)
    ema50 = _ema(closes[-50:], 50)
    rsi = _rsi(closes[-50:], 14)

    if ema20 is None or ema50 is None or rsi is None:
        return None

    # Trend/momentum filter
    uptrend = ema20 > ema50
    bullish_rsi = rsi >= 55

    # Volume surge vs 20-bar average
    vol_avg20 = mean(vols[-20:]) if len(vols) >= 20 else None
    vol_ratio = vols[-1] / vol_avg20 if vol_avg20 else 1
    vol_surge = vol_ratio >= 1.5 if vol_avg20 else False

    prior_high, prior_low = _recent_high_low(highs, 20)
    if prior_high is None or prior_low is None:
        return None

    last_close = closes[-1]
    breakout = last_close > prior_high

    if not (uptrend and bullish_rsi and breakout and vol_surge):
        return None

    entry = last_close
    stop = prior_low
    risk = entry - stop
    if risk <= 0:
        return None
    # Support / Resistance context (swing-based)
    sr = _swing_sr(highs, lows, closes)
    support = sr.get("support")
    resistance = sr.get("resistance")

    tp1 = entry + risk * risk_reward
    tp2 = entry + risk * (risk_reward + 1)  # e.g., 3R if risk_reward=2
    tp3 = entry + risk * (risk_reward + 2)  # e.g., 4R if risk_reward=2

    # Snap TP to nearest resistance if closer (for longs)
    rr_to_resistance = None
    if resistance and resistance.get("price"):
        rr_to_resistance = (resistance["price"] - entry) / risk if risk > 0 else None
        snapped_tp = min(tp1, resistance["price"])
        if snapped_tp > entry:
            tp1 = snapped_tp

    # Enforce minimum R:R to nearest resistance (avoid weak setups)
    if rr_to_resistance is not None and rr_to_resistance < 1.2:
        return None

    reason = [
        f"Trend: EMA20 ({ema20:.2f}) > EMA50 ({ema50:.2f})",
        f"Momentum: RSI(14)={rsi:.1f} (>=55)",
        f"Volume: {vols[-1]:.0f} vs 20-bar avg {vol_avg20:.0f} ({vol_ratio:.2f}x)" if vol_avg20 else "Volume check skipped",
        f"Breakout: close {last_close:.2f} > prior 20-bar high {prior_high:.2f}",
        f"Risk/Reward: {risk_reward:.1f}R, stop at prior low {prior_low:.2f}",
    ]

    if resistance and resistance.get("price"):
        reason.append(f"Nearest resistance {resistance['price']:.2f} (touches {resistance.get('touches', 1)})")
    if support and support.get("price"):
        reason.append(f"Nearest support {support['price']:.2f} (touches {support.get('touches', 1)})")

    confidence = _confidence_score(ema20, ema50, rsi, vol_ratio)
    if rr_to_resistance:
        confidence = int(min(100, confidence + max(0, (rr_to_resistance - 1.2) * 15)))

    return {
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "tp1": round(tp1, 4),
        "tp2": round(tp2, 4),
        "tp3": round(tp3, 4),
        "r_multiple": risk_reward,
        "confidence": confidence,
        "reason": reason,
        "levels": {
            "ema20": round(ema20, 4),
            "ema50": round(ema50, 4),
            "rsi14": round(rsi, 2),
            "prior_high": round(prior_high, 4),
            "prior_low": round(prior_low, 4),
            "vol_ratio": round(vol_ratio, 2),
            "support": support["price"] if support else None,
            "resistance": resistance["price"] if resistance else None,
            "rr_to_resistance": round(rr_to_resistance, 2) if rr_to_resistance else None,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


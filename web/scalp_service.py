"""
Scalp/Day-trade signal service.
Calculates entry, stop, and TP1 from intraday data with transparent rules.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from statistics import mean


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
    tp1 = entry + risk * risk_reward
    tp2 = entry + risk * (risk_reward + 1)  # e.g., 3R if risk_reward=2
    tp3 = entry + risk * (risk_reward + 2)  # e.g., 4R if risk_reward=2

    reason = [
        f"Trend: EMA20 ({ema20:.2f}) > EMA50 ({ema50:.2f})",
        f"Momentum: RSI(14)={rsi:.1f} (>=55)",
        f"Volume: {vols[-1]:.0f} vs 20-bar avg {vol_avg20:.0f} ({vol_ratio:.2f}x)" if vol_avg20 else "Volume check skipped",
        f"Breakout: close {last_close:.2f} > prior 20-bar high {prior_high:.2f}",
        f"Risk/Reward: {risk_reward:.1f}R, stop at prior low {prior_low:.2f}",
    ]

    confidence = _confidence_score(ema20, ema50, rsi, vol_ratio)

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
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


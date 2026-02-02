"""
Technical Analysis Helpers for Trading Application.
Provides functions for calculating technical indicators and analyzing price patterns.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import Optional
from typing import Tuple

logger = logging.getLogger(__name__)

class Trend(Enum):
    """Market trend direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class SignalStrength(Enum):
    """Signal strength indicator."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

@dataclass
class TechnicalSignal:
    """Represents a technical analysis signal."""
    indicator: str
    signal: str  # 'buy', 'sell', 'neutral'
    strength: SignalStrength
    value: float
    description: str

def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for SMA

    Returns:
        SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for EMA

    Returns:
        EMA value or None if insufficient data
    """
    if len(prices) < period:
        return None

    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period  # Start with SMA

    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema

def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index.

    Args:
        prices: List of closing prices (most recent last)
        period: RSI period (default 14)

    Returns:
        RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        return None

    # Calculate price changes
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]

    # Separate gains and losses
    gains = [change if change > 0 else 0 for change in changes]
    losses = [-change if change < 0 else 0 for change in changes]

    # Calculate average gain and loss
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)

def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Optional[Dict[str, float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices: List of closing prices (most recent last)
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)

    Returns:
        Dictionary with 'macd', 'signal', 'histogram' or None if insufficient data
    """
    if len(prices) < slow_period + signal_period:
        return None

    # Calculate EMAs for each point to get MACD line
    macd_values = []
    for i in range(slow_period - 1, len(prices)):
        subset = prices[:i+1]
        fast_ema = calculate_ema(subset, fast_period)
        slow_ema = calculate_ema(subset, slow_period)
        if fast_ema and slow_ema:
            macd_values.append(fast_ema - slow_ema)

    if len(macd_values) < signal_period:
        return None

    # Calculate signal line (EMA of MACD)
    signal_line = calculate_ema(macd_values, signal_period)

    if signal_line is None:
        return None

    macd_value = macd_values[-1]
    histogram = macd_value - signal_line

    return {
        'macd': round(macd_value, 4),
        'signal': round(signal_line, 4),
        'histogram': round(histogram, 4)
    }

def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Optional[Dict[str, float]]:
    """
    Calculate Bollinger Bands.

    Args:
        prices: List of closing prices (most recent last)
        period: SMA period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)

    Returns:
        Dictionary with 'upper', 'middle', 'lower', 'bandwidth' or None if insufficient data
    """
    if len(prices) < period:
        return None

    recent_prices = prices[-period:]
    sma = sum(recent_prices) / period

    # Calculate standard deviation
    variance = sum((p - sma) ** 2 for p in recent_prices) / period
    std = variance ** 0.5

    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    bandwidth = ((upper - lower) / sma) * 100 if sma > 0 else 0

    return {
        'upper': round(upper, 4),
        'middle': round(sma, 4),
        'lower': round(lower, 4),
        'bandwidth': round(bandwidth, 2),
        'std': round(std, 4)
    }

def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Optional[float]:
    """
    Calculate Average True Range.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period (default 14)

    Returns:
        ATR value or None if insufficient data
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        true_ranges.append(max(high_low, high_close, low_close))

    # Simple average of recent true ranges
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 4)

def calculate_stochastic(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    k_period: int = 14,
    d_period: int = 3
) -> Optional[Dict[str, float]]:
    """
    Calculate Stochastic Oscillator.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        k_period: %K period (default 14)
        d_period: %D smoothing period (default 3)

    Returns:
        Dictionary with 'k' and 'd' values or None if insufficient data
    """
    if len(highs) < k_period or len(lows) < k_period or len(closes) < k_period:
        return None

    # Calculate %K values
    k_values = []
    for i in range(k_period - 1, len(closes)):
        high_window = highs[i - k_period + 1:i + 1]
        low_window = lows[i - k_period + 1:i + 1]
        highest_high = max(high_window)
        lowest_low = min(low_window)

        if highest_high - lowest_low == 0:
            k_values.append(50)
        else:
            k = 100 * (closes[i] - lowest_low) / (highest_high - lowest_low)
            k_values.append(k)

    if len(k_values) < d_period:
        return None

    # %D is SMA of %K
    d = sum(k_values[-d_period:]) / d_period

    return {
        'k': round(k_values[-1], 2),
        'd': round(d, 2)
    }

def identify_trend(prices: List[float], short_period: int = 20, long_period: int = 50) -> Trend:
    """
    Identify market trend using moving averages.

    Args:
        prices: List of closing prices (most recent last)
        short_period: Short-term MA period
        long_period: Long-term MA period

    Returns:
        Trend enum value
    """
    short_ma = calculate_sma(prices, short_period)
    long_ma = calculate_sma(prices, long_period)

    if short_ma is None or long_ma is None:
        return Trend.NEUTRAL

    current_price = prices[-1]

    # Strong bullish: price above both MAs, short MA above long MA
    if current_price > short_ma > long_ma:
        return Trend.BULLISH

    # Strong bearish: price below both MAs, short MA below long MA
    if current_price < short_ma < long_ma:
        return Trend.BEARISH

    return Trend.NEUTRAL

def calculate_support_resistance(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = 20
) -> Dict[str, List[float]]:
    """
    Calculate potential support and resistance levels.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        lookback: Number of periods to analyze

    Returns:
        Dictionary with 'support' and 'resistance' levels
    """
    if len(highs) < lookback:
        lookback = len(highs)

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    recent_closes = closes[-lookback:]

    # Simple approach: use recent significant highs/lows
    support_levels = sorted(set(recent_lows))[:3]  # 3 lowest lows
    resistance_levels = sorted(set(recent_highs), reverse=True)[:3]  # 3 highest highs

    # Add current price levels
    current_price = closes[-1]

    # Pivot point calculation
    pivot = (recent_highs[-1] + recent_lows[-1] + recent_closes[-1]) / 3
    r1 = 2 * pivot - recent_lows[-1]
    s1 = 2 * pivot - recent_highs[-1]

    support_levels.append(round(s1, 2))
    resistance_levels.append(round(r1, 2))

    return {
        'support': sorted(set(round(s, 2) for s in support_levels)),
        'resistance': sorted(set(round(r, 2) for r in resistance_levels), reverse=True),
        'pivot': round(pivot, 2)
    }

def generate_technical_signals(
    prices: List[float],
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None
) -> List[TechnicalSignal]:
    """
    Generate technical analysis signals based on multiple indicators.

    Args:
        prices: List of closing prices (most recent last)
        highs: Optional list of high prices
        lows: Optional list of low prices

    Returns:
        List of TechnicalSignal objects
    """
    signals = []
    current_price = prices[-1]

    # RSI Signal
    rsi = calculate_rsi(prices)
    if rsi is not None:
        if rsi < 30:
            signals.append(TechnicalSignal(
                indicator='RSI',
                signal='buy',
                strength=SignalStrength.STRONG if rsi < 20 else SignalStrength.MODERATE,
                value=rsi,
                description=f"RSI is oversold at {rsi:.1f}"
            ))
        elif rsi > 70:
            signals.append(TechnicalSignal(
                indicator='RSI',
                signal='sell',
                strength=SignalStrength.STRONG if rsi > 80 else SignalStrength.MODERATE,
                value=rsi,
                description=f"RSI is overbought at {rsi:.1f}"
            ))
        else:
            signals.append(TechnicalSignal(
                indicator='RSI',
                signal='neutral',
                strength=SignalStrength.WEAK,
                value=rsi,
                description=f"RSI is neutral at {rsi:.1f}"
            ))

    # MACD Signal
    macd = calculate_macd(prices)
    if macd is not None:
        if macd['histogram'] > 0 and macd['macd'] > macd['signal']:
            signals.append(TechnicalSignal(
                indicator='MACD',
                signal='buy',
                strength=SignalStrength.MODERATE,
                value=macd['histogram'],
                description=f"MACD bullish crossover (histogram: {macd['histogram']:.4f})"
            ))
        elif macd['histogram'] < 0 and macd['macd'] < macd['signal']:
            signals.append(TechnicalSignal(
                indicator='MACD',
                signal='sell',
                strength=SignalStrength.MODERATE,
                value=macd['histogram'],
                description=f"MACD bearish crossover (histogram: {macd['histogram']:.4f})"
            ))

    # Bollinger Bands Signal
    bb = calculate_bollinger_bands(prices)
    if bb is not None:
        if current_price < bb['lower']:
            signals.append(TechnicalSignal(
                indicator='Bollinger Bands',
                signal='buy',
                strength=SignalStrength.MODERATE,
                value=current_price,
                description=f"Price below lower band ({bb['lower']:.2f})"
            ))
        elif current_price > bb['upper']:
            signals.append(TechnicalSignal(
                indicator='Bollinger Bands',
                signal='sell',
                strength=SignalStrength.MODERATE,
                value=current_price,
                description=f"Price above upper band ({bb['upper']:.2f})"
            ))

    # Moving Average Signal
    sma_20 = calculate_sma(prices, 20)
    sma_50 = calculate_sma(prices, 50)
    if sma_20 and sma_50:
        if current_price > sma_20 > sma_50:
            signals.append(TechnicalSignal(
                indicator='Moving Averages',
                signal='buy',
                strength=SignalStrength.STRONG,
                value=current_price,
                description=f"Price above 20 SMA ({sma_20:.2f}) and 50 SMA ({sma_50:.2f})"
            ))
        elif current_price < sma_20 < sma_50:
            signals.append(TechnicalSignal(
                indicator='Moving Averages',
                signal='sell',
                strength=SignalStrength.STRONG,
                value=current_price,
                description=f"Price below 20 SMA ({sma_20:.2f}) and 50 SMA ({sma_50:.2f})"
            ))

    return signals

def get_signal_summary(signals: List[TechnicalSignal]) -> Dict[str, any]:
    """
    Summarize technical signals into an overall recommendation.

    Args:
        signals: List of TechnicalSignal objects

    Returns:
        Dictionary with summary information
    """
    if not signals:
        return {
            'recommendation': 'neutral',
            'strength': 'weak',
            'buy_signals': 0,
            'sell_signals': 0,
            'neutral_signals': 0,
            'confidence': 0
        }

    buy_count = sum(1 for s in signals if s.signal == 'buy')
    sell_count = sum(1 for s in signals if s.signal == 'sell')
    neutral_count = sum(1 for s in signals if s.signal == 'neutral')

    # Calculate weighted score
    score = 0
    for signal in signals:
        weight = {'strong': 3, 'moderate': 2, 'weak': 1}[signal.strength.value]
        if signal.signal == 'buy':
            score += weight
        elif signal.signal == 'sell':
            score -= weight

    total_signals = len(signals)
    max_score = total_signals * 3

    if score > 2:
        recommendation = 'buy'
    elif score < -2:
        recommendation = 'sell'
    else:
        recommendation = 'neutral'

    # Confidence based on agreement between signals
    agreement = max(buy_count, sell_count, neutral_count) / total_signals
    confidence = round(agreement * 100, 1)

    # Determine overall strength
    if abs(score) >= max_score * 0.7:
        strength = 'strong'
    elif abs(score) >= max_score * 0.4:
        strength = 'moderate'
    else:
        strength = 'weak'

    return {
        'recommendation': recommendation,
        'strength': strength,
        'buy_signals': buy_count,
        'sell_signals': sell_count,
        'neutral_signals': neutral_count,
        'score': score,
        'confidence': confidence
    }

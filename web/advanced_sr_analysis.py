"""
Advanced Support/Resistance Analysis Module
Day Trading AI Enhancement - Experience-Based S/R Detection

Features:
1. Multi-Timeframe Confluence S/R
2. Volume Profile / VPOC (Point of Control)
3. ML-based S/R Bounce Prediction
4. Real-time Alert System

Author: AI Trading System
"""

import os
import logging

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import requests
from datetime import timedelta
import json
from typing import List
from typing import Optional
from typing import Tuple

logger = logging.getLogger(__name__)

class MultiTimeframeSR:
    """
    Multi-Timeframe Support/Resistance Confluence Analyzer

    Key Principle: S/R levels that appear on MULTIPLE timeframes are STRONGER
    - 5분, 15분, 1시간 차트에서 모두 지지선 = 매우 강력한 지지

    Confluence Scoring:
    - Single timeframe: Base strength
    - Two timeframes align: 1.5x strength
    - Three+ timeframes align: 2x strength (VERY STRONG)
    """

    TIMEFRAMES = {
        "5": {"name": "5분", "weight": 1.0, "minutes": 5},
        "15": {"name": "15분", "weight": 1.5, "minutes": 15},
        "60": {"name": "1시간", "weight": 2.0, "minutes": 60},
        "240": {"name": "4시간", "weight": 2.5, "minutes": 240},
    }

    # Tolerance for level matching (% difference allowed)
    LEVEL_TOLERANCE = 0.005  # 0.5%

    def __init__(self, polygon_key: str = None):
        self.polygon_key = polygon_key or os.getenv("POLYGON_API_KEY")

    def fetch_multi_timeframe_data(
        self,
        ticker: str,
        timeframes: List[str] = ["5", "15", "60"]
    ) -> Dict[str, List[Dict]]:
        """Fetch candlestick data for multiple timeframes"""
        data = {}

        for tf in timeframes:
            bars = self._fetch_bars(ticker, tf)
            if bars:
                data[tf] = bars
                logger.info(f"[MTF] Fetched {len(bars)} bars for {ticker} @ {tf}m")
            else:
                logger.warning(f"[MTF] Failed to fetch {ticker} @ {tf}m")

        return data

    def _fetch_bars(self, ticker: str, interval: str, limit: int = 100) -> List[Dict]:
        """Fetch bars from Polygon or Binance"""
        try:
            # Check if crypto
            if self._is_crypto(ticker):
                return self._fetch_binance(ticker, interval, limit)
            else:
                return self._fetch_polygon(ticker, interval, limit)
        except Exception as e:
            logger.error(f"[MTF] Error fetching {ticker}: {e}")
            return []

    def _is_crypto(self, ticker: str) -> bool:
        """Check if ticker is crypto pair"""
        crypto_patterns = ["USDT", "BUSD", "BTC", "ETH", "BNB"]
        return any(ticker.upper().endswith(p) for p in crypto_patterns)

    def _fetch_polygon(self, ticker: str, interval: str, limit: int) -> List[Dict]:
        """Fetch from Polygon.io"""
        try:
            timespan_map = {"5": "minute", "15": "minute", "60": "hour", "240": "hour"}
            multiplier_map = {"5": 5, "15": 15, "60": 1, "240": 4}

            timespan = timespan_map.get(interval, "minute")
            multiplier = multiplier_map.get(interval, 5)

            # Need more days for higher timeframes
            days_needed = max(3, int(interval) * limit // (60 * 6))
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_needed)

            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {"apiKey": self.polygon_key, "limit": limit, "sort": "desc"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("resultsCount", 0) > 0:
                return list(reversed(data.get("results", [])))
            return []
        except Exception as e:
            logger.error(f"[MTF] Polygon error: {e}")
            return []

    def _fetch_binance(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """Fetch from Binance"""
        try:
            interval_map = {"5": "5m", "15": "15m", "60": "1h", "240": "4h"}
            binance_interval = interval_map.get(interval, "5m")

            endpoints = [
                "https://api.binance.us/api/v3/klines",
                "https://api.binance.com/api/v3/klines",
            ]

            for url in endpoints:
                try:
                    params = {"symbol": symbol.upper(), "interval": binance_interval, "limit": limit}
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code == 451:  # Geo-restricted
                        continue

                    response.raise_for_status()
                    data = response.json()

                    bars = []
                    for kline in data:
                        bars.append({
                            "t": kline[0],
                            "o": float(kline[1]),
                            "h": float(kline[2]),
                            "l": float(kline[3]),
                            "c": float(kline[4]),
                            "v": float(kline[5]),
                        })
                    return bars
                except Exception:
                    continue

            return []
        except Exception as e:
            logger.error(f"[MTF] Binance error: {e}")
            return []

    def find_swing_points(self, bars: List[Dict], lookback: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """Find swing highs and lows"""
        if len(bars) < lookback * 2 + 1:
            return [], []

        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(bars) - lookback):
            high = bars[i].get("h", 0)
            low = bars[i].get("l", 0)

            # Check swing high
            is_swing_high = all(
                high > bars[i - j].get("h", 0) and high > bars[i + j].get("h", 0)
                for j in range(1, lookback + 1)
            )
            if is_swing_high:
                swing_highs.append({"price": high, "index": i, "bar": bars[i]})

            # Check swing low
            is_swing_low = all(
                low < bars[i - j].get("l", float("inf")) and low < bars[i + j].get("l", float("inf"))
                for j in range(1, lookback + 1)
            )
            if is_swing_low:
                swing_lows.append({"price": low, "index": i, "bar": bars[i]})

        return swing_highs, swing_lows

    def analyze_multi_timeframe(
        self,
        ticker: str,
        timeframes: List[str] = ["5", "15", "60"]
    ) -> Dict:
        """
        Analyze S/R across multiple timeframes and find confluence zones

        Returns:
            Dict with:
            - confluence_supports: List of support levels with MTF confluence
            - confluence_resistances: List of resistance levels with MTF confluence
            - current_price: Current price
            - strongest_support: Strongest support level
            - strongest_resistance: Strongest resistance level
        """
        # Fetch data for all timeframes
        mtf_data = self.fetch_multi_timeframe_data(ticker, timeframes)

        if not mtf_data:
            return {"error": "Failed to fetch multi-timeframe data"}

        # Get current price from lowest timeframe
        lowest_tf = min(timeframes, key=lambda x: int(x))
        current_price = mtf_data[lowest_tf][-1]["c"] if mtf_data.get(lowest_tf) else 0

        # Collect S/R from each timeframe
        all_supports = []  # [(price, timeframe, weight)]
        all_resistances = []

        for tf, bars in mtf_data.items():
            weight = self.TIMEFRAMES.get(tf, {}).get("weight", 1.0)
            swing_highs, swing_lows = self.find_swing_points(bars)

            for sh in swing_highs:
                all_resistances.append({
                    "price": sh["price"],
                    "timeframe": tf,
                    "weight": weight,
                    "tf_name": self.TIMEFRAMES.get(tf, {}).get("name", tf),
                })

            for sl in swing_lows:
                all_supports.append({
                    "price": sl["price"],
                    "timeframe": tf,
                    "weight": weight,
                    "tf_name": self.TIMEFRAMES.get(tf, {}).get("name", tf),
                })

        # Find confluence zones (levels that appear in multiple timeframes)
        confluence_supports = self._find_confluence_zones(all_supports, current_price)
        confluence_resistances = self._find_confluence_zones(all_resistances, current_price)

        # Sort by strength
        confluence_supports.sort(key=lambda x: x["strength"], reverse=True)
        confluence_resistances.sort(key=lambda x: x["strength"], reverse=True)

        # Find nearest levels
        nearest_support = None
        nearest_resistance = None

        for s in confluence_supports:
            if s["price"] < current_price:
                if nearest_support is None or s["price"] > nearest_support["price"]:
                    nearest_support = s

        for r in confluence_resistances:
            if r["price"] > current_price:
                if nearest_resistance is None or r["price"] < nearest_resistance["price"]:
                    nearest_resistance = r

        return {
            "confluence_supports": confluence_supports[:10],  # Top 10
            "confluence_resistances": confluence_resistances[:10],
            "current_price": current_price,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "strongest_support": confluence_supports[0] if confluence_supports else None,
            "strongest_resistance": confluence_resistances[0] if confluence_resistances else None,
            "timeframes_analyzed": list(mtf_data.keys()),
        }

    def _find_confluence_zones(
        self,
        levels: List[Dict],
        current_price: float
    ) -> List[Dict]:
        """
        Group nearby levels into confluence zones

        Confluence zones are stronger because multiple timeframes agree
        """
        if not levels:
            return []

        # Sort by price
        levels.sort(key=lambda x: x["price"])

        # Group levels within tolerance
        zones = []
        current_zone = [levels[0]]

        for level in levels[1:]:
            # Check if this level is close to the current zone
            zone_avg = sum(l["price"] for l in current_zone) / len(current_zone)

            if abs(level["price"] - zone_avg) / zone_avg < self.LEVEL_TOLERANCE:
                current_zone.append(level)
            else:
                # Finalize current zone
                zones.append(self._create_confluence_zone(current_zone, current_price))
                current_zone = [level]

        # Don't forget last zone
        if current_zone:
            zones.append(self._create_confluence_zone(current_zone, current_price))

        return zones

    def _create_confluence_zone(
        self,
        levels: List[Dict],
        current_price: float
    ) -> Dict:
        """Create a confluence zone from grouped levels"""
        avg_price = sum(l["price"] for l in levels) / len(levels)
        total_weight = sum(l["weight"] for l in levels)
        timeframes = list(set(l["timeframe"] for l in levels))
        tf_names = list(set(l["tf_name"] for l in levels))

        # Confluence multiplier
        if len(timeframes) >= 3:
            confluence_mult = 2.0
            confluence_label = "🔥 VERY STRONG"
        elif len(timeframes) == 2:
            confluence_mult = 1.5
            confluence_label = "⭐ STRONG"
        else:
            confluence_mult = 1.0
            confluence_label = "NORMAL"

        # Calculate strength (0-100)
        base_strength = min(100, total_weight * 20)
        final_strength = min(100, base_strength * confluence_mult)

        # Distance from current price
        distance_pct = abs(avg_price - current_price) / current_price * 100

        return {
            "price": round(avg_price, 4),
            "strength": round(final_strength, 1),
            "timeframes": timeframes,
            "tf_names": tf_names,
            "confluence_count": len(timeframes),
            "touch_count": len(levels),
            "confluence_label": confluence_label,
            "distance_percent": round(distance_pct, 2),
            "total_weight": round(total_weight, 2),
        }

class VolumeProfileAnalyzer:
    """
    Volume Profile / VPOC (Volume Point of Control) Analyzer

    Key Concepts:
    - Volume Profile: Histogram of volume traded at each price level
    - VPOC: Price level with the highest traded volume (institutional interest)
    - High Volume Node (HVN): Price levels with significant volume = S/R zones
    - Low Volume Node (LVN): Price levels with low volume = Fast price movement zones

    Trading Application:
    - VPOC acts as magnet (price tends to return to it)
    - HVN = Strong S/R zones
    - LVN = Price moves quickly through these zones
    """

    def __init__(self, num_bins: int = 50):
        self.num_bins = num_bins

    def calculate_volume_profile(self, bars: List[Dict]) -> Dict:
        """
        Calculate Volume Profile from OHLCV data

        Uses typical price (HLC/3) weighted by volume for each candle
        """
        if not bars or len(bars) < 10:
            return {"error": "Insufficient data for volume profile"}

        # Find price range
        all_highs = [b.get("h", 0) for b in bars]
        all_lows = [b.get("l", 0) for b in bars]
        price_min = min(all_lows)
        price_max = max(all_highs)

        if price_min >= price_max:
            return {"error": "Invalid price range"}

        # Create price bins
        bin_size = (price_max - price_min) / self.num_bins
        volume_at_price = defaultdict(float)

        for bar in bars:
            h, l, c, v = bar.get("h", 0), bar.get("l", 0), bar.get("c", 0), bar.get("v", 0)

            # Distribute volume across the candle's price range
            # More accurate than just using typical price
            candle_bins = []
            for i in range(self.num_bins):
                bin_low = price_min + i * bin_size
                bin_high = bin_low + bin_size
                bin_mid = (bin_low + bin_high) / 2

                # Check if this bin overlaps with candle range
                if bin_low <= h and bin_high >= l:
                    candle_bins.append(bin_mid)

            # Distribute volume evenly across touched bins
            if candle_bins:
                vol_per_bin = v / len(candle_bins)
                for bin_price in candle_bins:
                    volume_at_price[round(bin_price, 4)] += vol_per_bin

        # Convert to sorted list
        profile = sorted(
            [{"price": p, "volume": v} for p, v in volume_at_price.items()],
            key=lambda x: x["price"]
        )

        # Calculate statistics
        total_volume = sum(p["volume"] for p in profile)
        max_volume = max(p["volume"] for p in profile) if profile else 0

        # Find VPOC (Volume Point of Control)
        vpoc = max(profile, key=lambda x: x["volume"]) if profile else None

        # Find Value Area (70% of volume)
        value_area = self._calculate_value_area(profile, total_volume)

        # Find High Volume Nodes (above average)
        avg_volume = total_volume / len(profile) if profile else 0
        hvn_threshold = avg_volume * 1.5
        lvn_threshold = avg_volume * 0.5

        hvn = [p for p in profile if p["volume"] >= hvn_threshold]
        lvn = [p for p in profile if p["volume"] <= lvn_threshold]

        # Current price context
        current_price = bars[-1].get("c", 0)

        return {
            "vpoc": {
                "price": vpoc["price"] if vpoc else None,
                "volume": vpoc["volume"] if vpoc else 0,
                "distance_percent": abs(current_price - vpoc["price"]) / current_price * 100 if vpoc else 0,
            },
            "value_area": {
                "high": value_area["vah"],
                "low": value_area["val"],
                "volume_percent": 70,
            },
            "high_volume_nodes": [
                {"price": h["price"], "volume": h["volume"], "strength": min(100, h["volume"] / max_volume * 100)}
                for h in sorted(hvn, key=lambda x: x["volume"], reverse=True)[:5]
            ],
            "low_volume_nodes": [
                {"price": l["price"], "volume": l["volume"]}
                for l in sorted(lvn, key=lambda x: x["price"])[:5]
            ],
            "current_price": current_price,
            "price_range": {"min": price_min, "max": price_max},
            "total_volume": total_volume,
            "profile": profile,  # Full profile for visualization
        }

    def _calculate_value_area(
        self,
        profile: List[Dict],
        total_volume: float
    ) -> Dict:
        """
        Calculate Value Area (VA) - price range containing 70% of volume

        Standard method: Start from POC, add bars alternately above/below
        """
        if not profile or total_volume == 0:
            return {"vah": 0, "val": 0}

        # Find POC index
        poc_idx = max(range(len(profile)), key=lambda i: profile[i]["volume"])

        target_volume = total_volume * 0.7
        accumulated_volume = profile[poc_idx]["volume"]

        lower_idx = poc_idx - 1
        upper_idx = poc_idx + 1

        while accumulated_volume < target_volume:
            lower_vol = profile[lower_idx]["volume"] if lower_idx >= 0 else 0
            upper_vol = profile[upper_idx]["volume"] if upper_idx < len(profile) else 0

            if lower_vol == 0 and upper_vol == 0:
                break

            if lower_vol >= upper_vol and lower_idx >= 0:
                accumulated_volume += lower_vol
                lower_idx -= 1
            elif upper_idx < len(profile):
                accumulated_volume += upper_vol
                upper_idx += 1
            else:
                break

        val = profile[max(0, lower_idx + 1)]["price"]
        vah = profile[min(len(profile) - 1, upper_idx - 1)]["price"]

        return {"val": val, "vah": vah}

    def get_sr_from_volume_profile(self, bars: List[Dict]) -> Dict:
        """
        Extract support/resistance levels from volume profile

        HVN = Support/Resistance zones (high institutional interest)
        """
        profile_data = self.calculate_volume_profile(bars)

        if "error" in profile_data:
            return profile_data

        current_price = profile_data["current_price"]
        hvn = profile_data["high_volume_nodes"]
        vpoc = profile_data["vpoc"]
        va = profile_data["value_area"]

        # Supports: HVN below current price + VAL + VPOC if below
        supports = []
        resistances = []

        for node in hvn:
            level = {
                "price": node["price"],
                "strength": node["strength"],
                "type": "HVN",
                "label": "High Volume Node (거래량 집중 구간)",
            }
            if node["price"] < current_price:
                supports.append(level)
            else:
                resistances.append(level)

        # Add VPOC
        if vpoc["price"]:
            vpoc_level = {
                "price": vpoc["price"],
                "strength": 90,  # VPOC is always important
                "type": "VPOC",
                "label": "Volume Point of Control (기관 관심 가격)",
            }
            if vpoc["price"] < current_price:
                supports.append(vpoc_level)
            else:
                resistances.append(vpoc_level)

        # Add Value Area boundaries
        val_price = va.get("low") or va.get("val")
        vah_price = va.get("high") or va.get("vah")

        if val_price and val_price < current_price:
            supports.append({
                "price": val_price,
                "strength": 75,
                "type": "VAL",
                "label": "Value Area Low (70% 거래량 하단)",
            })

        if vah_price and vah_price > current_price:
            resistances.append({
                "price": vah_price,
                "strength": 75,
                "type": "VAH",
                "label": "Value Area High (70% 거래량 상단)",
            })

        # Sort by proximity to current price
        supports.sort(key=lambda x: current_price - x["price"])
        resistances.sort(key=lambda x: x["price"] - current_price)

        return {
            "supports": supports[:5],
            "resistances": resistances[:5],
            "vpoc": vpoc,
            "value_area": va,
            "current_price": current_price,
        }

class SRBouncePredictor:
    """
    ML-based Support/Resistance Bounce Prediction

    Predicts probability of price bouncing at S/R levels based on:
    - Historical bounce rate at similar levels
    - Volume at the level
    - Trend context
    - Time since level was established
    - Number of previous touches

    Uses simple statistical model (no heavy ML libraries required)
    For production, can upgrade to XGBoost or similar
    """

    def __init__(self):
        # Historical bounce statistics (can be trained on real data)
        # Format: {feature_combo: (bounce_rate, sample_count)}
        self.bounce_stats = {}
        self.min_samples = 10  # Minimum samples for reliable prediction

    def calculate_bounce_probability(
        self,
        level_info: Dict,
        bars: List[Dict],
        volume_profile: Dict = None
    ) -> Dict:
        """
        Calculate probability of bounce at an S/R level

        Factors considered:
        1. Touch count (more touches = stronger level)
        2. Confluence count (multi-timeframe = stronger)
        3. Volume at level (high volume = stronger)
        4. Trend alignment (counter-trend bounces are weaker)
        5. Distance from current price
        6. Time since last touch
        """
        if not level_info or not bars:
            return {"probability": 50, "confidence": "low", "factors": []}

        factors = []
        probability = 50  # Start at neutral

        # Factor 1: Touch Count (more touches = higher probability)
        touch_count = level_info.get("touch_count", 1)
        if touch_count >= 4:
            probability += 15
            factors.append(f"✅ {touch_count}회 터치 - 강한 레벨 (+15%)")
        elif touch_count >= 2:
            probability += 8
            factors.append(f"📊 {touch_count}회 터치 (+8%)")
        else:
            factors.append(f"⚠️ {touch_count}회 터치 - 검증 필요")

        # Factor 2: Multi-Timeframe Confluence
        confluence_count = level_info.get("confluence_count", 1)
        if confluence_count >= 3:
            probability += 20
            factors.append(f"🔥 {confluence_count}개 타임프레임 일치 (+20%)")
        elif confluence_count == 2:
            probability += 12
            factors.append(f"⭐ {confluence_count}개 타임프레임 일치 (+12%)")
        else:
            factors.append("📉 단일 타임프레임")

        # Factor 3: Volume at Level (if volume profile available)
        if volume_profile:
            level_price = level_info.get("price", 0)
            hvn = volume_profile.get("high_volume_nodes", [])

            # Check if level is near a high volume node
            for node in hvn:
                if abs(node["price"] - level_price) / level_price < 0.005:
                    prob_add = min(15, node["strength"] * 0.15)
                    probability += prob_add
                    factors.append(f"💰 거래량 집중 구간 (+{prob_add:.0f}%)")
                    break

        # Factor 4: Trend Alignment
        if len(bars) >= 20:
            sma20 = sum(b["c"] for b in bars[-20:]) / 20
            current_price = bars[-1]["c"]
            level_price = level_info.get("price", 0)

            is_uptrend = current_price > sma20
            is_support = level_price < current_price

            # Bounces are more likely when aligned with trend
            if (is_uptrend and is_support) or (not is_uptrend and not is_support):
                probability += 10
                trend_dir = "상승" if is_uptrend else "하락"
                factors.append(f"📈 {trend_dir}추세와 일치 (+10%)")
            else:
                probability -= 5
                factors.append("⚠️ 추세 역행 (-5%)")

        # Factor 5: Strength Score
        strength = level_info.get("strength", 50)
        if strength >= 80:
            probability += 10
            factors.append(f"💪 강도 {strength:.0f}% (+10%)")
        elif strength >= 60:
            probability += 5
            factors.append(f"📊 강도 {strength:.0f}% (+5%)")

        # Factor 6: Recent price action at level
        level_price = level_info.get("price", 0)
        if level_price and len(bars) >= 10:
            recent_touches = 0
            for bar in bars[-10:]:
                if abs(bar["l"] - level_price) / level_price < 0.003 or \
                   abs(bar["h"] - level_price) / level_price < 0.003:
                    recent_touches += 1

            if recent_touches >= 2:
                probability += 8
                factors.append(f"🎯 최근 {recent_touches}회 근접 - 활성 레벨 (+8%)")

        # Cap probability
        probability = max(20, min(95, probability))

        # Determine confidence
        if probability >= 75:
            confidence = "high"
            label = "🟢 높은 반등 확률"
        elif probability >= 60:
            confidence = "medium"
            label = "🟡 중간 반등 확률"
        else:
            confidence = "low"
            label = "🔴 낮은 반등 확률"

        return {
            "probability": round(probability, 1),
            "confidence": confidence,
            "label": label,
            "factors": factors,
            "level_info": level_info,
        }

    def analyze_all_levels(
        self,
        supports: List[Dict],
        resistances: List[Dict],
        bars: List[Dict],
        volume_profile: Dict = None
    ) -> Dict:
        """
        Analyze bounce probability for all S/R levels
        """
        support_analysis = []
        resistance_analysis = []

        for s in supports[:5]:  # Top 5
            analysis = self.calculate_bounce_probability(s, bars, volume_profile)
            support_analysis.append(analysis)

        for r in resistances[:5]:
            analysis = self.calculate_bounce_probability(r, bars, volume_profile)
            resistance_analysis.append(analysis)

        # Sort by probability
        support_analysis.sort(key=lambda x: x["probability"], reverse=True)
        resistance_analysis.sort(key=lambda x: x["probability"], reverse=True)

        return {
            "supports": support_analysis,
            "resistances": resistance_analysis,
            "best_support": support_analysis[0] if support_analysis else None,
            "best_resistance": resistance_analysis[0] if resistance_analysis else None,
        }

class PriceAlertManager:
    """
    Real-time Price Alert System

    Alert Types:
    1. Price approaching S/R level (within X%)
    2. Price touched S/R level
    3. Price broke through S/R level
    4. Volume spike at S/R level
    5. Entry signal generated

    Storage: In-memory for now, can be persisted to DB
    """

    def __init__(self):
        # Active alerts: {ticker: [alert_configs]}
        self.active_alerts = defaultdict(list)

        # Triggered alerts history
        self.triggered_history = []

        # Alert thresholds
        self.approach_threshold = 0.5  # 0.5% from level = "approaching"
        self.touch_threshold = 0.1  # 0.1% = "touched"

    def create_sr_alerts(
        self,
        ticker: str,
        supports: List[Dict],
        resistances: List[Dict],
        current_price: float
    ) -> List[Dict]:
        """
        Create alerts for S/R levels

        Returns list of created alerts
        """
        alerts = []

        # Support alerts (for potential longs)
        for s in supports[:3]:  # Top 3 supports
            level_price = s.get("price", 0)
            strength = s.get("strength", 50)

            if level_price <= 0:
                continue

            # Approaching alert
            approach_price = level_price * (1 + self.approach_threshold / 100)
            alerts.append({
                "ticker": ticker,
                "type": "approach_support",
                "level_price": level_price,
                "trigger_price": approach_price,
                "direction": "below",  # Trigger when price goes below
                "strength": strength,
                "message": f"📉 {ticker} approaching support ${level_price:.2f}",
                "action": "Prepare for potential LONG entry",
                "created_at": datetime.now().isoformat(),
            })

            # Touch alert
            touch_price = level_price * (1 + self.touch_threshold / 100)
            alerts.append({
                "ticker": ticker,
                "type": "touch_support",
                "level_price": level_price,
                "trigger_price": touch_price,
                "direction": "below",
                "strength": strength,
                "message": f"🎯 {ticker} touched support ${level_price:.2f}!",
                "action": "Look for bullish confirmation pattern",
                "created_at": datetime.now().isoformat(),
            })

        # Resistance alerts (for potential shorts or exits)
        for r in resistances[:3]:
            level_price = r.get("price", 0)
            strength = r.get("strength", 50)

            if level_price <= 0:
                continue

            # Approaching alert
            approach_price = level_price * (1 - self.approach_threshold / 100)
            alerts.append({
                "ticker": ticker,
                "type": "approach_resistance",
                "level_price": level_price,
                "trigger_price": approach_price,
                "direction": "above",
                "strength": strength,
                "message": f"📈 {ticker} approaching resistance ${level_price:.2f}",
                "action": "Consider taking profits or prepare for SHORT",
                "created_at": datetime.now().isoformat(),
            })

            # Touch alert
            touch_price = level_price * (1 - self.touch_threshold / 100)
            alerts.append({
                "ticker": ticker,
                "type": "touch_resistance",
                "level_price": level_price,
                "trigger_price": touch_price,
                "direction": "above",
                "strength": strength,
                "message": f"🎯 {ticker} touched resistance ${level_price:.2f}!",
                "action": "Look for bearish rejection pattern",
                "created_at": datetime.now().isoformat(),
            })

        # Store alerts
        self.active_alerts[ticker] = alerts

        return alerts

    def check_alerts(
        self,
        ticker: str,
        current_price: float,
        prev_price: float = None
    ) -> List[Dict]:
        """
        Check if any alerts have been triggered

        Returns list of triggered alerts
        """
        if ticker not in self.active_alerts:
            return []

        triggered = []
        remaining = []

        for alert in self.active_alerts[ticker]:
            trigger_price = alert.get("trigger_price", 0)
            direction = alert.get("direction", "below")

            is_triggered = False

            if direction == "below" and current_price <= trigger_price:
                is_triggered = True
            elif direction == "above" and current_price >= trigger_price:
                is_triggered = True

            if is_triggered:
                alert["triggered_at"] = datetime.now().isoformat()
                alert["triggered_price"] = current_price
                triggered.append(alert)
                self.triggered_history.append(alert)
            else:
                remaining.append(alert)

        # Update active alerts
        self.active_alerts[ticker] = remaining

        return triggered

    def get_active_alerts(self, ticker: str = None) -> Dict:
        """Get all active alerts, optionally filtered by ticker"""
        if ticker:
            return {
                "ticker": ticker,
                "alerts": self.active_alerts.get(ticker, []),
                "count": len(self.active_alerts.get(ticker, [])),
            }

        all_alerts = []
        for t, alerts in self.active_alerts.items():
            for a in alerts:
                all_alerts.append(a)

        return {
            "alerts": all_alerts,
            "count": len(all_alerts),
            "tickers": list(self.active_alerts.keys()),
        }

    def clear_alerts(self, ticker: str = None) -> Dict:
        """Clear alerts for a ticker or all tickers"""
        if ticker:
            count = len(self.active_alerts.get(ticker, []))
            self.active_alerts[ticker] = []
            return {"cleared": count, "ticker": ticker}

        total = sum(len(alerts) for alerts in self.active_alerts.values())
        self.active_alerts.clear()
        return {"cleared": total, "ticker": "all"}

class AdvancedSRAnalyzer:
    """
    Main class combining all advanced S/R analysis features

    Integrates:
    1. Multi-Timeframe Confluence
    2. Volume Profile
    3. ML Bounce Prediction
    4. Alert System
    """

    def __init__(self):
        self.mtf_analyzer = MultiTimeframeSR()
        self.volume_analyzer = VolumeProfileAnalyzer()
        self.bounce_predictor = SRBouncePredictor()
        self.alert_manager = PriceAlertManager()

    def full_analysis(
        self,
        ticker: str,
        timeframes: List[str] = ["5", "15", "60"],
        create_alerts: bool = True
    ) -> Dict:
        """
        Perform complete advanced S/R analysis

        Returns comprehensive analysis with all features
        """
        try:
            ticker = ticker.upper().strip()

            # 1. Multi-Timeframe Analysis
            mtf_result = self.mtf_analyzer.analyze_multi_timeframe(ticker, timeframes)

            if "error" in mtf_result:
                return {"error": mtf_result["error"]}

            current_price = mtf_result["current_price"]

            # 2. Volume Profile (using lowest timeframe data)
            lowest_tf = min(timeframes, key=lambda x: int(x))
            bars = self.mtf_analyzer._fetch_bars(ticker, lowest_tf, limit=100)

            volume_profile = None
            volume_sr = None
            if bars:
                volume_profile = self.volume_analyzer.calculate_volume_profile(bars)
                volume_sr = self.volume_analyzer.get_sr_from_volume_profile(bars)

            # 3. Combine S/R from MTF and Volume Profile
            all_supports = mtf_result.get("confluence_supports", [])
            all_resistances = mtf_result.get("confluence_resistances", [])

            if volume_sr:
                # Add volume-based S/R with appropriate labeling
                for vs in volume_sr.get("supports", []):
                    vs["source"] = "volume_profile"
                    all_supports.append(vs)

                for vr in volume_sr.get("resistances", []):
                    vr["source"] = "volume_profile"
                    all_resistances.append(vr)

            # Sort by strength
            all_supports.sort(key=lambda x: x.get("strength", 0), reverse=True)
            all_resistances.sort(key=lambda x: x.get("strength", 0), reverse=True)

            # 4. Bounce Probability Analysis
            bounce_analysis = self.bounce_predictor.analyze_all_levels(
                all_supports[:5],
                all_resistances[:5],
                bars,
                volume_profile
            )

            # 5. Create Alerts (if requested)
            alerts = []
            if create_alerts:
                alerts = self.alert_manager.create_sr_alerts(
                    ticker,
                    all_supports[:5],
                    all_resistances[:5],
                    current_price
                )

            # 6. Generate Trading Recommendation
            recommendation = self._generate_recommendation(
                current_price,
                bounce_analysis,
                volume_profile,
                mtf_result
            )

            return {
                "ticker": ticker,
                "current_price": current_price,
                "timestamp": datetime.now().isoformat(),

                # Multi-Timeframe S/R
                "mtf_analysis": {
                    "timeframes": mtf_result["timeframes_analyzed"],
                    "nearest_support": mtf_result.get("nearest_support"),
                    "nearest_resistance": mtf_result.get("nearest_resistance"),
                    "strongest_support": mtf_result.get("strongest_support"),
                    "strongest_resistance": mtf_result.get("strongest_resistance"),
                },

                # All S/R Levels (combined from MTF + Volume Profile)
                "supports": all_supports[:10],
                "resistances": all_resistances[:10],

                # Volume Profile
                "volume_profile": {
                    "vpoc": volume_profile.get("vpoc") if volume_profile else None,
                    "value_area": volume_profile.get("value_area") if volume_profile else None,
                    "high_volume_nodes": volume_profile.get("high_volume_nodes", [])[:3] if volume_profile else [],
                },

                # Bounce Predictions
                "bounce_predictions": {
                    "best_support": bounce_analysis.get("best_support"),
                    "best_resistance": bounce_analysis.get("best_resistance"),
                    "all_supports": bounce_analysis.get("supports", []),
                    "all_resistances": bounce_analysis.get("resistances", []),
                },

                # Alerts
                "alerts": {
                    "created": len(alerts),
                    "active": alerts[:5],
                },

                # Trading Recommendation
                "recommendation": recommendation,
            }

        except Exception as e:
            logger.error(f"[AdvancedSR] Error analyzing {ticker}: {e}", exc_info=True)
            return {"error": str(e)}

    def _generate_recommendation(
        self,
        current_price: float,
        bounce_analysis: Dict,
        volume_profile: Dict,
        mtf_result: Dict
    ) -> Dict:
        """Generate trading recommendation based on all analysis"""

        recommendations = []

        # Check if near strong support
        best_support = bounce_analysis.get("best_support")
        if best_support:
            support_price = best_support.get("level_info", {}).get("price", 0)
            support_prob = best_support.get("probability", 0)

            if support_price:
                distance_pct = (current_price - support_price) / current_price * 100

                if distance_pct < 1.0 and support_prob >= 65:
                    recommendations.append({
                        "action": "LONG",
                        "reason": f"Price near strong support ${support_price:.2f} ({support_prob}% bounce probability)",
                        "entry": support_price,
                        "stop": support_price * 0.99,
                        "target": current_price + (current_price - support_price * 0.99) * 2,
                        "priority": "HIGH" if support_prob >= 75 else "MEDIUM",
                    })

        # Check if near strong resistance
        best_resistance = bounce_analysis.get("best_resistance")
        if best_resistance:
            resistance_price = best_resistance.get("level_info", {}).get("price", 0)
            resistance_prob = best_resistance.get("probability", 0)

            if resistance_price:
                distance_pct = (resistance_price - current_price) / current_price * 100

                if distance_pct < 1.0 and resistance_prob >= 65:
                    recommendations.append({
                        "action": "SHORT or TAKE_PROFIT",
                        "reason": f"Price near strong resistance ${resistance_price:.2f} ({resistance_prob}% rejection probability)",
                        "entry": resistance_price,
                        "stop": resistance_price * 1.01,
                        "target": current_price - (resistance_price * 1.01 - current_price) * 2,
                        "priority": "HIGH" if resistance_prob >= 75 else "MEDIUM",
                    })

        # Check VPOC context
        if volume_profile and volume_profile.get("vpoc"):
            vpoc_price = volume_profile["vpoc"].get("price", 0)
            if vpoc_price:
                vpoc_distance = abs(current_price - vpoc_price) / current_price * 100

                if vpoc_distance > 2.0:
                    direction = "above" if current_price > vpoc_price else "below"
                    recommendations.append({
                        "action": "WATCH",
                        "reason": f"Price {vpoc_distance:.1f}% {direction} VPOC ${vpoc_price:.2f} - may return to POC",
                        "priority": "LOW",
                    })

        if not recommendations:
            recommendations.append({
                "action": "WAIT",
                "reason": "No clear setup - wait for price to approach key S/R levels",
                "priority": "NONE",
            })

        return {
            "primary": recommendations[0] if recommendations else None,
            "all_recommendations": recommendations,
        }

# Singleton instance
_advanced_sr_analyzer = None

def get_advanced_sr_analyzer() -> AdvancedSRAnalyzer:
    """Get or create AdvancedSRAnalyzer singleton"""
    global _advanced_sr_analyzer
    if _advanced_sr_analyzer is None:
        _advanced_sr_analyzer = AdvancedSRAnalyzer()
    return _advanced_sr_analyzer

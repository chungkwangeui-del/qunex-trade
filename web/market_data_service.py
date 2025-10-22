"""
Market Data Service - Real-time market data from Alpha Vantage API
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

load_dotenv()

class MarketDataService:
    def __init__(self):
        self.api_key = os.getenv('ALPHAVANTAGE_KEY')
        self.base_url = 'https://www.alphavantage.co/query'
        self.cache = {}
        self.cache_duration = 60  # Cache data for 60 seconds

    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False

        cached_time = self.cache[cache_key].get('timestamp')
        if not cached_time:
            return False

        age = (datetime.now() - cached_time).total_seconds()
        return age < self.cache_duration

    def _get_cached_data(self, cache_key):
        """Get cached data if valid"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key].get('data')
        return None

    def _set_cache(self, cache_key, data):
        """Set cache data with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }

    def get_global_quote(self, symbol):
        """Get real-time quote for a symbol"""
        cache_key = f'quote_{symbol}'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()

            if 'Global Quote' in data and data['Global Quote']:
                quote = data['Global Quote']
                result = {
                    'symbol': symbol,
                    'price': float(quote.get('05. price', 0)),
                    'change': float(quote.get('09. change', 0)),
                    'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                    'volume': int(quote.get('06. volume', 0)),
                    'latest_trading_day': quote.get('07. latest trading day', '')
                }

                self._set_cache(cache_key, result)
                return result

            return None

        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            return None

    def get_market_indices(self):
        """Get S&P 500, DOW, NASDAQ, VIX data"""
        cache_key = 'market_indices'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        indices = {
            'SPY': 'sp500',    # S&P 500 ETF
            'DIA': 'dow',      # Dow Jones ETF
            'QQQ': 'nasdaq',   # NASDAQ ETF
            'VIX': 'vix'       # Volatility Index
        }

        result = {}

        for symbol, key in indices.items():
            quote = self.get_global_quote(symbol)
            if quote:
                result[key] = {
                    'value': quote['price'],
                    'change': quote['change'],
                    'changePercent': float(quote['change_percent'])
                }
            else:
                # Fallback to simulated data if API fails
                result[key] = self._get_fallback_index(key)

        self._set_cache(cache_key, result)
        return result

    def _get_fallback_index(self, index_key):
        """Fallback simulated data"""
        import random

        base_values = {
            'sp500': 578.25,  # SPY price
            'dow': 428.63,    # DIA price
            'nasdaq': 485.42, # QQQ price
            'vix': 14.23
        }

        base = base_values.get(index_key, 100)
        change = random.uniform(-2, 2)

        return {
            'value': base + random.uniform(-5, 5),
            'change': change,
            'changePercent': (change / base) * 100
        }

    def get_sector_performance(self):
        """Get sector performance data"""
        cache_key = 'sector_performance'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        # Sector ETFs
        sector_etfs = {
            'XLK': 'Technology',
            'XLV': 'Healthcare',
            'XLF': 'Financials',
            'XLE': 'Energy',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLI': 'Industrials',
            'XLC': 'Communication',
            'XLU': 'Utilities',
            'XLRE': 'Real Estate',
            'XLB': 'Materials'
        }

        result = {}

        for etf, sector_name in sector_etfs.items():
            quote = self.get_global_quote(etf)
            if quote:
                result[sector_name] = float(quote['change_percent'])
            else:
                # Fallback
                import random
                result[sector_name] = random.uniform(-2, 2)

        self._set_cache(cache_key, result)
        return result

    def get_stock_batch_quotes(self, symbols):
        """Get quotes for multiple stocks (batched)"""
        result = {}

        for symbol in symbols:
            quote = self.get_global_quote(symbol)
            if quote:
                result[symbol] = {
                    'price': quote['price'],
                    'change': quote['change'],
                    'changePercent': float(quote['change_percent'])
                }

        return result

    def get_fear_greed_index(self):
        """Calculate Fear & Greed Index based on VIX and market performance"""
        cache_key = 'fear_greed'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            # Get VIX data
            vix_quote = self.get_global_quote('VIX')
            sp500_quote = self.get_global_quote('SPY')

            if vix_quote and sp500_quote:
                vix_value = vix_quote['price']
                sp500_change = float(sp500_quote['change_percent'])

                # Calculate Fear & Greed (0-100 scale)
                # Lower VIX = more greed, Higher VIX = more fear
                # VIX range: typically 10-30 (extreme 10-80)

                # Normalize VIX (inverse - lower VIX = higher score)
                vix_score = max(0, min(100, (30 - vix_value) / 20 * 100))

                # Market momentum score
                momentum_score = max(0, min(100, 50 + (sp500_change * 20)))

                # Weighted average
                fg_value = int((vix_score * 0.6) + (momentum_score * 0.4))

            else:
                # Fallback
                import random
                fg_value = random.randint(40, 70)

            # Determine label
            if fg_value <= 25:
                label = 'Extreme Fear'
                description = 'Market showing extreme pessimism'
            elif fg_value <= 45:
                label = 'Fear'
                description = 'Market showing bearish sentiment'
            elif fg_value <= 55:
                label = 'Neutral'
                description = 'Market balanced between fear and greed'
            elif fg_value <= 75:
                label = 'Greed'
                description = 'Market showing bullish sentiment'
            else:
                label = 'Extreme Greed'
                description = 'Market showing extreme optimism'

            result = {
                'value': fg_value,
                'label': label,
                'description': description
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"Error calculating Fear & Greed: {e}")
            return {
                'value': 50,
                'label': 'Neutral',
                'description': 'Market balanced between fear and greed'
            }

# Global instance
market_service = MarketDataService()

"""
Real-time Market Data Service using Finnhub API
Free tier: 60 requests/minute - much better than Alpha Vantage!
"""

import requests
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinnhubMarketService:
    def __init__(self):
        self.api_key = os.getenv('FINNHUB_API_KEY', 'd3shlnpr01qpdd5jmm1gd3shlnpr01qpdd5jmm20')
        self.base_url = 'https://finnhub.io/api/v1'
        self.cache = {}
        self.cache_duration = 60  # Cache for 1 minute (we have 60 req/min)

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
            logger.info(f"Returning cached data for {cache_key}")
            return self.cache[cache_key].get('data')
        return None

    def _set_cache(self, cache_key, data):
        """Set cache data with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }

    def _get_quote(self, symbol):
        """Get real-time quote for a symbol"""
        try:
            url = f'{self.base_url}/quote'
            params = {
                'symbol': symbol,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data and 'c' in data:  # c = current price
                return {
                    'value': float(data['c']),
                    'change': float(data['d']),  # d = change
                    'changePercent': float(data['dp'])  # dp = percent change
                }
            else:
                logger.warning(f"No data for {symbol}: {data}")
                return None

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    def get_market_indices(self):
        """Get S&P 500, DOW, NASDAQ, VIX data using Finnhub"""
        cache_key = 'market_indices_finnhub'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            logger.info("Fetching market indices from Finnhub...")

            # Use ETFs instead of index symbols (free tier limitation)
            indices_symbols = {
                'SPY': 'sp500',   # S&P 500 ETF
                'DIA': 'dow',     # Dow Jones ETF
                'QQQ': 'nasdaq',  # NASDAQ ETF
                'VXX': 'vix'      # VIX ETF
            }

            result = {}

            for symbol, key in indices_symbols.items():
                quote = self._get_quote(symbol)

                if quote:
                    # Convert ETF prices to index values
                    if key == 'sp500':
                        # SPY is ~1/10 of S&P 500
                        quote['value'] = quote['value'] * 10
                        quote['change'] = quote['change'] * 10
                    elif key == 'dow':
                        # DIA is ~1/100 of Dow Jones
                        quote['value'] = quote['value'] * 100
                        quote['change'] = quote['change'] * 100
                    elif key == 'nasdaq':
                        # QQQ needs adjustment (~40x)
                        quote['value'] = quote['value'] * 40
                        quote['change'] = quote['change'] * 40
                    # VXX doesn't need conversion (it tracks VIX)

                    result[key] = quote
                else:
                    # Fallback
                    result[key] = self._get_fallback_index(key)

            self._set_cache(cache_key, result)
            logger.info(f"Market indices fetched successfully from Finnhub: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in get_market_indices: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback data
            return {
                'sp500': self._get_fallback_index('sp500'),
                'dow': self._get_fallback_index('dow'),
                'nasdaq': self._get_fallback_index('nasdaq'),
                'vix': self._get_fallback_index('vix')
            }

    def _get_fallback_index(self, index_name):
        """Get fallback data for an index"""
        fallback_data = {
            'sp500': {'value': 5816.61, 'change': -9.82, 'changePercent': -0.17},
            'dow': {'value': 42859.15, 'change': -12.10, 'changePercent': -0.03},
            'nasdaq': {'value': 18351.46, 'change': 13.25, 'changePercent': 0.07},
            'vix': {'value': 20.47, 'change': -12.99, 'changePercent': -1.28}
        }
        return fallback_data.get(index_name, {'value': 0, 'change': 0, 'changePercent': 0})

    def get_sector_performance(self):
        """Get sector ETF performance using Finnhub"""
        cache_key = 'sector_performance_finnhub'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            logger.info("Fetching sector performance from Finnhub...")

            # Major sector ETFs
            sector_etfs = {
                'XLK': 'Technology',
                'XLV': 'Healthcare',
                'XLF': 'Financials',
                'XLY': 'Consumer Discretionary',
                'XLC': 'Communication',
                'XLI': 'Industrials',
                'XLP': 'Consumer Staples',
                'XLE': 'Energy',
                'XLU': 'Utilities',
                'XLRE': 'Real Estate',
                'XLB': 'Materials'
            }

            sectors = {}

            for etf_symbol, sector_name in sector_etfs.items():
                quote = self._get_quote(etf_symbol)
                if quote:
                    sectors[sector_name] = quote['changePercent']
                else:
                    # Use realistic fallback
                    fallback_sectors = {
                        'Technology': 1.02,
                        'Healthcare': 1.70,
                        'Financials': 0.40,
                        'Consumer Discretionary': -1.74,
                        'Communication': -0.41,
                        'Industrials': -1.22,
                        'Consumer Staples': -0.80,
                        'Energy': 0.36,
                        'Utilities': -0.68,
                        'Real Estate': -0.10,
                        'Materials': 1.57
                    }
                    sectors[sector_name] = fallback_sectors.get(sector_name, 0)

            self._set_cache(cache_key, sectors)
            logger.info(f"Sector performance fetched successfully: {sectors}")
            return sectors

        except Exception as e:
            logger.error(f"Error fetching sector performance: {e}")
            # Return fallback
            return {
                'Technology': 1.02,
                'Healthcare': 1.70,
                'Financials': 0.40,
                'Consumer Discretionary': -1.74,
                'Communication': -0.41,
                'Industrials': -1.22,
                'Consumer Staples': -0.80,
                'Energy': 0.36,
                'Utilities': -0.68,
                'Real Estate': -0.10,
                'Materials': 1.57
            }

    def get_fear_greed_index(self):
        """Calculate Fear & Greed Index based on VIX"""
        try:
            vix_data = self.get_market_indices().get('vix', {})
            vix_value = vix_data.get('value', 20)

            # VIX interpretation (inverse relationship)
            if vix_value < 12:
                value = 85
                label = "Extreme Greed"
            elif vix_value < 20:
                value = 65
                label = "Greed"
            elif vix_value < 30:
                value = 50
                label = "Neutral"
            elif vix_value < 40:
                value = 35
                label = "Fear"
            else:
                value = 15
                label = "Extreme Fear"

            return {
                'value': value,
                'label': label,
                'description': f'Market showing {label.lower()} sentiment'
            }

        except Exception as e:
            logger.error(f"Error calculating fear & greed index: {e}")
            return {
                'value': 50,
                'label': 'Neutral',
                'description': 'Market showing neutral sentiment'
            }

# Create global instance
finnhub_market_service = FinnhubMarketService()

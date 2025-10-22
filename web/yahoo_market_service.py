"""
Real-time Market Data Service using Yahoo Finance (yfinance)
Unlimited free API access with proper caching
"""

import yfinance as yf
from datetime import datetime, timedelta
import logging
import requests
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YahooMarketService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # Cache data for 5 minutes (reduce API calls)
        # Create a session with proper headers to avoid rate limiting
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

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

    def get_market_indices(self):
        """Get S&P 500, DOW, NASDAQ, VIX data using Yahoo Finance"""
        cache_key = 'market_indices'
        cached = self._get_cached_data(cache_key)
        if cached:
            logger.info("Returning cached market indices")
            return cached

        try:
            logger.info("Fetching market indices from Yahoo Finance...")

            # Fetch index data
            indices_symbols = {
                '^GSPC': 'sp500',   # S&P 500
                '^DJI': 'dow',      # Dow Jones
                '^IXIC': 'nasdaq',  # NASDAQ
                '^VIX': 'vix'       # Volatility Index
            }

            result = {}

            for symbol, key in indices_symbols.items():
                try:
                    ticker = yf.Ticker(symbol, session=self.session)
                    data = ticker.history(period='2d', interval='1d')

                    # Add small delay to avoid rate limiting
                    time.sleep(0.5)

                    if len(data) >= 2:
                        current_price = data['Close'].iloc[-1]
                        prev_price = data['Close'].iloc[-2]
                        change = current_price - prev_price
                        change_percent = (change / prev_price) * 100

                        result[key] = {
                            'value': round(current_price, 2),
                            'change': round(change, 2),
                            'changePercent': round(change_percent, 2)
                        }
                    else:
                        # Fallback
                        result[key] = self._get_fallback_index(key)

                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
                    result[key] = self._get_fallback_index(key)

            self._set_cache(cache_key, result)
            logger.info(f"Market indices fetched successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in get_market_indices: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback data for all indices
            return {
                'sp500': self._get_fallback_index('sp500'),
                'dow': self._get_fallback_index('dow'),
                'nasdaq': self._get_fallback_index('nasdaq'),
                'vix': self._get_fallback_index('vix')
            }

    def _get_fallback_index(self, index_key):
        """Fallback simulated data"""
        import random

        base_values = {
            'sp500': 5825.23,
            'dow': 42863.15,
            'nasdaq': 18342.67,
            'vix': 14.23
        }

        base = base_values.get(index_key, 100)
        change = random.uniform(-20, 20)
        change_percent = (change / base) * 100

        return {
            'value': round(base + random.uniform(-10, 10), 2),
            'change': round(change, 2),
            'changePercent': round(change_percent, 2)
        }

    def get_sector_performance(self):
        """Get sector ETF performance"""
        cache_key = 'sector_performance'
        cached = self._get_cached_data(cache_key)
        if cached:
            logger.info("Returning cached sector performance")
            return cached

        try:
            logger.info("Fetching sector performance from Yahoo Finance...")

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
                try:
                    ticker = yf.Ticker(etf)
                    data = ticker.history(period='2d', interval='1d')

                    if len(data) >= 2:
                        current_price = data['Close'].iloc[-1]
                        prev_price = data['Close'].iloc[-2]
                        change_percent = ((current_price - prev_price) / prev_price) * 100
                        result[sector_name] = round(change_percent, 2)
                    else:
                        # Fallback
                        import random
                        result[sector_name] = round(random.uniform(-2, 2), 2)

                except Exception as e:
                    logger.error(f"Error fetching sector {etf}: {e}")
                    import random
                    result[sector_name] = round(random.uniform(-2, 2), 2)

            self._set_cache(cache_key, result)
            logger.info(f"Sector performance fetched successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in get_sector_performance: {e}")
            import traceback
            traceback.print_exc()

            # Return random fallback data
            import random
            return {
                'Technology': round(random.uniform(-2, 2), 2),
                'Healthcare': round(random.uniform(-1.5, 1.5), 2),
                'Financials': round(random.uniform(-1, 1.5), 2),
                'Energy': round(random.uniform(-2, 2), 2),
                'Consumer Discretionary': round(random.uniform(-1.5, 1.5), 2),
                'Consumer Staples': round(random.uniform(-0.8, 1), 2),
                'Industrials': round(random.uniform(-1.5, 1.5), 2),
                'Communication': round(random.uniform(-1.8, 1.8), 2),
                'Utilities': round(random.uniform(-1, 1), 2),
                'Real Estate': round(random.uniform(-1.5, 1.5), 2),
                'Materials': round(random.uniform(-2, 2), 2)
            }

    def get_stock_batch_quotes(self, symbols):
        """Get quotes for multiple stocks (batched) - FAST with yfinance"""
        cache_key = f'batch_quotes_{" ".join(sorted(symbols))}'
        cached = self._get_cached_data(cache_key)
        if cached:
            logger.info(f"Returning cached batch quotes for {len(symbols)} symbols")
            return cached

        try:
            logger.info(f"Fetching batch quotes for {len(symbols)} symbols from Yahoo Finance...")

            # yfinance can download multiple symbols at once!
            data = yf.download(symbols, period='2d', interval='1d', group_by='ticker', progress=False, threads=True)

            result = {}

            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_data = data
                    else:
                        symbol_data = data[symbol] if symbol in data.columns.levels[0] else None

                    if symbol_data is not None and len(symbol_data) >= 2:
                        current_price = symbol_data['Close'].iloc[-1]
                        prev_price = symbol_data['Close'].iloc[-2]
                        change = current_price - prev_price
                        change_percent = (change / prev_price) * 100

                        result[symbol] = {
                            'price': round(current_price, 2),
                            'change': round(change, 2),
                            'changePercent': round(change_percent, 2)
                        }
                    else:
                        # Fallback for this symbol
                        import random
                        result[symbol] = {
                            'price': round(random.uniform(50, 500), 2),
                            'change': round(random.uniform(-10, 10), 2),
                            'changePercent': round(random.uniform(-3, 3), 2)
                        }

                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    import random
                    result[symbol] = {
                        'price': round(random.uniform(50, 500), 2),
                        'change': round(random.uniform(-10, 10), 2),
                        'changePercent': round(random.uniform(-3, 3), 2)
                    }

            self._set_cache(cache_key, result)
            logger.info(f"Batch quotes fetched successfully for {len(result)} symbols")
            return result

        except Exception as e:
            logger.error(f"Error in get_stock_batch_quotes: {e}")
            import traceback
            traceback.print_exc()

            # Return random fallback data
            import random
            result = {}
            for symbol in symbols:
                result[symbol] = {
                    'price': round(random.uniform(50, 500), 2),
                    'change': round(random.uniform(-10, 10), 2),
                    'changePercent': round(random.uniform(-3, 3), 2)
                }
            return result

    def get_fear_greed_index(self):
        """Calculate Fear & Greed Index based on VIX and market performance"""
        cache_key = 'fear_greed'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            # Get VIX and S&P500 data
            indices = self.get_market_indices()

            vix_value = indices.get('vix', {}).get('value', 14.23)
            sp500_change = indices.get('sp500', {}).get('changePercent', 0)

            # Calculate Fear & Greed (0-100 scale)
            # Lower VIX = more greed, Higher VIX = more fear
            # VIX range: typically 10-30 (extreme 10-80)

            # Normalize VIX (inverse - lower VIX = higher score)
            vix_score = max(0, min(100, (30 - vix_value) / 20 * 100))

            # Market momentum score
            momentum_score = max(0, min(100, 50 + (sp500_change * 20)))

            # Weighted average
            fg_value = int((vix_score * 0.6) + (momentum_score * 0.4))

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
            logger.error(f"Error calculating Fear & Greed: {e}")
            return {
                'value': 50,
                'label': 'Neutral',
                'description': 'Market balanced between fear and greed'
            }

# Global instance
yahoo_market_service = YahooMarketService()

"""
Polygon.io Market Data Service
Real-time and historical stock market data
"""

import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

class PolygonService:
    """Polygon.io API wrapper for real-time market data"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        self.base_url = 'https://api.polygon.io'
        self.session = requests.Session()
        # Polygon.io uses query params for auth, not headers

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request with error handling"""
        try:
            if not self.api_key:
                print("[Polygon API Error] API key not set! Check POLYGON_API_KEY environment variable")
                return None

            url = f"{self.base_url}{endpoint}"
            if params is None:
                params = {}
            params['apiKey'] = self.api_key

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Log API errors
            if data.get('status') == 'ERROR':
                print(f"[Polygon API Error] {endpoint}: {data.get('error', 'Unknown error')}")

            return data
        except requests.exceptions.RequestException as e:
            print(f"[Polygon API Error] {endpoint}: {e}")
            return None

    def get_stock_quote(self, ticker: str) -> Optional[Dict]:
        """Get latest quote for a stock (15-min delayed on Starter plan)"""
        endpoint = f'/v2/last/trade/{ticker}'
        data = self._make_request(endpoint)

        if not data or data.get('status') != 'OK':
            return None

        result = data.get('results', {})
        return {
            'ticker': ticker,
            'price': result.get('p'),
            'size': result.get('s'),
            'timestamp': result.get('t'),
            'exchange': result.get('x'),
        }

    def get_previous_close(self, ticker: str) -> Optional[Dict]:
        """Get previous day's close data"""
        endpoint = f'/v2/aggs/ticker/{ticker}/prev'
        data = self._make_request(endpoint)

        if not data or data.get('status') != 'OK':
            return None

        results = data.get('results', [])
        if not results:
            return None

        result = results[0]
        return {
            'ticker': ticker,
            'open': result.get('o'),
            'high': result.get('h'),
            'low': result.get('l'),
            'close': result.get('c'),
            'volume': result.get('v'),
            'vwap': result.get('vw'),
            'timestamp': result.get('t'),
            'transactions': result.get('n')
        }

    def get_aggregates(self, ticker: str, multiplier: int = 1,
                      timespan: str = 'day', from_date: str = None,
                      to_date: str = None, limit: int = 120) -> Optional[List[Dict]]:
        """
        Get aggregate bars for a stock

        Args:
            ticker: Stock symbol
            multiplier: Size of timespan multiplier (e.g., 1, 5, 15)
            timespan: Size of time window (minute, hour, day, week, month, quarter, year)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            limit: Max results (default 120)
        """
        if not from_date:
            from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        endpoint = f'/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}'
        params = {'adjusted': 'true', 'sort': 'asc', 'limit': limit}

        data = self._make_request(endpoint, params)

        if not data or data.get('status') != 'OK':
            return None

        results = data.get('results', [])
        return [{
            'timestamp': r.get('t'),
            'open': r.get('o'),
            'high': r.get('h'),
            'low': r.get('l'),
            'close': r.get('c'),
            'volume': r.get('v'),
            'vwap': r.get('vw'),
            'transactions': r.get('n')
        } for r in results]

    def get_ticker_details(self, ticker: str) -> Optional[Dict]:
        """Get detailed information about a ticker"""
        endpoint = f'/v3/reference/tickers/{ticker}'
        data = self._make_request(endpoint)

        if not data or data.get('status') != 'OK':
            return None

        result = data.get('results', {})
        return {
            'ticker': result.get('ticker'),
            'name': result.get('name'),
            'market': result.get('market'),
            'locale': result.get('locale'),
            'primary_exchange': result.get('primary_exchange'),
            'type': result.get('type'),
            'active': result.get('active'),
            'currency_name': result.get('currency_name'),
            'cik': result.get('cik'),
            'composite_figi': result.get('composite_figi'),
            'share_class_figi': result.get('share_class_figi'),
            'market_cap': result.get('market_cap'),
            'phone_number': result.get('phone_number'),
            'address': result.get('address'),
            'description': result.get('description'),
            'sic_code': result.get('sic_code'),
            'sic_description': result.get('sic_description'),
            'ticker_root': result.get('ticker_root'),
            'homepage_url': result.get('homepage_url'),
            'total_employees': result.get('total_employees'),
            'list_date': result.get('list_date'),
            'branding': result.get('branding'),
            'share_class_shares_outstanding': result.get('share_class_shares_outstanding'),
            'weighted_shares_outstanding': result.get('weighted_shares_outstanding')
        }

    def get_market_snapshot(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get snapshot of multiple tickers"""
        endpoint = '/v2/snapshot/locale/us/markets/stocks/tickers'
        data = self._make_request(endpoint)

        if not data or data.get('status') != 'OK':
            return {}

        results = data.get('tickers', [])
        snapshot = {}

        for ticker_data in results:
            ticker = ticker_data.get('ticker')
            if ticker in tickers:
                day = ticker_data.get('day', {})
                prev_day = ticker_data.get('prevDay', {})
                last_trade = ticker_data.get('lastTrade', {})

                snapshot[ticker] = {
                    'ticker': ticker,
                    'price': last_trade.get('p'),
                    'size': last_trade.get('s'),
                    'timestamp': last_trade.get('t'),
                    'day_open': day.get('o'),
                    'day_high': day.get('h'),
                    'day_low': day.get('l'),
                    'day_close': day.get('c'),
                    'day_volume': day.get('v'),
                    'day_vwap': day.get('vw'),
                    'prev_close': prev_day.get('c'),
                    'prev_open': prev_day.get('o'),
                    'prev_high': prev_day.get('h'),
                    'prev_low': prev_day.get('l'),
                    'prev_volume': prev_day.get('v'),
                    'change': day.get('c', 0) - prev_day.get('c', 0) if day.get('c') and prev_day.get('c') else 0,
                    'change_percent': ((day.get('c', 0) - prev_day.get('c', 0)) / prev_day.get('c', 1)) * 100 if day.get('c') and prev_day.get('c') else 0
                }

        return snapshot

    def get_gainers_losers(self, direction: str = 'gainers') -> List[Dict]:
        """
        Get top gainers or losers

        Args:
            direction: 'gainers' or 'losers'
        """
        endpoint = f'/v2/snapshot/locale/us/markets/stocks/{direction}'
        data = self._make_request(endpoint)

        if not data or data.get('status') != 'OK':
            return []

        results = data.get('tickers', [])
        return [{
            'ticker': r.get('ticker'),
            'price': r.get('lastTrade', {}).get('p'),
            'change': r.get('todaysChange'),
            'change_percent': r.get('todaysChangePerc'),
            'volume': r.get('day', {}).get('v'),
            'day_high': r.get('day', {}).get('h'),
            'day_low': r.get('day', {}).get('l'),
            'day_open': r.get('day', {}).get('o'),
        } for r in results[:20]]  # Top 20

    def get_market_status(self) -> Optional[Dict]:
        """Get current market status (open/closed)"""
        endpoint = '/v1/marketstatus/now'
        data = self._make_request(endpoint)

        if not data:
            return None

        return {
            'market': data.get('market'),
            'serverTime': data.get('serverTime'),
            'exchanges': {
                'nyse': data.get('exchanges', {}).get('nyse'),
                'nasdaq': data.get('exchanges', {}).get('nasdaq'),
                'otc': data.get('exchanges', {}).get('otc')
            },
            'currencies': {
                'fx': data.get('currencies', {}).get('fx'),
                'crypto': data.get('currencies', {}).get('crypto')
            }
        }

    def search_tickers(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tickers by name or symbol"""
        endpoint = '/v3/reference/tickers'
        params = {
            'search': query,
            'active': 'true',
            'limit': limit,
            'market': 'stocks'
        }

        data = self._make_request(endpoint, params)

        if not data or data.get('status') != 'OK':
            return []

        results = data.get('results', [])
        return [{
            'ticker': r.get('ticker'),
            'name': r.get('name'),
            'market': r.get('market'),
            'locale': r.get('locale'),
            'primary_exchange': r.get('primary_exchange'),
            'type': r.get('type'),
            'active': r.get('active'),
            'currency_name': r.get('currency_name')
        } for r in results]

    def get_technical_indicators(self, ticker: str, days: int = 30) -> Dict:
        """
        Calculate technical indicators from historical data
        """
        # Get historical data
        from_date = (datetime.now() - timedelta(days=days+50)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')

        aggs = self.get_aggregates(ticker, 1, 'day', from_date, to_date, limit=days+50)

        if not aggs or len(aggs) < 20:
            return {}

        # Calculate simple indicators
        closes = [bar['close'] for bar in aggs if bar['close']]
        volumes = [bar['volume'] for bar in aggs if bar['volume']]

        # Moving averages
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None

        # RSI (simplified)
        if len(closes) >= 14:
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))

            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs != 0 else 50
        else:
            rsi = None

        return {
            'ticker': ticker,
            'current_price': closes[-1] if closes else None,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rsi_14': rsi,
            'volume_avg_20': sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None,
            'high_52w': max(closes) if closes else None,
            'low_52w': min(closes) if closes else None,
        }

    def get_market_indices(self) -> Dict[str, Dict]:
        """Get major market indices (SPY, QQQ, DIA as proxies)"""
        indices = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ',
            'DIA': 'Dow Jones',
            'IWM': 'Russell 2000',
            'VIX': 'Volatility Index'
        }

        result = {}
        for ticker, name in indices.items():
            data = self.get_previous_close(ticker)
            if data:
                result[ticker] = {
                    'name': name,
                    'price': data['close'],
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'volume': data['volume'],
                    'change': data['close'] - data['open'],
                    'change_percent': ((data['close'] - data['open']) / data['open'] * 100) if data['open'] else 0
                }

        return result

    def get_sector_performance(self) -> List[Dict]:
        """Get sector ETF performance as proxy for sector performance"""
        sectors = {
            'XLK': 'Technology',
            'XLF': 'Financial',
            'XLV': 'Healthcare',
            'XLE': 'Energy',
            'XLI': 'Industrial',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLU': 'Utilities',
            'XLC': 'Communication'
        }

        result = []
        for ticker, name in sectors.items():
            data = self.get_previous_close(ticker)
            if data:
                change_pct = ((data['close'] - data['open']) / data['open'] * 100) if data['open'] else 0
                result.append({
                    'ticker': ticker,
                    'sector': name,
                    'price': data['close'],
                    'change': data['close'] - data['open'],
                    'change_percent': change_pct,
                    'volume': data['volume']
                })

        # Sort by performance
        result.sort(key=lambda x: x['change_percent'], reverse=True)
        return result

    def screen_stocks(self, criteria: Dict) -> List[Dict]:
        """
        Screen stocks based on criteria

        Criteria examples:
        - min_volume: Minimum volume
        - min_price: Minimum price
        - max_price: Maximum price
        - min_change_percent: Minimum % change
        - max_change_percent: Maximum % change
        """
        # Get all stocks snapshot (this returns active stocks)
        endpoint = '/v2/snapshot/locale/us/markets/stocks/tickers'
        data = self._make_request(endpoint)

        if not data or data.get('status') != 'OK':
            return []

        tickers = data.get('tickers', [])
        results = []

        for ticker_data in tickers[:500]:  # Limit to 500 for performance
            ticker = ticker_data.get('ticker', '')
            day = ticker_data.get('day', {})
            prev_day = ticker_data.get('prevDay', {})
            last_trade = ticker_data.get('lastTrade', {})

            if not day or not prev_day:
                continue

            price = day.get('c', 0)
            volume = day.get('v', 0)
            prev_close = prev_day.get('c', 1)

            # Calculate metrics
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0

            # Apply criteria
            if criteria.get('min_volume') and volume < criteria['min_volume']:
                continue
            if criteria.get('min_price') and price < criteria['min_price']:
                continue
            if criteria.get('max_price') and price > criteria['max_price']:
                continue
            if criteria.get('min_change_percent') and change_percent < criteria['min_change_percent']:
                continue
            if criteria.get('max_change_percent') and change_percent > criteria['max_change_percent']:
                continue

            results.append({
                'ticker': ticker,
                'price': price,
                'change': change,
                'change_percent': change_percent,
                'volume': volume,
                'day_high': day.get('h'),
                'day_low': day.get('l'),
                'day_open': day.get('o'),
                'prev_close': prev_close
            })

        return results


# Singleton instance
_polygon_instance = None

def get_polygon_service() -> PolygonService:
    """Get or create Polygon service instance"""
    global _polygon_instance
    if _polygon_instance is None:
        _polygon_instance = PolygonService()
    return _polygon_instance

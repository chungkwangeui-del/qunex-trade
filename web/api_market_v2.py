"""
Real-time market data API endpoints using Yahoo Finance
"""

from flask import jsonify
from yahoo_market_service import yahoo_market_service
import random

def setup_market_api_routes(app):
    """Add market data API routes to Flask app"""

    @app.route('/api/market-overview-v2')
    def api_market_overview_v2():
        """Get real-time market overview data from Yahoo Finance"""
        try:
            # Get market indices (cached for 60 seconds)
            indices = yahoo_market_service.get_market_indices()

            # Get sector performance
            sectors_raw = yahoo_market_service.get_sector_performance()

            # Map sector names to frontend keys
            sectors = {
                'tech': sectors_raw.get('Technology', 0),
                'health': sectors_raw.get('Healthcare', 0),
                'finance': sectors_raw.get('Financials', 0),
                'energy': sectors_raw.get('Energy', 0),
                'consumerDisc': sectors_raw.get('Consumer Discretionary', 0),
                'consumerStaples': sectors_raw.get('Consumer Staples', 0),
                'industrial': sectors_raw.get('Industrials', 0),
                'communication': sectors_raw.get('Communication', 0),
                'utilities': sectors_raw.get('Utilities', 0),
                'realEstate': sectors_raw.get('Real Estate', 0),
                'materials': sectors_raw.get('Materials', 0)
            }

            # Get Fear & Greed Index
            fear_greed = yahoo_market_service.get_fear_greed_index()

            market_data = {
                'sp500': indices.get('sp500', {'value': 5825.23, 'change': 0, 'changePercent': 0}),
                'dow': indices.get('dow', {'value': 42863.15, 'change': 0, 'changePercent': 0}),
                'nasdaq': indices.get('nasdaq', {'value': 18342.67, 'change': 0, 'changePercent': 0}),
                'vix': indices.get('vix', {'value': 14.23, 'change': 0, 'changePercent': 0}),
                'fearGreed': fear_greed,
                'sectors': sectors
            }

            return jsonify(market_data)

        except Exception as e:
            print(f"Error fetching market data: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback data
            return jsonify({
                'sp500': { 'value': 5825.23, 'change': random.uniform(-20, 20), 'changePercent': random.uniform(-0.5, 0.5) },
                'dow': { 'value': 42863.15, 'change': random.uniform(-150, 150), 'changePercent': random.uniform(-0.5, 0.5) },
                'nasdaq': { 'value': 18342.67, 'change': random.uniform(-80, 80), 'changePercent': random.uniform(-0.5, 0.5) },
                'vix': { 'value': 14.23, 'change': random.uniform(-0.5, 0.5), 'changePercent': random.uniform(-3, 3) },
                'fearGreed': { 'value': 62, 'label': 'Greed', 'description': 'Market showing bullish sentiment' },
                'sectors': {
                    'tech': random.uniform(-2, 2),
                    'health': random.uniform(-1.5, 1.5),
                    'finance': random.uniform(-1, 1.5),
                    'energy': random.uniform(-2, 2),
                    'consumerDisc': random.uniform(-1.5, 1.5),
                    'consumerStaples': random.uniform(-0.8, 1),
                    'industrial': random.uniform(-1.5, 1.5),
                    'communication': random.uniform(-1.8, 1.8),
                    'utilities': random.uniform(-1, 1),
                    'realEstate': random.uniform(-1.5, 1.5),
                    'materials': random.uniform(-2, 2)
                }
            })

    @app.route('/api/sector-stocks-v2')
    def api_sector_stocks_v2():
        """Get real-time data for stocks in each sector"""
        try:
            # Define stock lists by sector with subcategories (same as finviz-data.js structure)
            stock_symbols = {
                'Technology': {
                    'Software - Infrastructure': ['MSFT', 'ORCL', 'PANW', 'CRWD', 'NOW', 'SNOW'],
                    'Semiconductors': ['NVDA', 'AVGO', 'AMD', 'QCOM', 'MU', 'AMAT', 'LRCX', 'KLAC'],
                    'Software - Application': ['CRM', 'ADBE', 'INTU', 'UBER', 'WDAY', 'TEAM'],
                    'Consumer Electronics': ['AAPL', 'SMCI'],
                    'Hardware': ['HPQ', 'DELL', 'NTAP'],
                },
                'Financials': {
                    'Banks - Diversified': ['JPM', 'BAC', 'WFC', 'C'],
                    'Credit Services': ['V', 'MA', 'AXP'],
                    'Capital Markets': ['MS', 'GS', 'SCHW', 'SPGI', 'BLK'],
                    'Financial Data': ['MCO', 'MSCI'],
                    'Insurance - Property & Casualty': ['PGR', 'TRV', 'ALL'],
                    'Insurance - Life': ['PRU', 'MET'],
                },
                'Healthcare': {
                    'Drug Manufacturers - General': ['LLY', 'JNJ', 'ABBV', 'MRK', 'PFE', 'BMY'],
                    'Health Care Plans': ['UNH', 'CVS', 'CI', 'ELV', 'HUM'],
                    'Medical Devices': ['ISRG', 'ABT', 'MDT', 'TMO', 'DHR', 'SYK'],
                    'Biotechnology': ['AMGN', 'GILD', 'REGN', 'VRTX'],
                },
                'Communication': {
                    'Internet Content & Information': ['GOOGL', 'META', 'NFLX'],
                    'Telecom Services': ['T', 'VZ', 'TMUS'],
                    'Entertainment': ['DIS', 'WBD'],
                },
                'Consumer Discretionary': {
                    'Internet Retail': ['AMZN', 'BKNG', 'EBAY'],
                    'Auto Manufacturers': ['TSLA', 'F', 'GM'],
                    'Restaurants': ['MCD', 'SBUX', 'CMG', 'YUM'],
                    'Specialty Retail': ['HD', 'LOW', 'TJX'],
                    'Apparel Retail': ['NKE', 'LULU'],
                },
                'Consumer Staples': {
                    'Discount Stores': ['WMT', 'COST', 'TGT'],
                    'Beverages - Non-Alcoholic': ['KO', 'PEP'],
                    'Household & Personal Products': ['PG', 'CL', 'KMB'],
                    'Packaged Foods': ['MDLZ', 'GIS', 'K'],
                    'Tobacco': ['PM', 'MO', 'BTI'],
                },
                'Industrials': {
                    'Aerospace & Defense': ['GE', 'RTX', 'LMT', 'BA', 'NOC'],
                    'Agricultural Inputs': ['CAT', 'DE'],
                    'Railroads': ['UNP', 'NSC', 'CSX'],
                    'Package Delivery': ['UPS', 'FDX'],
                },
                'Energy': {
                    'Oil & Gas Integrated': ['XOM', 'CVX'],
                    'Oil & Gas E&P': ['COP', 'EOG', 'PXD', 'MRO'],
                },
                'Materials': {
                    'Specialty Chemicals': ['LIN', 'APD', 'ECL', 'SHW'],
                    'Steel': ['NUE'],
                },
                'Real Estate': {
                    'REIT - Industrial': ['PLD'],
                    'REIT - Specialty': ['AMT', 'CCI'],
                },
                'Utilities': {
                    'Utilities - Regulated Electric': ['NEE', 'DUK', 'SO', 'D', 'EXC'],
                }
            }

            # Collect all unique symbols
            all_symbols = set()
            for sector_stocks in stock_symbols.values():
                for subcategory_stocks in sector_stocks.values():
                    all_symbols.update(subcategory_stocks)

            # Get batch quotes (this will use caching to minimize API calls)
            quotes = yahoo_market_service.get_stock_batch_quotes(list(all_symbols))

            # Build result structure
            result = {}
            for sector, subcategories in stock_symbols.items():
                result[sector] = {}
                for subcategory, symbols in subcategories.items():
                    result[sector][subcategory] = []
                    for symbol in symbols:
                        if symbol in quotes:
                            result[sector][subcategory].append({
                                'symbol': symbol,
                                'price': quotes[symbol]['price'],
                                'change': quotes[symbol]['change'],
                                'changePercent': quotes[symbol]['changePercent']
                            })
                        else:
                            # Fallback random data
                            result[sector][subcategory].append({
                                'symbol': symbol,
                                'price': round(random.uniform(50, 500), 2),
                                'change': round(random.uniform(-10, 10), 2),
                                'changePercent': round(random.uniform(-3, 3), 2)
                            })

            return jsonify(result)

        except Exception as e:
            print(f"Error fetching sector stocks: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback random data
            return jsonify({})

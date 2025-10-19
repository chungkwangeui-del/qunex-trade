"""
Data Collection Module for Penny Stocks
Collects historical and real-time data for penny stocks
"""

import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class PennyStockCollector:
    """Collect and manage penny stock data"""

    def __init__(self, config):
        self.config = config
        self.max_price = config['data']['penny_stock_max_price']
        self.min_volume = config['data']['min_volume']
        self.min_market_cap = config['data']['min_market_cap']
        self.lookback_days = config['data']['lookback_days']
        self.logger = logging.getLogger(__name__)

    def get_penny_stock_universe(self) -> List[str]:
        """
        Get a list of potential penny stocks
        This is a starting list - you can expand this with real-time screeners
        """
        # Common penny stock exchanges and tickers
        # In practice, you would use a stock screener API or service

        penny_stocks = [
            # ===== 2022-2025 급등 실적 페니스톡 (50%+ 상승) =====

            # AI & 퀀텀 컴퓨팅 급등주 (2024-2025)
            'RGTI',   # Rigetti Computing - 4,300% 급등 (2024-2025)
            'IREN',   # IREN Ltd - 790% 급등 (2025), Nvidia 파트너
            'SOUN',   # SoundHound AI - 400% (2024), 190% (2025) 급등
            'RR',     # Richtech Robotics - 210% 급등 (2024)
            'IONQ',   # IonQ - 퀀텀 컴퓨팅
            'QUBT',   # Quantum Computing Inc
            'ARQQ',   # Arqit Quantum Inc

            # 바이오테크 급등주 (2022-2024)
            'NVAX',   # Novavax - COVID 백신, 급등락 반복
            'MRNA',   # Moderna - mRNA 선두주자
            'BNTX',   # BioNTech - 화이자 파트너
            'ARDX',   # Ardelyx - 120% 급등 (2022)
            'SAVA',   # Cassava Sciences - 알츠하이머 치료제
            'OCUL',   # Ocular Therapeutix
            'PACB',   # Pacific Biosciences
            'ZLAB',   # Zai Lab Ltd

            # 자동차/EV 급등주 (2023-2024)
            'CVNA',   # Carvana - 1,500% 급등 (2023)
            'BLNK',   # Blink Charging - 73% 매출 성장 (2024)
            'PSNY',   # Polestar Automotive
            'LCID',   # Lucid Motors
            'RIVN',   # Rivian Automotive
            'FFIE',   # Faraday Future

            # 대마초/헬스 급등주 (2024)
            'CGC',    # Canopy Growth - 231% 급등 (2024)
            'TLRY',   # Tilray Brands
            'SNDL',   # Sundial Growers
            'ACB',    # Aurora Cannabis
            'CRON',   # Cronos Group

            # 에너지 급등주 (2022)
            'INDO',   # Indonesia Energy - 1,800% 급등 (2022)
            'TALO',   # Talos Energy
            'REI',    # Ring Energy
            'VTLE',   # Vital Energy

            # AI/테크 급등주 (2024)
            'AMST',   # Amesite Inc - 110% 급등 (2024), AI 앱
            'BBAI',   # BigBear.ai Holdings
            'AI',     # C3.ai Inc
            'PLTR',   # Palantir Technologies

            # ===== 기존 밈주식 & 고변동성 (역사적 급등 경험) =====
            'AMC', 'GME', 'BBBY', 'NOK', 'BB', 'KOSS', 'EXPR', 'NAKD',
            'CLOV', 'WISH', 'MVIS', 'ATER', 'BBIG', 'SPRT', 'GREE',
            'PHUN', 'DWAC', 'IRNT', 'PROG', 'CEI', 'XELA',

            # 바이오테크 & 헬스케어 페니스톡 (FDA 승인 기대)
            'ATOS', 'OCGN', 'VXRT', 'INO', 'SRNE', 'OBSV',
            'SESN', 'TNXP', 'ADMP', 'ATNF', 'CRBP', 'ONTX', 'VBIV',
            'NLSP', 'SENS', 'SEEL', 'ABVC', 'BKSY', 'SKIN', 'MBRX',
            'AGRX', 'AQST', 'ARQT', 'HOOK', 'NRXP', 'PRTA', 'RAPT',
            'RYTM', 'SGMO', 'SYRS', 'TCON', 'TPTX', 'VSTM', 'XERS',
            'ZYXI', 'AGLE', 'ARWR', 'BLUE', 'FATE', 'NTLA', 'CRSP',
            'EDIT', 'BEAM', 'VERV', 'SGFY', 'CDMO',

            # EV & 그린에너지 (고성장 섹터)
            'WKHS', 'RIDE', 'SOLO', 'GEVO', 'IDEX', 'MULN', 'ELMS',
            'AYRO', 'CHPT', 'EVGO', 'PTRA', 'HYZN', 'GOEV',
            'ARVL', 'NKLA', 'FSR', 'HYLN', 'LEV', 'ACTC', 'REE',
            'LOTZ', 'SBE', 'CIIC', 'THCB', 'CCIV', 'PSAC',

            # 크립토 관련 페니스톡
            'BTBT', 'EBON', 'CAN', 'MIGI', 'XNET', 'SOS', 'APLD',
            'ARBK', 'BITF', 'HUT', 'DMGI', 'ANY', 'CNET',
            'RIOT', 'MARA', 'COIN', 'CLSK', 'CIFR',

            # 기술주 & 소프트웨어 페니스톡
            'GNUS', 'JAGX', 'HOFV', 'DLPN', 'LIDR', 'MVST', 'CRTD',
            'SDIG', 'INSG', 'SKLZ', 'FUBO', 'HUSA', 'MICT', 'OZSC',

            # 헬스케어 & 메디컬 디바이스
            'BNGO', 'ZOM', 'GSAT', 'TELL',
            'GRWG', 'IIPR', 'CURLF', 'GTBIF', 'TCNNF', 'CRLBF',

            # 해운 & 운송 (고변동성)
            'ZIM', 'TOPS', 'SHIP', 'CTRM', 'SBLK', 'ESEA', 'EDRY',
            'GLBS', 'HSHP', 'MATX', 'GSL', 'NMM', 'CMRE', 'GOGL',

            # 금융 & 원자재
            'GTE', 'SIRI', 'VALE',
            'SWN', 'AR', 'CLF', 'X', 'MT', 'FCX', 'NEM',

            # 통신 & 미디어
            'VEON', 'LUMN', 'T', 'VZ', 'TMUS', 'S', 'VOD', 'ORAN',

            # 고변동성 추가 종목 (급등 가능성)
            'TRCH', 'MMAT', 'NEGG', 'MRIN', 'CARV', 'WKEY', 'VERB',
            'HMBL', 'SRMX', 'IGEX', 'OPTI', 'VYST', 'PHIL', 'AITX',
            'GTEH', 'ENZC', 'ADTM', 'PCTL', 'USMJ', 'RTON', 'SING',

            # 추가 저가 급등주 후보
            'AESE', 'AIHS', 'ALPP', 'AMLH', 'AMZG', 'AVVH', 'AZFL',
            'BDGR', 'BIEL', 'BLSP', 'BOTY', 'BRLL', 'BTCS', 'BVTK',
            'CBDL', 'CELZ', 'CGRA', 'CHUC', 'CRWG', 'CTXR', 'CWGYF',
            'DECN', 'DSCR', 'DXBRF', 'EAWD', 'EEENF', 'ENKN', 'EPAZ',

            # 소형주 AI/데이터센터 (2024-2025)
            'SMCI',   # Super Micro Computer
            'AVGO',   # Broadcom
            'ARM',    # ARM Holdings

            # 추가 바이오테크 (임상시험 단계)
            'VKTX',   # Viking Therapeutics
            'KPTI',   # Karyopharm Therapeutics
            'TGTX',   # TG Therapeutics
            'DMTK',   # DermTech Inc
            'RVMD',   # Revolution Medicines
            'IMVT',   # Immunovant Inc
            'AKRO',   # Akero Therapeutics
            'VRTX',   # Vertex Pharmaceuticals

            # 추가 EV 인프라 (충전소/배터리)
            'CHPT',   # ChargePoint Holdings
            'EVGO',   # EVgo Inc
            'STEM',   # Stem Inc (에너지 저장)
            'QS',     # QuantumScape (배터리)
            'NOVA',   # Sunnova Energy

            # 우주/항공
            'SPCE',   # Virgin Galactic
            'ASTR',   # Astra Space
            'RKLB',   # Rocket Lab
            'LUNR',   # Intuitive Machines

            # 핀테크/결제
            'UPST',   # Upstart Holdings
            'SOFI',   # SoFi Technologies
            'AFRM',   # Affirm Holdings
            'NU',     # Nu Holdings

            # 추가 크립토/블록체인
            'MSTR',   # MicroStrategy (비트코인 보유)
            'HOOD',   # Robinhood
            'SI',     # Silvergate Capital

            # ===== 일일 50%+ 급등 실적 종목 추가 (2024-2025) =====
            # 고변동성 2024 종목
            'MTTR',   # Matterport - 인수 발표 후 +180% (2024-04)
            'EDBL',   # Edible Garden - 고변동성
            'PEGY',   # Pineapple Energy
            'ONFO',   # Onfolio Holdings
            'SPRC',   # SciSparc Ltd
            'AUUD',   # Auddia Inc
            'BMR',    # Beamr Imaging - Nvidia 협력

            # 바이오테크 고변동성
            'PBLA',   # Panbela Therapeutics
            'KTRA',   # Kintara Therapeutics
            'BXRX',   # Baudax Bio
            'OCEA',   # Ocean Biomedical

            # OTC/Pink Sheet 고변동성
            'EEENF',  # 이미 포함됨
            'GOFF',   # Goff Corp
            'SNGX',   # Sanguine Corp

            # 추가 뉴스 기반 급등 종목들
            'REED',   # Reed's Inc
            'BKTI',   # BK Technologies
            'DPLS',   # DarkPulse Inc
            'LQDA',   # Liquidia Corp
            'HSTO',   # Histogen Inc
            'DRUG',   # Bright Minds Biosciences
            'DRMA',   # Dermata Therapeutics
            'TPST',   # Tempest Therapeutics
            'EVAX',   # Evaxion Biotech
            'CDTX',   # Cidara Therapeutics
        ]

        self.logger.info(f"Penny stock universe: {len(penny_stocks)} tickers")
        return penny_stocks

    def screen_penny_stocks(self, tickers: List[str]) -> List[str]:
        """
        Screen stocks based on penny stock criteria
        Filters by price, volume, and market cap
        """
        valid_tickers = []

        self.logger.info(f"Screening {len(tickers)} tickers...")

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                # Get current price
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')

                # Get volume
                volume = info.get('volume') or info.get('averageVolume')

                # Get market cap
                market_cap = info.get('marketCap', 0)

                # Apply filters
                if (current_price and current_price <= self.max_price and
                    volume and volume >= self.min_volume and
                    market_cap >= self.min_market_cap):
                    valid_tickers.append(ticker)
                    self.logger.info(f"{ticker}: ${current_price:.2f}, Vol: {volume:,}, MCap: ${market_cap:,}")

                time.sleep(0.1)  # Rate limiting

            except Exception as e:
                self.logger.warning(f"Error screening {ticker}: {str(e)}")
                continue

        self.logger.info(f"Found {len(valid_tickers)} valid penny stocks")
        return valid_tickers

    def download_stock_data(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Download historical data for a single stock"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)

            if df.empty:
                self.logger.warning(f"No data for {ticker}")
                return None

            # Add ticker column
            df['Ticker'] = ticker

            # Reset index to have Date as column
            df.reset_index(inplace=True)

            # Clean column names
            df.columns = df.columns.str.lower().str.replace(' ', '_')

            self.logger.info(f"Downloaded {len(df)} rows for {ticker}")
            return df

        except Exception as e:
            self.logger.error(f"Error downloading {ticker}: {str(e)}")
            return None

    def download_multiple_stocks(self, tickers: List[str], start_date: str, end_date: str,
                                 max_workers: int = 5) -> pd.DataFrame:
        """Download data for multiple stocks in parallel"""
        all_data = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.download_stock_data, ticker, start_date, end_date): ticker
                for ticker in tickers
            }

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    df = future.result()
                    if df is not None:
                        all_data.append(df)
                except Exception as e:
                    self.logger.error(f"Error processing {ticker}: {str(e)}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            self.logger.info(f"Total data collected: {len(combined_df)} rows for {len(all_data)} stocks")
            return combined_df
        else:
            self.logger.warning("No data collected")
            return pd.DataFrame()

    def get_realtime_quote(self, ticker: str) -> Dict:
        """Get real-time quote for a ticker"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            quote = {
                'ticker': ticker,
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'volume': info.get('volume'),
                'change_percent': info.get('regularMarketChangePercent'),
                'market_cap': info.get('marketCap'),
                'timestamp': datetime.now()
            }

            return quote

        except Exception as e:
            self.logger.error(f"Error getting quote for {ticker}: {str(e)}")
            return {}

    def add_technical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic technical indicators to the data"""
        df = df.copy()

        # Price changes
        df['price_change'] = df.groupby('ticker')['close'].pct_change()
        df['price_change_1d'] = df.groupby('ticker')['close'].pct_change(1)
        df['price_change_5d'] = df.groupby('ticker')['close'].pct_change(5)

        # Volume changes
        df['volume_change'] = df.groupby('ticker')['volume'].pct_change()

        # High-Low range
        df['hl_range'] = (df['high'] - df['low']) / df['close']

        # Gap detection
        df['gap'] = df.groupby('ticker')['open'].shift(-1) / df['close'] - 1

        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f'sma_{window}'] = df.groupby('ticker')['close'].rolling(window=window).mean().reset_index(0, drop=True)

        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data"""
        df = df.copy()

        # Remove rows with missing critical values
        df.dropna(subset=['close', 'volume'], inplace=True)

        # Remove duplicates
        df.drop_duplicates(subset=['ticker', 'date'], inplace=True)

        # Sort by ticker and date
        df.sort_values(['ticker', 'date'], inplace=True)

        # Reset index
        df.reset_index(drop=True, inplace=True)

        self.logger.info(f"Data cleaned: {len(df)} rows remaining")
        return df

    def save_data(self, df: pd.DataFrame, filename: str = 'penny_stocks_data.csv'):
        """Save collected data to CSV"""
        filepath = f"{self.config['output']['data_dir']}/{filename}"
        df.to_csv(filepath, index=False)
        self.logger.info(f"Data saved to {filepath}")

    def load_data(self, filename: str = 'penny_stocks_data.csv') -> pd.DataFrame:
        """Load data from CSV"""
        filepath = f"{self.config['output']['data_dir']}/{filename}"
        try:
            df = pd.read_csv(filepath)
            df['date'] = pd.to_datetime(df['date'])
            self.logger.info(f"Data loaded from {filepath}: {len(df)} rows")
            return df
        except FileNotFoundError:
            self.logger.error(f"File not found: {filepath}")
            return pd.DataFrame()

    def update_data(self, existing_df: pd.DataFrame, tickers: List[str]) -> pd.DataFrame:
        """Update existing data with new data"""
        # Get the latest date in existing data
        latest_date = existing_df['date'].max()

        # Download new data from latest date to now
        start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        new_data = self.download_multiple_stocks(tickers, start_date, end_date)

        if not new_data.empty:
            # Combine with existing data
            combined = pd.concat([existing_df, new_data], ignore_index=True)
            combined = self.clean_data(combined)
            return combined
        else:
            return existing_df

    def collect_all_data(self, use_screening: bool = True) -> pd.DataFrame:
        """
        Main method to collect all penny stock data

        Args:
            use_screening: If True, screen stocks first. If False, use all tickers.

        Returns:
            DataFrame with all collected data
        """
        # Get penny stock universe
        all_tickers = self.get_penny_stock_universe()

        # Screen stocks if requested
        if use_screening:
            valid_tickers = self.screen_penny_stocks(all_tickers)
        else:
            valid_tickers = all_tickers

        if not valid_tickers:
            self.logger.error("No valid tickers found")
            return pd.DataFrame()

        # Calculate date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime('%Y-%m-%d')

        # Download data
        self.logger.info(f"Downloading data from {start_date} to {end_date}")
        df = self.download_multiple_stocks(valid_tickers, start_date, end_date)

        if df.empty:
            return df

        # Clean data
        df = self.clean_data(df)

        # Add technical data
        df = self.add_technical_data(df)

        # Save data
        self.save_data(df)

        return df

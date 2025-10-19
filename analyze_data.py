import pandas as pd

df = pd.read_csv('data/penny_stocks_data.csv')
df['return_5d'] = df.groupby('ticker')['close'].pct_change(5)

print("\n"+"="*70)
print("페니스톡 데이터 분석")
print("="*70)
print(f"총 데이터 행: {len(df):,}")
print(f"종목 수: {df['ticker'].nunique()}")
print(f"종목 리스트: {', '.join(df['ticker'].unique())}")
print(f"기간: {df['date'].min()} ~ {df['date'].max()}")

print("\n급등 패턴 분석 (5일 기준):")
print("-"*70)
for thresh in [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00]:
    surges = (df['return_5d'] >= thresh).sum()
    pct = surges/len(df)*100 if len(df) > 0 else 0
    print(f"{thresh*100:>5.0f}%+ 급등: {surges:>5}건 ({pct:>5.2f}%)")

print("\n종목별 최대 급등률 (5일 기준):")
print("-"*70)
for ticker in df['ticker'].unique():
    ticker_df = df[df['ticker'] == ticker]
    max_return = ticker_df['return_5d'].max()
    print(f"{ticker}: {max_return*100:>6.2f}%")

print("="*70)

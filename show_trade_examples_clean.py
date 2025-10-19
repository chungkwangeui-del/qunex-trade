import pandas as pd

df = pd.read_csv('results/backtest_threshold_0.95.csv')
df['date'] = pd.to_datetime(df['date'])
df['trade_date'] = pd.to_datetime(df['trade_date'])

print("=" * 100)
print("   ")
print("=" * 100)

#  1:   
print("\n" + "=" * 100)
print(" 1:     (BLSP)")
print("=" * 100)
example = df.nlargest(1, 'net_return').iloc[0]

print(f"\n[+]  : {example['date'].strftime('%Y-%m-%d (%A)')}")
print(f"[+]  : {example['trade_date'].strftime('%Y-%m-%d (%A)')}")
print(f"[+] : {example['ticker']}")
print(f"[+]  : {example['predicted_prob']:.2%}")
print(f"")
print(f"[$]  (  + 0.5% ): ${example['buy_price']:.6f}")
print(f"[$]  (  - 0.5% ): ${example['sell_price']:.6f}")
print(f"")
print(f"[^]   (->): {example['actual_return']*100:.2f}%")
print(f"[!]  ( 0.2% +  1% ): {example['net_return']*100:.2f}%")
print(f"[OK] 50%  : {'' if example['is_surge'] else ''}")
print(f"[#] : {example['volume']:,.0f}")

print(f"\n  :")
print(f"  {example['date'].strftime('%Y-%m-%d')}  :")
print(f"     God  ")
print(f"     : {example['ticker']}   {example['predicted_prob']:.1%}  ")
print(f"")
print(f"  {example['trade_date'].strftime('%Y-%m-%d')} ():")
print(f"       : ${example['buy_price']/1.005:.6f}")
print(f"       ( ): ${example['buy_price']:.6f}")
print(f"       : ${example['sell_price']/0.995:.6f}")
print(f"       ( ): ${example['sell_price']:.6f}")
print(f"      : {example['net_return']*100:.2f}% ")

#  2:   
print("\n" + "=" * 100)
print(" 2:    (BIEL)")
print("=" * 100)
successful_trades = df[(df['is_surge'] == True) & (df['net_return'] < 2)]
if len(successful_trades) > 0:
    example = successful_trades.iloc[0]

    print(f"\n  : {example['date'].strftime('%Y-%m-%d (%A)')}")
    print(f"  : {example['trade_date'].strftime('%Y-%m-%d (%A)')}")
    print(f" : {example['ticker']}")
    print(f"  : {example['predicted_prob']:.2%}")
    print(f"")
    print(f" : ${example['buy_price']:.6f}")
    print(f" : ${example['sell_price']:.6f}")
    print(f"")
    print(f"  : {example['actual_return']*100:.2f}%")
    print(f" : {example['net_return']*100:.2f}%")
    print(f" 50%  : {'' if example['is_surge'] else ''}")

#  3:  
print("\n" + "=" * 100)
print(" 3:   (SRMX)")
print("=" * 100)
example = df.nsmallest(1, 'net_return').iloc[0]

print(f"\n  : {example['date'].strftime('%Y-%m-%d (%A)')}")
print(f"  : {example['trade_date'].strftime('%Y-%m-%d (%A)')}")
print(f" : {example['ticker']}")
print(f"  : {example['predicted_prob']:.2%} ( )")
print(f"")
print(f" : ${example['buy_price']:.6f}")
print(f" : ${example['sell_price']:.6f}")
print(f"")
print(f"  : {example['actual_return']*100:.2f}%")
print(f" : {example['net_return']*100:.2f}%")
print(f" 50%  ")
print(f"")
print(f" :   ({example['predicted_prob']:.1%})   ")
print(f"               ")

#  
print("\n" + "=" * 100)
print("  ")
print("=" * 100)

df['month'] = df['trade_date'].dt.to_period('M')
monthly = df.groupby('month').agg({
    'ticker': 'count',
    'is_surge': 'sum',
    'net_return': lambda x: (x > 0).sum()
}).rename(columns={'ticker': 'total_trades', 'is_surge': 'surge_count', 'net_return': 'win_count'})

monthly['surge_rate'] = (monthly['surge_count'] / monthly['total_trades'] * 100).round(1)
monthly['win_rate'] = (monthly['win_count'] / monthly['total_trades'] * 100).round(1)

print(f"\n{'':<15} {'':<10} {'50%':<15} {'':<15}")
print("-" * 60)
for month, row in monthly.iterrows():
    print(f"{str(month):<15} {row['total_trades']:<10} {int(row['surge_count'])}/{int(row['total_trades'])} ({row['surge_rate']}%)      {int(row['win_count'])}/{int(row['total_trades'])} ({row['win_rate']}%)")

print("\n" + "=" * 100)
print("Lookahead Bias ")
print("=" * 100)

print("\n  :")
print("  1.   'date' (T)  ")
print("  2.   'trade_date' (T+1)  ")
print("  3.  =   (Open)")
print("  4.  =   (Close)")
print("  5.  0.5% +  0.1%  ")
print("\n Lookahead Bias  !")
print("         ")

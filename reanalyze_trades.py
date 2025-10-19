"""
Re-analyze existing trades with INDEPENDENT TRADE statistics
"""
import pandas as pd
import numpy as np

# Load existing trades
trades_df = pd.read_csv('results/backtest_trades_20251018_202305.csv')

print("="*70)
print("RE-ANALYSIS: INDEPENDENT TRADE STATISTICS")
print("="*70)
print()

# Filter for completed trades only
trades_df = trades_df[trades_df['actual_return'].notna()]

# Basic stats - INDEPENDENT TRADES
total_trades = len(trades_df)
winning_trades = len(trades_df[trades_df['actual_return'] > 0])
losing_trades = len(trades_df[trades_df['actual_return'] < 0])
breakeven_trades = len(trades_df[trades_df['actual_return'] == 0])

win_rate = winning_trades / total_trades if total_trades > 0 else 0

# Average statistics across all independent trades
avg_return = trades_df['actual_return'].mean()
median_return = trades_df['actual_return'].median()
std_return = trades_df['actual_return'].std()

max_return = trades_df['actual_return'].max()
min_return = trades_df['actual_return'].min()

# Average win/loss amounts
avg_win = trades_df[trades_df['actual_return'] > 0]['actual_return'].mean() if winning_trades > 0 else 0
avg_loss = trades_df[trades_df['actual_return'] < 0]['actual_return'].mean() if losing_trades > 0 else 0

# Profit factor
total_wins = trades_df[trades_df['actual_return'] > 0]['actual_return'].sum() if winning_trades > 0 else 0
total_losses = abs(trades_df[trades_df['actual_return'] < 0]['actual_return'].sum()) if losing_trades > 0 else 0
profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

# Sharpe ratio (assuming 252 trading days, 2% risk-free rate)
if std_return > 0:
    sharpe_ratio = (avg_return - 0.02/252) / std_return * np.sqrt(252)
else:
    sharpe_ratio = 0

# Simulated cumulative return (if each trade used $10,000)
simulated_initial = 10000
simulated_total_return = avg_return * total_trades
simulated_final = simulated_initial * (1 + simulated_total_return)

# Print results
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate*100:.2f}%")
print(f"  - Winning Trades: {winning_trades}")
print(f"  - Losing Trades: {losing_trades}")
print(f"  - Breakeven Trades: {breakeven_trades}")
print()
print(f"Average Return per Trade: {avg_return*100:.2f}%")
print(f"Median Return per Trade: {median_return*100:.2f}%")
print(f"Std Dev: {std_return*100:.2f}%")
print(f"  - Best Trade: {max_return*100:.2f}%")
print(f"  - Worst Trade: {min_return*100:.2f}%")
print(f"  - Avg Win: {avg_win*100:.2f}%")
print(f"  - Avg Loss: {avg_loss*100:.2f}%")
print()
print(f"Profit Factor: {profit_factor:.2f}")
print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
print()
print(f"Simulated Total Return: {simulated_total_return*100:.2f}%")
print(f"  (If $10,000 invested in each trade independently)")
print(f"Simulated Final Value: ${simulated_final:,.2f}")
print("="*70)
print()

# Show trade breakdown by ticker
print("Trade Breakdown by Ticker:")
print("-"*70)
ticker_summary = trades_df.groupby('ticker').agg({
    'actual_return': ['count', 'mean', 'sum'],
    'profit_loss': 'sum'
}).round(4)
ticker_summary.columns = ['Trades', 'Avg Return', 'Total Return', 'Total P/L']
ticker_summary = ticker_summary.sort_values('Total Return', ascending=False)
print(ticker_summary)
print()

# Save updated summary
summary = {
    'total_trades': total_trades,
    'winning_trades': winning_trades,
    'losing_trades': losing_trades,
    'breakeven_trades': breakeven_trades,
    'win_rate': win_rate,
    'avg_return_per_trade': avg_return,
    'median_return': median_return,
    'std_return': std_return,
    'max_return': max_return,
    'min_return': min_return,
    'avg_win': avg_win,
    'avg_loss': avg_loss,
    'profit_factor': profit_factor,
    'sharpe_ratio': sharpe_ratio,
    'simulated_total_return': simulated_total_return,
    'simulated_final_value': simulated_final
}

summary_df = pd.DataFrame([summary])
summary_df.to_csv('results/backtest_summary_independent_trades.csv', index=False)
print("Summary saved to: results/backtest_summary_independent_trades.csv")

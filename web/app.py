"""
Flask 웹 애플리케이션 - God Model Signal Dashboard
"""

from flask import Flask, render_template, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)

def load_signals_history():
    """시그널 히스토리 로드"""
    path = 'data/signals_history.csv'
    if os.path.exists(path):
        df = pd.read_csv(path)
        df['signal_date'] = pd.to_datetime(df['signal_date'])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        return df
    return pd.DataFrame()

def load_today_signals():
    """오늘 시그널 로드"""
    path = 'data/signals_today.csv'
    if os.path.exists(path):
        df = pd.read_csv(path)
        df['signal_date'] = pd.to_datetime(df['signal_date'])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        return df
    return pd.DataFrame()

def calculate_statistics(df):
    """통계 계산"""
    if df.empty:
        return {
            'total_signals': 0,
            'success_rate': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_tracked': 0
        }

    tracked = df[df['status'].isin(['success', 'partial', 'failed'])]

    if tracked.empty:
        return {
            'total_signals': len(df),
            'success_rate': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_tracked': 0
        }

    stats = {
        'total_signals': len(df),
        'total_tracked': len(tracked),
        'success_count': len(tracked[tracked['status'] == 'success']),
        'partial_count': len(tracked[tracked['status'] == 'partial']),
        'failed_count': len(tracked[tracked['status'] == 'failed']),
        'pending_count': len(df[df['status'] == 'pending']),
        'success_rate': len(tracked[tracked['status'] == 'success']) / len(tracked) * 100 if len(tracked) > 0 else 0,
        'win_rate': len(tracked[tracked['actual_return'] >= 0]) / len(tracked) * 100 if len(tracked) > 0 else 0,
        'avg_return': tracked['actual_return'].mean() if len(tracked) > 0 else 0,
        'median_return': tracked['actual_return'].median() if len(tracked) > 0 else 0,
        'max_return': tracked['actual_return'].max() if len(tracked) > 0 else 0,
        'min_return': tracked['actual_return'].min() if len(tracked) > 0 else 0
    }

    return stats

@app.route('/')
def index():
    """메인 페이지"""
    # 오늘 시그널
    today_signals = load_today_signals()

    # 전체 히스토리
    history = load_signals_history()

    # 통계
    stats = calculate_statistics(history)

    # 최근 30일 성과
    if not history.empty:
        history_30d = history[history['signal_date'] >= datetime.now() - timedelta(days=30)]
        stats_30d = calculate_statistics(history_30d)
    else:
        stats_30d = stats

    return render_template('index.html',
                         today_signals=today_signals.to_dict('records') if not today_signals.empty else [],
                         stats=stats,
                         stats_30d=stats_30d)

@app.route('/about')
def about():
    """About 페이지"""
    return render_template('about.html')

@app.route('/api/signals/today')
def api_today_signals():
    """오늘 시그널 API"""
    signals = load_today_signals()

    if signals.empty:
        return jsonify([])

    # JSON 변환을 위해 날짜를 문자열로 변환
    signals['signal_date'] = signals['signal_date'].dt.strftime('%Y-%m-%d')
    signals['trade_date'] = signals['trade_date'].dt.strftime('%Y-%m-%d')

    return jsonify(signals.to_dict('records'))

@app.route('/api/signals/history')
def api_history():
    """전체 히스토리 API"""
    history = load_signals_history()

    if history.empty:
        return jsonify([])

    # 최근 100개만
    history = history.sort_values('signal_date', ascending=False).head(100)

    # JSON 변환
    history['signal_date'] = history['signal_date'].dt.strftime('%Y-%m-%d')
    history['trade_date'] = history['trade_date'].dt.strftime('%Y-%m-%d')

    return jsonify(history.to_dict('records'))

@app.route('/api/statistics')
def api_statistics():
    """통계 API"""
    history = load_signals_history()
    stats = calculate_statistics(history)

    # 최근 7일, 30일 통계도 추가
    if not history.empty:
        history_7d = history[history['signal_date'] >= datetime.now() - timedelta(days=7)]
        history_30d = history[history['signal_date'] >= datetime.now() - timedelta(days=30)]

        stats['last_7_days'] = calculate_statistics(history_7d)
        stats['last_30_days'] = calculate_statistics(history_30d)

    return jsonify(stats)

@app.route('/api/chart/daily_performance')
def api_chart_daily():
    """일별 성과 차트 데이터"""
    history = load_signals_history()

    if history.empty:
        return jsonify([])

    # 날짜별 그룹화
    tracked = history[history['status'].isin(['success', 'partial', 'failed'])]

    if tracked.empty:
        return jsonify([])

    daily = tracked.groupby(tracked['signal_date'].dt.date).agg({
        'ticker': 'count',
        'actual_return': 'mean',
        'status': lambda x: (x == 'success').sum()
    }).reset_index()

    daily.columns = ['date', 'total_signals', 'avg_return', 'success_count']
    daily['success_rate'] = daily['success_count'] / daily['total_signals'] * 100
    daily['date'] = daily['date'].astype(str)

    return jsonify(daily.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

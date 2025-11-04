# Enhanced AI News Analysis System

## Overview
Real-time financial news collection and AI-powered analysis system that filters for **credible and important news only** (4-5 star ratings).

## Features

### 1. Real-Time News Collection
- **Multiple Reliable Sources:**
  - **Polygon.io** - Real-time market news (highly reliable)
  - **NewsAPI** - Top-tier financial sources only:
    - Bloomberg, Reuters, Financial Times, Wall Street Journal
    - CNBC, MarketWatch, The Economist, Fortune

- **Smart Filtering:**
  - Focuses on market-moving keywords (Fed, inflation, earnings, GDP, etc.)
  - Removes promotional content and low-quality articles
  - Deduplicates news across sources

### 2. AI-Powered Analysis (Claude AI)
- **Importance Rating (1-5 stars):**
  - 5 stars: Federal Reserve decisions, major economic data (CPI, jobs), market crashes/rallies
  - 4 stars: Significant earnings, major company news, important indicators
  - 3 stars or below: FILTERED OUT (not shown)

- **Credibility Rating (1-5 stars):**
  - Based on source reputation and factual content
  - News below 3-star credibility is filtered out

- **Additional Analysis:**
  - Market impact summary (2-3 sentences)
  - Affected stocks (tickers)
  - Affected sectors
  - Sentiment (bullish/bearish/neutral)
  - Time sensitivity (immediate/short-term/long-term)
  - Key points extraction

### 3. News Display
- **Beautiful UI** with filtering by importance
- **Search functionality** - filter by stock ticker or keyword
- **Real-time refresh** button
- **Stock tags** for quick reference
- **Sector categorization**

## How to Use

### Manual News Refresh
```bash
python refresh_news.py
```

This will:
1. Collect news from Polygon.io and NewsAPI (last 12 hours)
2. Analyze each news item with Claude AI
3. Filter for only 4-5 star importance AND 3+ star credibility
4. Save results to `data/news_analysis.json`

### Automatic Refresh
The Flask app (`web/app.py`) automatically refreshes news every hour in the background.

### View News
1. Run the web app: `python web/app.py`
2. Navigate to `/news`
3. Filter by importance (All / 5★ / 4★)
4. Search by stock ticker or keyword
5. Click "Refresh News" for latest updates

## API Endpoints

### GET `/api/news/refresh`
Manually trigger news collection and analysis
- Returns: `{success: true, total_analyzed: X, high_impact_count: Y}`

### GET `/api/news/search?ticker=AAPL&keyword=earnings`
Search news by ticker and/or keyword
- Parameters:
  - `ticker` - Stock ticker (e.g., AAPL, TSLA)
  - `keyword` - Any keyword
- Returns: Filtered news array

### GET `/api/news/critical`
Get only 5-star (critical) news
- Returns: Array of critical news items

## Configuration

### API Keys Required (in `.env`):
```
NEWSAPI_KEY=your_newsapi_key
ANTHROPIC_API_KEY=your_claude_api_key
POLYGON_API_KEY=your_polygon_key
```

### Customization

#### Change News Sources
Edit `src/news_collector.py`:
```python
self.tier1_sources = [
    'bloomberg', 'reuters', 'financial-times',
    # Add more sources...
]
```

#### Adjust Importance Threshold
Edit `src/news_analyzer.py`:
```python
# Line 90: Only keep important and credible news
if importance < 4 or credibility < 3:  # Change these numbers
    return None
```

#### Change AI Model
Edit `src/news_analyzer.py`:
```python
self.model = "claude-3-haiku-20240307"  # Fast and cheap
# OR
self.model = "claude-3-5-sonnet-20240620"  # More accurate (if available)
```

## File Structure

```
PENNY STOCK TRADE/
├── src/
│   ├── __init__.py
│   ├── news_collector.py     # Collects news from APIs
│   └── news_analyzer.py      # AI analysis with Claude
├── data/
│   └── news_analysis.json    # Analyzed news (output)
├── web/
│   ├── app.py                # Flask app (auto-refresh)
│   └── templates/
│       └── news.html         # News page UI
└── refresh_news.py           # Manual refresh script
```

## Performance

- **News Collection:** ~10-15 seconds (50 articles)
- **AI Analysis:** ~2-3 minutes (40 articles)
- **Total Time:** ~3-4 minutes for full refresh
- **Cost:** ~$0.10-0.20 per refresh (using Claude Haiku)

## Output Example

```json
{
  "importance": 5,
  "credibility": 5,
  "impact_summary": "Federal Reserve announces 25 basis point rate cut...",
  "affected_stocks": ["SPY", "QQQ", "TLT"],
  "affected_sectors": ["Financial", "Technology", "Real Estate"],
  "sentiment": "bullish",
  "time_sensitivity": "immediate",
  "key_points": [
    "Fed cuts rates by 25bps",
    "Signals dovish pivot",
    "Markets rally on news"
  ],
  "news_title": "Federal Reserve Cuts Interest Rates...",
  "news_source": "Reuters",
  "news_url": "https://...",
  "published_at": "2025-11-04T10:30:00Z"
}
```

## Benefits for Traders

1. **Save Time** - Only see important news (filters out 70-80% of noise)
2. **High Quality** - Only credible sources (Bloomberg, Reuters, etc.)
3. **AI Insights** - Get instant analysis of market impact
4. **Stock Correlation** - See which stocks are affected
5. **Real-Time** - Auto-refreshes every hour

## Future Enhancements (Monetization Ready)

- [ ] Real-time alerts (email/SMS for 5-star news)
- [ ] Custom watchlists (get news for specific stocks)
- [ ] News sentiment tracking over time
- [ ] Breaking news push notifications
- [ ] Premium: Unlimited news history
- [ ] Premium: Faster refresh intervals (every 15 minutes)

## Troubleshooting

### No news collected
- Check API keys in `.env`
- Verify NewsAPI tier 1 sources are accessible
- Try increasing time range (hours parameter)

### AI analysis fails
- Check ANTHROPIC_API_KEY is valid
- Verify model name is correct
- Check API rate limits

### Encoding errors
- Fixed in current version (uses ASCII for console output)
- Web display uses UTF-8 (no issues)

---

**Status:** ✅ FULLY FUNCTIONAL - Ready for production use!

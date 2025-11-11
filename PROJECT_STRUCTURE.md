# Qunex Trade - Project Structure

**Last Updated:** 2025-11-11
**Status:** Production-Ready

---

## Directory Structure

```
PENNY STOCK TRADE/
├── web/                        # Flask Web Application
│   ├── templates/              # Jinja2 HTML templates (16 files)
│   │   ├── index.html          # Homepage with search & market overview
│   │   ├── stock_chart.html    # Individual stock page with TradingView widget
│   │   ├── market.html         # Market overview & indices
│   │   ├── screener.html       # Stock screener
│   │   ├── watchlist.html      # User watchlist
│   │   ├── calendar.html       # Economic calendar
│   │   ├── news.html           # News feed
│   │   ├── account.html        # User account settings
│   │   ├── admin_dashboard.html # Admin dashboard
│   │   ├── pricing.html        # Pricing plans
│   │   ├── privacy.html        # Privacy policy
│   │   ├── terms.html          # Terms of service
│   │   ├── login.html          # Login page
│   │   ├── signup.html         # Signup page
│   │   ├── forgot_password.html # Forgot password
│   │   └── reset_password.html  # Reset password
│   ├── static/                 # Static assets
│   │   ├── *.css               # CSS files (5 files)
│   │   │   ├── basic.css       # Base styles & theme variables
│   │   │   ├── common-components.css # Shared components
│   │   │   ├── skeleton-loading.css  # Loading animations
│   │   │   ├── mobile.css      # Mobile responsive styles
│   │   │   └── animations.css  # CSS animations
│   │   ├── *.js                # JavaScript files (7 files)
│   │   │   ├── session-timeout.js    # Session management
│   │   │   ├── finviz-data-realtime.js # Market data
│   │   │   ├── recaptcha.js    # reCAPTCHA integration
│   │   │   ├── ui-enhancements.js    # UI improvements
│   │   │   ├── toast.js        # Toast notifications
│   │   │   ├── theme-toggle.js # Theme switching
│   │   │   └── market-overview-realtime.js # Market overview
│   │   ├── favicon.svg         # Favicon
│   │   └── manifest files      # PWA manifest
│   ├── app.py                  # Main Flask application
│   ├── auth.py                 # Authentication & OAuth
│   ├── database.py             # Database models
│   ├── payments.py             # Payment integration (Stripe)
│   ├── polygon_service.py      # Polygon.io service layer
│   ├── api_polygon.py          # Polygon.io API routes
│   ├── api_watchlist.py        # Watchlist API routes
│   └── instance/               # Database files (SQLite)
├── ml/                         # Machine Learning System
│   ├── ai_score_system.py      # AI Score model (XGBoost)
│   ├── train_ai_score.py       # Model training script
│   ├── test_ai_score.py        # Model testing script
│   ├── train_model_only.py     # Quick training from CSV
│   ├── README.md               # ML system documentation
│   ├── requirements.txt        # ML dependencies
│   ├── training_data.csv       # Training data (Git LFS)
│   └── models/                 # Trained models
│       └── ai_score_model.pkl  # XGBoost model (Git LFS)
├── src/                        # Source utilities
│   ├── news_analyzer.py        # AI news analysis with Claude
│   └── news_collector.py       # News collection from APIs
├── data/                       # Data files
│   └── news_analysis.json      # Cached news analysis
├── tests/                      # Test files
│   ├── test_pages.py           # Page load tests
│   ├── test_screener.py        # Screener tests
│   └── test_stock_page.py      # Stock page tests
├── .env                        # Environment variables (gitignored)
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── Procfile                    # Heroku/Render deployment
├── render.yaml                 # Render.com configuration
├── runtime.txt                 # Python version
├── build.sh                    # Build script
├── generate_favicons.py        # Favicon generator
├── generate_og_image.py        # Open Graph image generator
├── refresh_news.py             # News refresh utility
├── CLEANUP_REPORT.md           # Previous cleanup report
└── README.md                   # Project documentation
```

---

## Core Technologies

### Backend
- **Framework:** Flask (Python)
- **Database:** SQLite (development) / PostgreSQL (production)
- **ORM:** SQLAlchemy
- **Authentication:** Flask-Login + Google OAuth
- **API:** Polygon.io (real-time market data)

### Frontend
- **Templates:** Jinja2
- **CSS:** Custom CSS with theme variables (light/dark mode)
- **JavaScript:** Vanilla JS
- **Charts:** TradingView Widget

### Machine Learning
- **Framework:** XGBoost
- **Features:** 22 technical indicators (RSI, MACD, Moving Averages, etc.)
- **Training Data:** Real historical data from Polygon.io
- **Model:** Binary classification (0-100 score)

### External Services
- **Market Data:** Polygon.io API
- **News:** NewsAPI
- **AI Analysis:** Anthropic Claude API
- **Payments:** Stripe

---

## Key Features

### 1. Stock Analysis
- Individual stock pages with TradingView charts
- Real-time price updates
- AI Score (0-100) powered by XGBoost ML model
- Recent news with AI sentiment analysis

### 2. Market Overview
- Major indices (S&P 500, Nasdaq, Dow Jones)
- Market sectors performance
- Top movers (gainers/losers)
- Real-time updates

### 3. Stock Screener
- Filter stocks by various criteria
- AI Score integration
- Customizable columns
- Export functionality

### 4. User Features
- Personal watchlists
- Account management
- Premium subscriptions (Stripe)
- Google OAuth login

### 5. News & Calendar
- Economic events calendar
- AI-analyzed news feed
- Sector-specific news

---

## Environment Variables

Required environment variables (see `.env.example`):

```bash
# API Keys
POLYGON_API_KEY=your_polygon_api_key
NEWSAPI_KEY=your_newsapi_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Email (Gmail)
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# reCAPTCHA
RECAPTCHA_SECRET_KEY=your_recaptcha_key

# Database (production)
DATABASE_URL=postgresql://...

# Stripe (optional)
STRIPE_PUBLIC_KEY=your_stripe_public_key
STRIPE_SECRET_KEY=your_stripe_secret_key
```

---

## Deployment

### Development
```bash
# Install dependencies
pip install -r requirements.txt
cd web && pip install -r requirements.txt

# Run Flask server
python web/app.py
```

### Production (Render.com)
- Automatically deployed via `render.yaml`
- Uses PostgreSQL database
- Gunicorn WSGI server
- Environment variables set in Render dashboard

---

## Git Workflow

### Branches
- `main` - Production-ready code
- Feature branches as needed

### Commits
- Conventional commit messages
- Co-authored by Claude Code
- Pushed to GitHub

---

## Code Quality

### Status: ✅ Production-Ready

- **No debug files** - All test/debug files removed
- **Clean structure** - Organized folders and files
- **Documentation** - Comprehensive README and docs
- **Type safety** - Python type hints where appropriate
- **Security** - CSP headers, input validation, HTTPS
- **Performance** - Optimized queries, caching
- **Testing** - Test files in `tests/` folder

---

## Recent Updates

### 2025-11-11
- ✅ Implemented TradingView Widget for professional charts
- ✅ Added individual stock pages with AI Score
- ✅ Code cleanup - removed old documentation
- ✅ Organized test files into tests/ folder
- ✅ Fixed template syntax errors

### 2025-11-07
- ✅ Comprehensive code cleanup
- ✅ Removed debug files
- ✅ Optimized HTML templates
- ✅ Cleaned Python code

---

## Future Enhancements

- [ ] Real-time WebSocket price updates
- [ ] Advanced screener filters
- [ ] Portfolio tracking
- [ ] Backtesting system
- [ ] Mobile app (React Native)

---

**Maintained by:** Claude Code Assistant
**Project Status:** Active Development
**License:** Proprietary

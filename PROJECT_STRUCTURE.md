# PENNY STOCK TRADE - Project Structure Documentation

**Last Updated:** 2025-11-07
**Version:** 1.0

---

## TABLE OF CONTENTS
1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [File Groups](#file-groups)
4. [Module Dependencies](#module-dependencies)
5. [File Purpose Reference](#file-purpose-reference)

---

## PROJECT OVERVIEW

**PENNY STOCK TRADE** is a professional-grade AI-powered stock market intelligence platform built with Flask, featuring real-time market data, AI news analysis, stock screener, and economic calendar.

**Tech Stack:**
- **Backend:** Python 3.14, Flask 3.1.0
- **Database:** SQLite (dev), PostgreSQL (production)
- **Frontend:** HTML5, CSS3, JavaScript, D3.js
- **APIs:** Polygon.io, NewsAPI, Anthropic Claude AI
- **Deployment:** Render.com
- **Authentication:** Flask-Login, OAuth (Google)
- **Payment:** Stripe (in development)

---

## DIRECTORY STRUCTURE

```
PENNY STOCK TRADE/
│
├── .git/                          # Git repository
├── .claude/                       # Claude Code settings
│
├── data/                          # Application data (JSON storage)
│   ├── economic_calendar.json    # Economic events data
│   └── news_analysis.json        # AI-analyzed news data
│
├── instance/                      # Database instance (root level)
│   └── qunextrade.db             # SQLite database (development)
│
├── src/                          # Source modules (News processing)
│   ├── __init__.py               # Package marker
│   ├── news_analyzer.py          # AI-powered news analysis (Claude)
│   └── news_collector.py         # Multi-source news collection
│
├── web/                          # Main Flask web application
│   │
│   ├── data/                     # ⚠️ DUPLICATE - Should consolidate
│   │   └── news_analysis.json
│   │
│   ├── instance/                 # ⚠️ DUPLICATE - Should consolidate
│   │   └── qunextrade.db
│   │
│   ├── static/                   # Static assets (CSS, JS, Images)
│   │   ├── CSS Files
│   │   │   ├── animations.css           # CSS animations & transitions
│   │   │   ├── basic.css                # Basic dark theme styles
│   │   │   ├── mobile.css               # Mobile responsive styles
│   │   │   ├── skeleton-loading.css     # Loading skeleton animations
│   │   │   └── theme.css                # Theme variables & switching
│   │   │
│   │   ├── JavaScript Files
│   │   │   ├── d3.v7.min.js            # D3.js library (data visualization)
│   │   │   ├── finviz-data-realtime.js # Real-time stock data updates
│   │   │   ├── market-overview-realtime.js # Market indices updates
│   │   │   ├── recaptcha.js            # reCAPTCHA integration (disabled)
│   │   │   ├── session-timeout.js      # Session timeout handling
│   │   │   ├── theme-toggle.js         # Dark/light mode toggle
│   │   │   ├── toast.js                # Toast notification system
│   │   │   └── ui-enhancements.js      # UI interaction enhancements
│   │   │
│   │   ├── Images & Favicons
│   │   │   ├── favicon.svg             # SVG favicon
│   │   │   ├── favicon-16x16.png       # Small favicon
│   │   │   ├── favicon-32x32.png       # Standard favicon
│   │   │   ├── favicon-192x192.png     # Android chrome
│   │   │   ├── favicon-512x512.png     # High-res favicon
│   │   │   ├── apple-touch-icon.png    # iOS home screen icon
│   │   │   └── og-image.png            # Open Graph social media image
│   │   │
│   │   └── Other Files
│   │       ├── FAVICON_README.md       # Favicon documentation
│   │       ├── robots.txt              # SEO robots file
│   │       ├── sitemap.xml             # SEO sitemap
│   │       └── site.webmanifest        # PWA manifest
│   │
│   ├── templates/                # Jinja2 HTML templates
│   │   ├── Core Pages
│   │   │   ├── index.html              # Homepage
│   │   │   ├── about.html              # About page
│   │   │   ├── market.html             # Market dashboard
│   │   │   ├── screener.html           # Stock screener
│   │   │   ├── watchlist.html          # Personal watchlist
│   │   │   ├── calendar.html           # Economic calendar
│   │   │   └── news.html               # News & analysis
│   │   │
│   │   ├── Authentication
│   │   │   ├── login.html              # Login page
│   │   │   ├── signup.html             # Signup page
│   │   │   ├── forgot_password.html    # Password reset request
│   │   │   ├── reset_password.html     # Password reset form
│   │   │   └── account.html            # User account settings
│   │   │
│   │   ├── Admin
│   │   │   └── admin_dashboard.html    # Admin control panel
│   │   │
│   │   ├── Legal & Info
│   │   │   ├── pricing.html            # Subscription pricing
│   │   │   ├── terms.html              # Terms of service
│   │   │   ├── privacy.html            # Privacy policy
│   │   │   └── seo_meta.html           # SEO meta tag template
│   │   │
│   │   └── Utilities
│   │       ├── reset_theme.html        # Theme reset utility
│   │       └── FORCE_DARK_MODE.html    # Force dark mode utility
│   │
│   ├── Python Modules
│   │   ├── app.py                      # Main Flask application (573 lines)
│   │   ├── auth.py                     # Authentication routes (669 lines)
│   │   ├── database.py                 # Database models (134 lines)
│   │   ├── payments.py                 # Stripe payment processing (145 lines)
│   │   ├── polygon_service.py          # Polygon.io API wrapper (592 lines)
│   │   ├── api_polygon.py              # Polygon API endpoints (417 lines)
│   │   └── api_watchlist.py            # Watchlist API endpoints (240 lines)
│   │
│   └── requirements.txt          # ⚠️ DUPLICATE - Should consolidate
│
├── Utility Scripts (Root Level)
│   ├── generate_favicons.py      # Favicon generation utility
│   ├── generate_og_image.py      # Open Graph image generator
│   └── refresh_news.py           # Manual news refresh script
│
├── Configuration Files
│   ├── .env                      # Environment variables (not in git)
│   ├── .env.example              # Environment template
│   ├── .gitignore                # Git ignore rules
│   ├── .gitattributes            # Git LFS configuration
│   ├── .python-version           # Python version specification
│   ├── requirements.txt          # Python dependencies
│   ├── runtime.txt               # Python runtime for Render
│   ├── Procfile                  # Process file for deployment
│   └── render.yaml               # Render.com deployment config
│
├── Documentation
│   ├── ECONOMIC_EVENTS_GUIDE.md  # Economic calendar guide
│   ├── NEWS_SYSTEM_README.md     # News system documentation
│   ├── PROJECT_AUDIT_REPORT.md   # Comprehensive audit report
│   └── PROJECT_STRUCTURE.md      # This file
│
└── Debug Files (⚠️ Should move to dev folder)
    ├── test-theme.html           # Theme testing page
    └── THEME_DEBUG.html          # Theme debug utilities
```

---

## FILE GROUPS

### GROUP 1: Core Application (Python Backend)

**Purpose:** Main application logic, routing, business logic

| File | Lines | Purpose | Dependencies |
|------|-------|---------|--------------|
| `web/app.py` | 573 | Main Flask app, routes, config | Flask, database, auth, payments, API modules |
| `web/auth.py` | 669 | Authentication, signup, login, OAuth | Flask, database, email |
| `web/database.py` | 134 | Database models (User, Payment, Watchlist) | SQLAlchemy, Flask-Login |
| `web/payments.py` | 145 | Stripe payment processing | Flask, database, Stripe |

**Status:** ✓ Well organized but needs refactoring (auth.py too long)

---

### GROUP 2: API Services (External Data Integration)

**Purpose:** API wrappers and endpoints for external data

| File | Lines | Purpose | Dependencies |
|------|-------|---------|--------------|
| `web/polygon_service.py` | 592 | Polygon.io API wrapper with caching | requests, datetime |
| `web/api_polygon.py` | 417 | REST endpoints for Polygon data | Flask, polygon_service |
| `web/api_watchlist.py` | 240 | Watchlist CRUD API endpoints | Flask, database, polygon_service |

**Status:** ✓ Clean architecture with proper separation

---

### GROUP 3: News Processing (AI-Powered)

**Purpose:** News collection and AI analysis

| File | Lines | Purpose | Dependencies |
|------|-------|---------|--------------|
| `src/news_collector.py` | 295 | Multi-source news collection | requests, NewsAPI, Polygon |
| `src/news_analyzer.py` | 240 | AI news analysis with Claude | Anthropic API, json |
| `refresh_news.py` | 87 | Manual news refresh script | news_collector, news_analyzer |

**Status:** ✓ Excellent design, well-documented

---

### GROUP 4: Frontend Templates (HTML)

**Purpose:** User interface templates

#### Core Pages (7 files)
- `index.html` - Homepage with market overview
- `market.html` - Real-time market dashboard
- `screener.html` - Stock screening tool
- `watchlist.html` - Personal stock watchlist
- `calendar.html` - Economic calendar
- `news.html` - AI-analyzed news feed
- `about.html` - About the platform

#### Authentication (5 files)
- `login.html` - User login
- `signup.html` - User registration
- `account.html` - Account settings
- `forgot_password.html` - Password reset request
- `reset_password.html` - Password reset form

#### Admin (1 file)
- `admin_dashboard.html` - Admin control panel

#### Legal (3 files)
- `pricing.html` - Subscription plans
- `terms.html` - Terms of service
- `privacy.html` - Privacy policy

#### Utilities (3 files)
- `seo_meta.html` - SEO meta tags template
- `reset_theme.html` - Theme reset utility
- `FORCE_DARK_MODE.html` - Dark mode fix

**Status:** ⚠️ Many inline styles, need CSS extraction

---

### GROUP 5: Static Assets (CSS)

**Purpose:** Styling and visual presentation

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `theme.css` | 265 | Theme variables & dark/light mode | ⚠️ Duplicates basic.css |
| `basic.css` | 186 | Basic dark theme styles | ⚠️ Duplicates theme.css |
| `mobile.css` | 253 | Mobile responsive styles | ✓ Good |
| `skeleton-loading.css` | 365 | Loading animations | ✓ Good |
| `animations.css` | 174 | CSS transitions & effects | ✓ Good |

**Status:** ⚠️ Need consolidation - theme.css and basic.css have duplicate variables

---

### GROUP 6: Static Assets (JavaScript)

**Purpose:** Client-side interactivity and data updates

| File | Purpose | Console.logs | Status |
|------|---------|--------------|--------|
| `d3.v7.min.js` | D3 data visualization library | N/A | ✓ External library |
| `theme-toggle.js` | Dark/light mode switching | 0 | ✓ Clean |
| `finviz-data-realtime.js` | Real-time stock data updates | 2 | ⚠️ Remove logs |
| `market-overview-realtime.js` | Market indices updates | 4 | ⚠️ Remove logs |
| `session-timeout.js` | Session timeout handling | 0 | ✓ Clean |
| `toast.js` | Toast notifications | 0 | ✓ Clean |
| `ui-enhancements.js` | UI interaction utilities | 0 | ✓ Clean |
| `recaptcha.js` | reCAPTCHA integration | 0 | ⚠️ Disabled (bug) |

**Status:** ⚠️ Need to remove production console.logs and fix reCAPTCHA

---

### GROUP 7: Data Files (JSON)

**Purpose:** Application data storage

| File | Purpose | Location |
|------|---------|----------|
| `news_analysis.json` | AI-analyzed news data | `data/` and `web/data/` (duplicate) |
| `economic_calendar.json` | Economic events data | `data/` |

**Status:** ⚠️ Duplicate directories need consolidation

---

### GROUP 8: Database Files

**Purpose:** Data persistence

| File | Purpose | Location |
|------|---------|----------|
| `qunextrade.db` | SQLite database | `instance/` and `web/instance/` (duplicate) |

**Status:** 🔴 Critical - Duplicate databases must be consolidated

---

### GROUP 9: Configuration Files

**Purpose:** Project configuration and deployment

| File | Purpose |
|------|---------|
| `.env` | Environment variables (secrets) |
| `.env.example` | Environment template |
| `requirements.txt` | Python dependencies (root) |
| `web/requirements.txt` | Python dependencies (duplicate) |
| `runtime.txt` | Python version for Render |
| `Procfile` | Process definition for deployment |
| `render.yaml` | Render.com deployment config |
| `.gitignore` | Git ignore rules |
| `.gitattributes` | Git LFS configuration |
| `.python-version` | Python version |

**Status:** ⚠️ Duplicate requirements.txt files

---

### GROUP 10: Utility Scripts

**Purpose:** Development and maintenance utilities

| File | Lines | Purpose |
|------|-------|---------|
| `generate_favicons.py` | 97 | Generate favicon files |
| `generate_og_image.py` | 105 | Generate Open Graph image |
| `refresh_news.py` | 87 | Manual news refresh |

**Status:** ✓ Clean and well-documented

---

### GROUP 11: Documentation

**Purpose:** Project documentation

| File | Purpose |
|------|---------|
| `NEWS_SYSTEM_README.md` | News system documentation |
| `ECONOMIC_EVENTS_GUIDE.md` | Economic calendar guide |
| `PROJECT_AUDIT_REPORT.md` | Comprehensive audit report |
| `PROJECT_STRUCTURE.md` | This file |
| `web/static/FAVICON_README.md` | Favicon documentation |

**Status:** ✓ Good documentation coverage

---

### GROUP 12: Debug/Test Files

**Purpose:** Development testing and debugging

| File | Purpose | Status |
|------|---------|--------|
| `test-theme.html` | Theme testing | ⚠️ Move to dev folder |
| `THEME_DEBUG.html` | Theme debugging | ⚠️ Move to dev folder |

**Status:** ⚠️ Should not be in root directory

---

## MODULE DEPENDENCIES

### Dependency Graph

```
app.py (Main Entry Point)
├── database.py (Models)
│   └── SQLAlchemy
├── auth.py (Authentication)
│   ├── database.py
│   ├── Flask-Mail
│   └── OAuth (Authlib)
├── payments.py (Payments)
│   ├── database.py
│   └── Stripe
├── api_polygon.py (Market Data API)
│   └── polygon_service.py
│       └── requests (HTTP)
├── api_watchlist.py (Watchlist API)
│   ├── database.py
│   └── polygon_service.py
└── src/news_* (News Processing)
    ├── news_collector.py
    │   ├── requests
    │   └── External APIs (NewsAPI, Polygon)
    └── news_analyzer.py
        └── Anthropic API (Claude)
```

### External Dependencies

**Python Packages (from requirements.txt):**
- `flask==3.1.0` - Web framework
- `flask-login==0.6.3` - User session management
- `flask-sqlalchemy==3.1.1` - Database ORM
- `flask-mail==0.10.0` - Email sending
- `flask-limiter==3.8.0` - Rate limiting
- `flask-wtf==1.2.2` - CSRF protection
- `werkzeug==3.1.3` - WSGI utilities
- `sqlalchemy==2.0.36` - SQL toolkit
- `gunicorn==23.0.0` - WSGI server
- `stripe==11.2.0` - Payment processing
- `authlib==1.4.0` - OAuth authentication
- `requests==2.32.3` - HTTP client
- `python-dotenv==1.0.1` - Environment variables
- `psycopg[binary]==3.2.4` - PostgreSQL driver
- `anthropic>=0.71.0` - Claude AI API
- `schedule==1.2.2` - Task scheduling

**External APIs:**
- Polygon.io - Real-time market data
- NewsAPI - News articles
- Anthropic Claude - AI analysis
- Google OAuth - Social login
- Stripe - Payment processing (in development)

---

## FILE PURPOSE REFERENCE

### Quick Lookup Table

| File | Primary Purpose | Size | Critical? |
|------|----------------|------|-----------|
| `web/app.py` | Main app, routes, config | 573L | 🔴 Critical |
| `web/auth.py` | User authentication | 669L | 🔴 Critical |
| `web/database.py` | Database models | 134L | 🔴 Critical |
| `web/polygon_service.py` | Market data API wrapper | 592L | 🟡 Important |
| `web/api_polygon.py` | Market data endpoints | 417L | 🟡 Important |
| `src/news_collector.py` | News collection | 295L | 🟡 Important |
| `src/news_analyzer.py` | AI news analysis | 240L | 🟡 Important |
| `web/api_watchlist.py` | Watchlist API | 240L | 🟢 Normal |
| `web/payments.py` | Payment processing | 145L | 🟢 Normal |
| `static/*.css` | Styles | 1243L | 🟢 Normal |
| `static/*.js` | Client scripts | 1256L | 🟢 Normal |
| `templates/*.html` | UI templates | 8968L | 🟢 Normal |

---

## RECOMMENDED ORGANIZATION IMPROVEMENTS

### 1. Consolidate Duplicate Directories

**Current Structure:**
```
./data/ and ./web/data/
./instance/ and ./web/instance/
```

**Recommended:**
```
./data/                 (Keep only this)
./instance/             (Keep only this)
```

**Action:** Remove `web/data/` and `web/instance/`, update paths in code

### 2. Create Dev/Test Directory

**Recommended Structure:**
```
dev/
├── test-theme.html
├── THEME_DEBUG.html
└── test_*.py (future test files)
```

### 3. Consolidate Configuration

**Current:**
```
requirements.txt (root)
web/requirements.txt
```

**Recommended:**
```
requirements.txt (keep root only)
```

### 4. Organize Static Assets Better

**Current:**
```
static/ (all files mixed)
```

**Recommended:**
```
static/
├── css/
│   ├── theme.css (consolidated)
│   ├── mobile.css
│   ├── animations.css
│   └── skeleton-loading.css
├── js/
│   ├── vendor/
│   │   └── d3.v7.min.js
│   ├── theme-toggle.js
│   ├── market-data.js (combine finviz + market-overview)
│   └── utils.js (combine toast + ui-enhancements + session-timeout)
└── images/
    ├── favicons/
    └── og-image.png
```

---

## NOTES

### Misplaced Files
- `test-theme.html` - Should be in dev/ folder
- `THEME_DEBUG.html` - Should be in dev/ folder
- `web/requirements.txt` - Duplicate, should remove

### Duplicate Data
- `news_analysis.json` exists in both `data/` and `web/data/`
- `qunextrade.db` exists in both `instance/` and `web/instance/`
- This can cause data inconsistency issues

### Large Files Requiring Refactoring
1. `web/auth.py` (669 lines) - Email templates should be extracted
2. `web/polygon_service.py` (592 lines) - Could split into modules
3. `web/app.py` (573 lines) - Routes should be blueprints

### CSS Consolidation Needed
- `theme.css` and `basic.css` have duplicate CSS variables
- Choose one as the source of truth
- Remove or consolidate the other

---

**Document Maintained By:** Development Team
**Last Review:** 2025-11-07
**Next Review:** Monthly or after major refactoring

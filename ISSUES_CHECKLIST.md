# PENNY STOCK TRADE - Issues Checklist

**Quick reference for all identified issues with file locations and line numbers**
**Last Updated:** 2025-11-07

---

## CRITICAL ISSUES 🔴 (Fix Immediately - 4-5 hours)

### 1. Duplicate Database Files
- [ ] **REMOVE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\instance\qunextrade.db`
- [ ] **KEEP:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\instance\qunextrade.db`
- [ ] **UPDATE:** All database paths in code to point to root `instance/`
- **Effort:** 30 minutes

### 2. Weak Default SECRET_KEY
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\app.py:68`
- [ ] **CURRENT:** `'dev-secret-key-change-in-production'`
- [ ] **FIX:** Fail fast if `SECRET_KEY` not in environment
```python
# CHANGE FROM:
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# CHANGE TO:
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable must be set")
app.config['SECRET_KEY'] = secret_key
```
- **Effort:** 15 minutes

### 3. Weak Default ADMIN_PASSWORD
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:220`
- [ ] **CURRENT:** `'change-me-in-production'`
- [ ] **FIX:** Require environment variable
```python
# CHANGE FROM:
admin_password = os.getenv('ADMIN_PASSWORD', 'change-me-in-production')

# CHANGE TO:
admin_password = os.getenv('ADMIN_PASSWORD')
if not admin_password:
    return jsonify({'error': 'Admin password not configured'}), 500
```
- **Effort:** 15 minutes

### 4. Debug Print Statements in Production
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py`
  - [ ] Line 72: `print(f"[DEBUG] Login attempt for email: {email}")`
  - [ ] Line 77: `print(f"[DEBUG] User not found: {email}")`
  - [ ] Line 81: `print(f"[DEBUG] User found: {user.username}, checking password...")`
  - [ ] Line 84: `print(f"[DEBUG] Password check failed for {email}")`
  - [ ] Line 88: `print(f"[DEBUG] Login successful for {email}")`
  - [ ] Line 113: `print(f"[DEBUG] Signup attempt - Email: {email}, Username: {username}")`
  - [ ] Line 123: `print(f"[DEBUG] Email already exists: {email}")`
  - [ ] Line 129: `print(f"[DEBUG] Username already taken: {username}")`
  - [ ] Line 143: `print(f"[DEBUG] Creating new user: {username}")`
  - [ ] Line 148: `print(f"[DEBUG] User created successfully: {new_user.id}")`
  - [ ] Line 504: `print(f"❌ Error sending email: {type(e).__name__}: {e}")`
  - [ ] Line 505: `print(f"Full traceback:\n{traceback.format_exc()}")`
  - [ ] Line 509-510: Fallback prints
- **ACTION:** Replace with proper `logging` module
- **Effort:** 1 hour

### 5. Duplicate requirements.txt
- [ ] **REMOVE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\requirements.txt`
- [ ] **KEEP:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\requirements.txt`
- **Effort:** 5 minutes

---

## HIGH PRIORITY ISSUES 🟡 (Fix This Week - 17-18 hours)

### 6. Disabled reCAPTCHA (Security Risk)
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:28-33`
- [ ] **ISSUE:** Function always returns `True` (no bot protection)
- [ ] **FIX:** Fix infinite loop in `recaptcha.js` and re-enable
- [ ] **TODO COMMENT:** Line 31 - "TODO: Fix recaptcha.js form submission infinite loop"
- **Effort:** 2 hours

### 7. Console.log in Production JavaScript
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\static\finviz-data-realtime.js`
  - [ ] Line 62: `console.log('Fetching real-time stock data...')`
  - [ ] Line 70: `console.log('Real-time data fetched successfully:', data)`
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\static\market-overview-realtime.js`
  - [ ] Line 9: `console.log('Fetched market overview data:', data)`
  - [ ] Line 35: `console.log('✓ Market overview updated successfully...')`
  - [ ] Line 70: `console.log('Loading market overview real-time data...')`
  - [ ] Line 77: `console.log('Loading market overview real-time data...')`
- **ACTION:** Remove or wrap in `if (DEBUG)` conditional
- **Effort:** 30 minutes

### 8. Google Analytics Placeholder
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\index.html`
  - [ ] Line 41: `https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX`
  - [ ] Line 46: `gtag('config', 'G-XXXXXXXXXX')`
- **ACTION:** Replace with actual GA ID or remove
- **Effort:** 5 minutes

### 9. Excessive Inline Styles (105 occurrences)
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\index.html` - 26 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\news.html` - 13 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\account.html` - 12 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\pricing.html` - 12 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\market.html` - 8 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\about.html` - 7 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\login.html` - 5 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\signup.html` - 5 inline styles
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\watchlist.html` - 5 inline styles
- [ ] **FILE:** Others - 27 more inline styles
- **ACTION:** Move all to CSS files
- **Effort:** 4 hours

### 10. Duplicate CSS Variables
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\static\theme.css` (lines 14-45)
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\static\basic.css` (lines 14-37)
- **ISSUE:** Both files define identical CSS variables (:root)
- **ACTION:** Consolidate to ONE file (choose theme.css), remove from basic.css
- **Effort:** 1 hour

### 11. Long Function: send_verification_code()
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:371-516` (145 lines!)
- **ISSUE:** Entire HTML email template inline (lines 407-499)
- **ACTION:** Extract HTML to separate Jinja2 template file
- **Effort:** 2 hours

### 12. Long Function: forgot_password()
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:549-628` (79 lines)
- **ISSUE:** HTML email template inline (lines 600-621)
- **ACTION:** Extract HTML to separate Jinja2 template file
- **Effort:** 1 hour

### 13. Hardcoded Configuration Values
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\app.py`
  - [ ] Line 28: `RATE_LIMITS = {"daily": 200, "hourly": 50, "auth_per_minute": 10}`
  - [ ] Line 29: `NEWS_COLLECTION_HOURS = 24`
  - [ ] Line 30: `NEWS_ANALYSIS_LIMIT = 50`
  - [ ] Line 31: `CALENDAR_DAYS_AHEAD = 60`
  - [ ] Line 32: `AUTO_REFRESH_INTERVAL = 3600`
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\payments.py`
  - [ ] Lines 22-47: `PRICING` dictionary
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\polygon_service.py`
  - [ ] Lines 58-65: Cache TTL settings
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_polygon.py`
  - [ ] Lines 189-201: Sector stocks mapping
- **ACTION:** Move to `.env` or config file
- **Effort:** 2 hours

### 14. Missing Type Hints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\app.py` - No type hints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py` - No type hints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\payments.py` - No type hints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_polygon.py` - No type hints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_watchlist.py` - No type hints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\database.py` - No type hints
- **ACTION:** Add type hints to all functions
- **Effort:** 3 hours

---

## MEDIUM PRIORITY ISSUES 🟢 (Fix This Month - 37 hours)

### 15. Insecure Admin Endpoint
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:215-244`
- **ISSUES:**
  - [ ] Password passed in query string (visible in logs)
  - [ ] No rate limiting
  - [ ] No IP whitelist
- **ACTION:** Use session-based auth, require admin role
- **Effort:** 2 hours

### 16. Missing Rate Limiting on API Endpoints
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_polygon.py` - All `/api/market/*` routes
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_watchlist.py` - All `/api/watchlist/*` routes
- **ACTION:** Add `@limiter.limit()` decorators
- **Effort:** 2 hours

### 17. Duplicate Data Directories
- [ ] **REMOVE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\data\`
- [ ] **KEEP:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\data\`
- [ ] **UPDATE:** All data paths in code
- **Effort:** 30 minutes

### 18. Misplaced Debug Files
- [ ] **MOVE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\test-theme.html` → `dev/`
- [ ] **MOVE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\THEME_DEBUG.html` → `dev/`
- [ ] **CREATE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\dev\` directory
- **Effort:** 10 minutes

### 19. Unused Import
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:13`
- [ ] **LINE:** `import requests`
- **ISSUE:** Only used in disabled `verify_recaptcha()` function
- **ACTION:** Remove or re-enable reCAPTCHA
- **Effort:** 5 minutes (after fixing reCAPTCHA)

### 20. N+1 Query Problem in Watchlist
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_watchlist.py:29-31`
```python
for item in watchlist_items:
    quote = polygon.get_stock_quote(item.ticker)  # Sequential API calls
```
- **ISSUE:** Makes N API calls for N stocks
- **ACTION:** Use batch quote endpoint
- **Effort:** 2 hours

### 21. Email HTML Injection Risk
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:407-499`
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\auth.py:600-621`
- **ISSUE:** `{user.username}` in HTML not escaped
- **ACTION:** Use Jinja2 templates with autoescaping
- **Effort:** Covered in item #11-12

### 22. API Key Exposure
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\api_polygon.py:314`
```python
api_key_preview = f"{os.getenv('POLYGON_API_KEY', '')[:8]}..."
```
- **ACTION:** Remove API key preview or require authentication
- **Effort:** 15 minutes

### 23. Missing Accessibility Features
- [ ] **All HTML Templates** - Missing ARIA labels on interactive elements
- [ ] **All HTML Templates** - Some images missing alt attributes
- [ ] **CSS Files** - Focus indicators not visible
- [ ] **HTML Templates** - Use semantic HTML (header, nav, main, section)
- **Effort:** 4 hours

### 24. No Minification/Bundling
- [ ] **CSS Files** (5 files, 1,243 lines) - Not minified, not bundled
- [ ] **JS Files** (7 files + D3) - Not minified, not bundled
- **ACTION:** Set up build process (webpack/rollup)
- **Effort:** 3 hours

### 25. Missing Unit Tests
- [ ] **All Python Modules** - No test files found
- [ ] **Create:** `tests/` directory
- [ ] **Create:** Test files for critical modules
- **Effort:** 20 hours

### 26. Long Function: screen_stocks()
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\polygon_service.py:519-581` (62 lines)
- **ACTION:** Split into smaller functions
- **Effort:** 1 hour

---

## LOW PRIORITY ISSUES ⚪ (Nice to Have - 32 hours)

### 27. Incomplete Stripe Integration
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\payments.py`
- **ISSUE:** Stripe integration not fully implemented (mocked)
- **Effort:** 8 hours

### 28. No Redis Caching
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\polygon_service.py`
- **CURRENT:** In-memory `SimpleCache`
- **ENHANCEMENT:** Use Redis for production
- **Effort:** 4 hours

### 29. No CI/CD Pipeline
- [ ] **CREATE:** `.github/workflows/` directory
- [ ] **CREATE:** GitHub Actions for testing
- [ ] **CREATE:** GitHub Actions for deployment
- **Effort:** 6 hours

### 30. No API Documentation
- [ ] **CREATE:** OpenAPI/Swagger docs for API endpoints
- [ ] **TOOLS:** Use Flask-RESTX or similar
- **Effort:** 8 hours

### 31. Admin Dashboard Improvements
- [ ] **FILE:** `c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE\web\templates\admin_dashboard.html`
- **ENHANCEMENTS:** Better charts, user analytics, system health
- **Effort:** 4 hours

### 32. Dark Mode Testing
- [ ] **CREATE:** Test suite for theme switching
- [ ] **TEST:** localStorage persistence
- [ ] **TEST:** No flash of wrong theme
- **Effort:** 2 hours

---

## SUMMARY CHECKLIST

### Critical (5 issues) - 4-5 hours
- [ ] 1. Duplicate database files
- [ ] 2. Weak SECRET_KEY
- [ ] 3. Weak ADMIN_PASSWORD
- [ ] 4. Debug print statements
- [ ] 5. Duplicate requirements.txt

### High Priority (9 issues) - 17-18 hours
- [ ] 6. Disabled reCAPTCHA
- [ ] 7. Production console.logs
- [ ] 8. Google Analytics placeholder
- [ ] 9. Inline styles (105 occurrences)
- [ ] 10. Duplicate CSS variables
- [ ] 11. Long function: send_verification_code()
- [ ] 12. Long function: forgot_password()
- [ ] 13. Hardcoded configuration
- [ ] 14. Missing type hints

### Medium Priority (8 issues) - 37 hours
- [ ] 15. Insecure admin endpoint
- [ ] 16. Missing rate limiting
- [ ] 17. Duplicate data directories
- [ ] 18. Misplaced debug files
- [ ] 19. Unused import
- [ ] 20. N+1 query problem
- [ ] 21-22. Security issues (covered in other items)
- [ ] 23. Accessibility
- [ ] 24. No minification
- [ ] 25. No unit tests
- [ ] 26. Long function: screen_stocks()

### Low Priority (6 issues) - 32 hours
- [ ] 27. Incomplete Stripe
- [ ] 28. Redis caching
- [ ] 29. CI/CD
- [ ] 30. API docs
- [ ] 31. Admin dashboard
- [ ] 32. Dark mode tests

---

**Total Issues:** 32
**Total Estimated Effort:** ~90 hours
**Priority Distribution:**
- 🔴 Critical: 5 issues (5 hours)
- 🟡 High: 9 issues (18 hours)
- 🟢 Medium: 12 issues (37 hours)
- ⚪ Low: 6 issues (32 hours)

---

**Last Updated:** 2025-11-07
**Checklist Version:** 1.0

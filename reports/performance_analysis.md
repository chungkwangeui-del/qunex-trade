# Performance Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {summary.get('by_severity', {}).get('critical', 0)} |
| 🟠 High | {summary.get('by_severity', {}).get('high', 0)} |
| 🟡 Medium | {summary.get('by_severity', {}).get('medium', 0)} |
| 🟢 Low | {summary.get('by_severity', {}).get('low', 0)} |
| **Total** | **{summary.get('total', 0)}** |

## Issues by Type

- **Pandas Iterrows**: 4
- **String Concat Loop**: 1
- **Read Entire File**: 1
- **Global Import In Function**: 13
- **Synchronous Io**: 18
- **Unnecessary List Conversion**: 7
- **Exception In Loop**: 32

## Top Issues to Address

### 🟠 Using iterrows() on DataFrame

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_earnings.py` (line 138)

**Impact:** Significant performance loss

**Suggestion:** Use vectorized operations, apply(), or itertuples()

```python
                for idx, row in hist.iterrows():
                    earnings_history.append({
                        "date": str(idx) if hasattr(idx, '__str__') else str(idx),
                      
```

---

### 🟠 Using iterrows() on DataFrame

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_earnings.py` (line 153)

**Impact:** Significant performance loss

**Suggestion:** Use vectorized operations, apply(), or itertuples()

```python
                for idx, row in q_earnings.iterrows():
                    quarterly.append({
                        "quarter": str(idx),
                        "revenue": row.get("Revenue"),
```

---

### 🟠 Using iterrows() on DataFrame

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_options.py` (line 180)

**Impact:** Significant performance loss

**Suggestion:** Use vectorized operations, apply(), or itertuples()

```python
                    for _, row in opts.calls.iterrows():
                        volume = int(row.get("volume", 0)) if row.get("volume") else 0
                        oi = int(row.get("openInterest",
```

---

### 🟠 Using iterrows() on DataFrame

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_options.py` (line 200)

**Impact:** Significant performance loss

**Suggestion:** Use vectorized operations, apply(), or itertuples()

```python
                    for _, row in opts.puts.iterrows():
                        volume = int(row.get("volume", 0)) if row.get("volume") else 0
                        oi = int(row.get("openInterest", 
```

---

### 🟠 String concatenation in loop

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\agents\autonomous\advanced_systems.py` (line 456)

**Impact:** O(n²) → O(n)

**Suggestion:** Use list comprehension with join(), or StringIO

```python
        for func in functions:
            test_content += '''
class Test{func.title().replace('_', '')}:
    """Tests for {func}"""
```

---

### 🟡 Reading entire file into memory

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\agents\codebase_knowledge.py` (line 378)

**Impact:** Memory usage

**Suggestion:** Consider streaming with iterators for large files

```python
                content = f.read()

            tree = ast.parse(content)

```

---

### 🟡 Import inside function

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\agents\scheduler.py` (line 35)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
    def __init__(self, check_interval: int = 30):
        """
        Initialize scheduler.

```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\scripts\cron_refresh_insider.py` (line 146)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code != 200:
                        logger.warning(f"Failed to fetch insider data f
```

---

### 🟡 Import inside function

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\scripts\refresh_data_cron.py` (line 33)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
def refresh_news_data():
    """
    Fetch and analyze latest news articles from Polygon News API.

```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\scripts\refresh_data_cron.py` (line 264)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            api_data = response.json()
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\src\news_collector.py` (line 87)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\advanced_sr_analysis.py` (line 107)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\advanced_sr_analysis.py` (line 132)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code == 451:  # Geo-restricted
                        continue
```

---

### 🟡 Import inside function

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_chat.py` (line 42)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
    def polygon(self):
        """Lazy-load polygon service to avoid initialization issues"""
        if self._polygon is None:
            self._polygon = get_polygon_service()
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_flow.py` (line 57)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

```

---

### 🟡 Import inside function

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 19)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
def get_news():
    """Get all news articles"""
    articles = DatabaseService.get_news_articles(limit=50)
    return jsonify({"success": True, "articles": articles})
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 152)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            resp = requests.get("https://api.twelvedata.com/quote", params={"symbol": "AAPL", "apikey": twelvedata_key}, timeout=10)
            if resp.status_code == 200:
                data = resp
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 162)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
        resp = requests.get("https://api.binance.us/api/v3/ping", timeout=5)
        if resp.status_code == 200:
            status["binance"] = {"connected": True, "message": "OK: Binance.US working"
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 177)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            resp = requests.get(f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={finnhub_key}", timeout=5)
            if resp.status_code == 200:
                status["finnhub"] = {"conn
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_market_features.py` (line 62)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params={"symbol": tickers_str, "apikey": twelvedata_key}, timeout=15)

            if response.ok:
                data = response.json()
```

---

## General Optimization Tips

1. **Use appropriate data structures**
   - Set for membership testing
   - Dict for key-value lookups
   - Deque for queue operations

2. **Vectorize operations**
   - Use NumPy/Pandas vectorization instead of loops
   - Use list comprehensions over append loops

3. **Minimize I/O**
   - Batch database queries
   - Use async I/O for concurrent operations
   - Cache frequently accessed data

4. **Profile before optimizing**
   - Use cProfile or line_profiler
   - Focus on actual bottlenecks

---
*Report generated by Performance Optimizer*

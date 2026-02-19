# Performance Analysis Report

Generated: 2026-02-19 01:17:04

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 0 |
| 🟠 High | 0 |
| 🟡 Medium | 22 |
| 🟢 Low | 39 |
| **Total** | **61** |

## Issues by Type

- **Read Entire File**: 1
- **Global Import In Function**: 4
- **Synchronous Io**: 17
- **Unnecessary List Conversion**: 7
- **Exception In Loop**: 32

## Top Issues to Address

### 🟡 Reading entire file into memory

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\agents\codebase_knowledge.py` (line 387)

**Impact:** Memory usage

**Suggestion:** Consider streaming with iterators for large files

```python
                content = f.read()
                line_count = len(content.splitlines())

            tree = ast.parse(content)
```

---

### 🟡 Import inside function

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\agents\scheduler.py` (line 39)

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

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\scripts\refresh_data_cron.py` (line 258)

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

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 149)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            resp = requests.get("https://api.twelvedata.com/quote", params={"symbol": "AAPL", "apikey": twelvedata_key}, timeout=10)
            if resp.status_code == 200:
                data = resp
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 159)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
        resp = requests.get("https://api.binance.us/api/v3/ping", timeout=5)
        if resp.status_code == 200:
            status["binance"] = {"connected": True, "message": "OK: Binance.US working"
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_main.py` (line 174)

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

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_portfolio.py` (line 54)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params={"symbol": ticker, "apikey": twelvedata_key}, timeout=10)
            if response.ok:
                data = response.json()
                if data and
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_portfolio.py` (line 67)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params={"symbol": ticker, "token": finnhub_key}, timeout=5)
            if response.ok:
                data = response.json()
                if data and data
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\api_swing.py` (line 129)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\indices_service.py` (line 82)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 429:
                logger.error("[Indices] Rate limit exceeded (5 calls/minute)")
```

---

### 🟡 Import inside function

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\web\utils.py` (line 89)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
def rate_limit(calls_per_minute: int = 60):
    """
    Simple rate limiter decorator for API calls.

```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\src\services\market_data_service.py` (line 160)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\src\services\scalp_engine.py` (line 1234)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                response = requests.get(url, params=params, timeout=10)

                # Skip to next endpoint if geo-restricted (451)
                if response.status_code == 451:
```

---

### 🟡 Synchronous HTTP requests

**File:** `C:\Users\chung\.openclaw\workspace\qunex-trade\src\services\scalp_engine.py` (line 1291)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
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

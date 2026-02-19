# Performance Analysis Report

Generated: 2026-02-19 03:17:01

## Summary

| Severity | Count |
|----------|-------|
| [CRITICAL] | 0 |
| [HIGH] | 0 |
| [MEDIUM] | 19 |
| [LOW] | 39 |
| TOTAL | 58 |

## Issues by Type

- Read Entire File: 1
- Global Import In Function: 3
- Synchronous Io: 15
- Unnecessary List Conversion: 7
- Exception In Loop: 32

## Top Issues to Address

### [MEDIUM] Reading entire file into memory

**File:** qunex-trade\agents\codebase_knowledge.py (line 387)

**Impact:** Memory usage

**Suggestion:** Consider streaming with iterators for large files

```python
                content = f.read()
                line_count = len(content.splitlines())

            tree = ast.parse(content)
```

---

### [MEDIUM] Import inside function

**File:** qunex-trade\agents\scheduler.py (line 39)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
    def __init__(self, check_interval: int = 30):
        """
        Initialize scheduler.

```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\scripts\cron_refresh_insider.py (line 156)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code != 200:
                            logger.warning(f"Failed to fetch ins
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\scripts\refresh_data_cron.py (line 258)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            api_data = response.json()
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\src\news_collector.py (line 87)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\advanced_sr_analysis.py (line 107)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\advanced_sr_analysis.py (line 132)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code == 451:  # Geo-restricted
                        continue
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\api_flow.py (line 71)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\api_main.py (line 169)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                resp = requests.get("https://api.twelvedata.com/quote", params={"symbol": "AAPL", "apikey": twelvedata_key}, timeout=10)
                if resp.status_code == 200:
                   
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\api_main.py (line 189)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            resp = requests.get("https://api.binance.us/api/v3/ping", timeout=5)
            if resp.status_code == 200:
                status["binance"] = {"connected": True, "message": "OK: Binance
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\api_main.py (line 209)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                resp = requests.get(f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={finnhub_key}", timeout=5)
                if resp.status_code == 200:
                    status["finnhu
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\api_market_features.py (line 62)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params={"symbol": tickers_str, "apikey": twelvedata_key}, timeout=15)

            if response.ok:
                data = response.json()
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\api_swing.py (line 129)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\web\indices_service.py (line 100)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 429:
                        logger.error("[Indices] Rate limit exceeded (5 c
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\src\services\market_data_service.py (line 160)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\src\services\scalp_engine.py (line 1234)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
                response = requests.get(url, params=params, timeout=10)

                # Skip to next endpoint if geo-restricted (451)
                if response.status_code == 451:
```

---

### [MEDIUM] Synchronous HTTP requests

**File:** qunex-trade\src\services\scalp_engine.py (line 1291)

**Impact:** Blocking I/O

**Suggestion:** Consider async with aiohttp for concurrent requests

```python
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

```

---

### [MEDIUM] Import inside function

**File:** qunex-trade\agents\autonomous\advanced_systems.py (line 71)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
    def record_cycle(self):
        """Record a cycle completion."""
        self.current_stats['cycles_run'] += 1

```

---

### [MEDIUM] Import inside function

**File:** qunex-trade\agents\autonomous\code_generator.py (line 80)

**Impact:** Repeated import overhead

**Suggestion:** Move import to module level (unless conditional)

```python
def index():
    """Main page for {name}."""
    return render_template("{name}/index.html")

```

---

### [LOW] Unnecessary list(dict.keys())

**File:** qunex-trade\agents\base.py (line 315)

**Impact:** Unnecessary memory allocation

**Suggestion:** Iterate directly over dict

```python
            "categories": list(by_category.keys()),
            "agents_by_category": by_category,
        }

```

---

## General Optimization Tips

1. Use appropriate data structures
2. Vectorize operations
3. Minimize IO
4. Profile before optimizing

---
*Report generated by Performance Optimizer*
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

- **Pandas Iterrows**: 2
- **String Concat Loop**: 1
- **Read Entire File**: 1
- **Global Import In Function**: 13
- **Synchronous Io**: 18
- **Unnecessary List Conversion**: 7
- **Exception In Loop**: 32

## Top Issues to Address

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
```

---

### {severity_icon} {issue.description}

**File:** `{issue.file_path}` (line {issue.line_number})

**Impact:** {issue.estimated_impact}

**Suggestion:** {issue.suggestion}

```python
{issue.code_snippet}
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

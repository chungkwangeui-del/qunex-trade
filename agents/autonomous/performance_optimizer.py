"""
Performance Optimizer
Detects and suggests fixes for performance issues in code.
"""
import re
import ast
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceIssue:
    """A detected performance issue."""
    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # low, medium, high, critical
    suggestion: str
    code_snippet: str = ""
    estimated_impact: str = ""


@dataclass
class OptimizationResult:
    """Result of an optimization attempt."""
    file_path: str
    issue_type: str
    optimized: bool
    original_code: str
    new_code: str


class PerformanceOptimizer:
    """
    Analyzes code for performance issues and suggests optimizations.
    """

    PERFORMANCE_PATTERNS = [
        {
            'name': 'string_concat_loop',
            'pattern': r'for\s+\w+\s+in\s+.*:\s*\n\s*\w+\s*\+=\s*["\']',
            'description': 'String concatenation in loop',
            'severity': 'high',
            'suggestion': 'Use list comprehension with join(), or StringIO',
            'impact': 'O(n²) → O(n)'
        },
        {
            'name': 'list_in_loop',
            'pattern': r'for\s+\w+\s+in\s+\w+:\s*\n\s*if\s+\w+\s+in\s+\[',
            'description': 'List membership check in loop',
            'severity': 'high',
            'suggestion': 'Convert list to set for O(1) lookups',
            'impact': 'O(n×m) → O(n)'
        },
        {
            'name': 'nested_loops',
            'pattern': r'for\s+\w+\s+in\s+.*:\s*\n\s+for\s+\w+\s+in\s+.*:\s*\n\s+for\s+\w+\s+in',
            'description': 'Triple nested loop detected',
            'severity': 'critical',
            'suggestion': 'Consider algorithm optimization or data structure change',
            'impact': 'O(n³) complexity'
        },
        {
            'name': 'repeated_computation',
            'pattern': r'for\s+\w+\s+in\s+.*:\s*\n(?:.*\n)*?\s*len\(\w+\)',
            'description': 'len() called inside loop',
            'severity': 'low',
            'suggestion': 'Cache length before loop',
            'impact': 'Minor - depends on object type'
        },
        {
            'name': 'global_import_in_function',
            'pattern': r'def\s+\w+\([^)]*\):\s*\n(?:\s*#.*\n|\s*"""[\s\S]*?"""|\s*\'\'\'[\s\S]*?\'\'\')?\s*import\s+',
            'description': 'Import inside function',
            'severity': 'medium',
            'suggestion': 'Move import to module level (unless conditional)',
            'impact': 'Repeated import overhead'
        },
        {
            'name': 'unnecessary_list_conversion',
            'pattern': r'list\(\w+\.keys\(\)\)',
            'description': 'Unnecessary list(dict.keys())',
            'severity': 'low',
            'suggestion': 'Iterate directly over dict',
            'impact': 'Unnecessary memory allocation'
        },
        {
            'name': 'read_entire_file',
            'pattern': r'\.read\(\)\s*$',
            'description': 'Reading entire file into memory',
            'severity': 'medium',
            'suggestion': 'Consider streaming with iterators for large files',
            'impact': 'Memory usage'
        },
        {
            'name': 'regex_in_loop',
            'pattern': r'for\s+\w+\s+in\s+.*:\s*\n(?:.*\n)*?\s*re\.(?:search|match|findall)\(',
            'description': 'Regex compilation in loop',
            'severity': 'medium',
            'suggestion': 'Pre-compile regex with re.compile() outside loop',
            'impact': 'Regex compilation overhead'
        },
        {
            'name': 'exception_in_loop',
            'pattern': r'for\s+\w+\s+in\s+.*:\s*\n\s*try:',
            'description': 'Try/except inside loop',
            'severity': 'low',
            'suggestion': 'Move try/except outside loop if possible',
            'impact': 'Exception handling overhead'
        },
        {
            'name': 'append_in_comprehension',
            'pattern': r'\[\w+\.append\(',
            'description': 'append() in list comprehension',
            'severity': 'medium',
            'suggestion': 'Use list comprehension properly or extend()',
            'impact': 'Inefficient pattern'
        },
        {
            'name': 'synchronous_io',
            'pattern': r'requests\.(?:get|post|put|delete)\(',
            'description': 'Synchronous HTTP requests',
            'severity': 'medium',
            'suggestion': 'Consider async with aiohttp for concurrent requests',
            'impact': 'Blocking I/O'
        },
        {
            'name': 'pandas_iterrows',
            'pattern': r'\.iterrows\(\)',
            'description': 'Using iterrows() on DataFrame',
            'severity': 'high',
            'suggestion': 'Use vectorized operations, apply(), or itertuples()',
            'impact': 'Significant performance loss'
        },
        {
            'name': 'plus_equals_dataframe',
            'pattern': r'df\s*=\s*pd\.concat\(\[df',
            'description': 'Concatenating DataFrames in loop',
            'severity': 'high',
            'suggestion': 'Collect in list and concat once at end',
            'impact': 'O(n²) memory operations'
        }
    ]

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.issues: List[PerformanceIssue] = []
        self.optimizations: List[OptimizationResult] = []

    def analyze_file(self, file_path: Path) -> List[PerformanceIssue]:
        """Analyze a file for performance issues."""
        issues = []

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            for pattern_info in self.PERFORMANCE_PATTERNS:
                matches = list(re.finditer(
                    pattern_info['pattern'],
                    content,
                    re.MULTILINE
                ))

                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1

                    # Get code snippet
                    start_line = max(0, line_num - 1)
                    end_line = min(len(lines), line_num + 3)
                    snippet = '\n'.join(lines[start_line:end_line])

                    issue = PerformanceIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type=pattern_info['name'],
                        description=pattern_info['description'],
                        severity=pattern_info['severity'],
                        suggestion=pattern_info['suggestion'],
                        code_snippet=snippet[:200],
                        estimated_impact=pattern_info.get('impact', '')
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return issues

    def analyze_project(self) -> List[PerformanceIssue]:
        """Analyze entire project for performance issues."""
        try:
            print("  Analyzing performance...")
        except UnicodeEncodeError:
            print("  Analyzing performance...")

        all_issues = []

        # Find all Python files
        py_files = list(self.project_root.rglob("*.py"))

        # Exclude common directories
        exclude_dirs = {'venv', 'env', '.venv', 'node_modules', '__pycache__', '.git'}
        py_files = [f for f in py_files if not any(d in f.parts for d in exclude_dirs)]

        for file_path in py_files[:100]:  # Limit to 100 files
            issues = self.analyze_file(file_path)
            all_issues.extend(issues)

        self.issues = all_issues

        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        self.issues.sort(key=lambda x: severity_order.get(x.severity, 4))

        try:
            print(f"     Found {len(all_issues)} performance issues")
        except UnicodeEncodeError:
            print(f"     Found {len(all_issues)} performance issues")

        return all_issues

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of performance issues."""
        if not self.issues:
            return {'status': 'no_issues', 'total': 0}

        by_severity = {
            'critical': sum(1 for i in self.issues if i.severity == 'critical'),
            'high': sum(1 for i in self.issues if i.severity == 'high'),
            'medium': sum(1 for i in self.issues if i.severity == 'medium'),
            'low': sum(1 for i in self.issues if i.severity == 'low')
        }

        by_type = {}
        for issue in self.issues:
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

        return {
            'status': 'ok',
            'total': len(self.issues),
            'by_severity': by_severity,
            'by_type': by_type,
            'top_issues': [
                {
                    'file': i.file_path,
                    'line': i.line_number,
                    'type': i.issue_type,
                    'severity': i.severity
                }
                for i in self.issues[:10]
            ]
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate performance analysis report."""
        output = output_path or Path("reports/performance_analysis.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        summary = self.get_summary()

        # Severity icons mapping - use plain text labels
        severity_labels = {
            'critical': '[CRITICAL]',
            'high': '[HIGH]',
            'medium': '[MEDIUM]',
            'low': '[LOW]'
        }

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Build the report using manual concatenation to be safe
        report = "# Performance Analysis Report\n\n"
        report += "Generated: " + str(now_str) + "\n\n"
        report += "## Summary\n\n"
        report += "| Severity | Count |\n"
        report += "|----------|-------|\n"
        report += "| CRITICAL | " + str(summary.get('by_severity', {}).get('critical', 0)) + " |\n"
        report += "| HIGH | " + str(summary.get('by_severity', {}).get('high', 0)) + " |\n"
        report += "| MEDIUM | " + str(summary.get('by_severity', {}).get('medium', 0)) + " |\n"
        report += "| LOW | " + str(summary.get('by_severity', {}).get('low', 0)) + " |\n"
        report += "| **Total** | **" + str(summary.get('total', 0)) + "** |\n\n"

        report += "## Issues by Type\n\n"
        for issue_type, count in summary.get('by_type', {}).items():
            report += "- **" + str(issue_type.replace('_', ' ').title()) + "**: " + str(count) + "\n"

        report += "\n## Top Issues to Address\n\n"
        for issue in self.issues[:20]:
            label = severity_labels.get(issue.severity, '[INFO]')
            report += "### " + str(label) + " " + str(issue.description) + "\n\n"
            report += "**File:** `" + str(issue.file_path) + "` (line " + str(issue.line_number) + ")\n\n"
            report += "**Impact:** " + str(issue.estimated_impact) + "\n\n"
            report += "**Suggestion:** " + str(issue.suggestion) + "\n\n"
            report += "```python\n"
            report += str(issue.code_snippet) + "\n"
            report += "```\n\n---\n\n"

        report += "## General Optimization Tips\n\n"
        report += "1. Use appropriate data structures\n"
        report += "2. Vectorize operations\n"
        report += "3. Minimize IO\n"
        report += "4. Profile before optimizing\n\n"
        report += "---\n"
        report += "*Report generated by Performance Optimizer*"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_optimizer(project_root: Optional[Path] = None) -> PerformanceOptimizer:
    """Get or create performance optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer(project_root)
    return _optimizer

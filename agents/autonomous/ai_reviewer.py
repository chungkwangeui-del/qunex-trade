"""
🧠 AI Code Reviewer
Uses AI to provide intelligent code reviews and suggestions.
"""
import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result of an AI code review."""
    file_path: str
    quality_score: float  # 0-100
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    complexity_rating: str = "Low"  # Low, Medium, High, Very High
    maintainability_score: float = 0.0
    test_coverage_suggestion: str = ""


class AICodeReviewer:
    """
    Intelligent code reviewer that analyzes code quality,
    patterns, and provides actionable suggestions.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.reviews: list[ReviewResult] = []
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> dict:
        """Load code review patterns."""
        return {
            'anti_patterns': [
                (r'except\s*:', 'Bare except clause - catch specific exceptions'),
                (r'import \*', 'Star import - import specific names'),
                (r'global\s+\w+', 'Global variable usage - consider dependency injection'),
                (r'eval\s*\(', 'eval() usage - security risk'),
                (r'exec\s*\(', 'exec() usage - security risk'),
                (r'print\s*\((?!.*#\s*debug)', 'print() in production - use logging'),
                (r'time\.sleep\s*\(\d{2,}\)', 'Long sleep - consider async/event-based'),
                (r'\.read\(\)\s*$', 'Reading entire file - consider streaming'),
                (r'except.*pass\s*$', 'Silent exception - log or handle properly'),
                (r'TODO|FIXME|HACK|XXX', 'Unresolved marker comment'),
            ],
            'best_practices': [
                (r'def \w+\([^)]*\)\s*->', 'Type hints present', True),
                (r'"""[\s\S]*?"""', 'Docstring present', True),
                (r'logging\.(debug|info|warning|error)', 'Proper logging used', True),
                (r'with\s+open\s*\(', 'Context manager for files', True),
                (r'@dataclass', 'Dataclass usage', True),
                (r'async def', 'Async pattern usage', True),
                (r'from typing import', 'Type imports', True),
            ],
            'security': [
                (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
                (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
                (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
                (r'SELECT.*\+.*user', 'Potential SQL injection'),
                (r'shell\s*=\s*True', 'Shell injection risk'),
                (r'verify\s*=\s*False', 'SSL verification disabled'),
            ],
            'performance': [
                (r'for.*in.*\.keys\(\)', 'Unnecessary .keys() call'),
                (r'\+\s*=.*in\s+.*loop', 'String concatenation in loop'),
                (r'\.append\(.*\)\s*$.*for', 'Consider list comprehension'),
                (r'len\(\w+\)\s*==\s*0', 'Use "if not x" instead of len(x)==0'),
                (r'len\(\w+\)\s*>\s*0', 'Use "if x" instead of len(x)>0'),
            ]
        }

    async def review_file(self, file_path: Path) -> ReviewResult:
        """Review a single file."""
        result = ReviewResult(
            file_path=str(file_path),
            quality_score=100.0,
            issues=[],
            suggestions=[]
        )

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            # Analyze code metrics
            metrics = self._analyze_metrics(content, lines)

            # Check anti-patterns
            for pattern, message in self.patterns['anti_patterns']:
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    result.issues.append({
                        'type': 'anti_pattern',
                        'line': line_num,
                        'message': message,
                        'severity': 'warning'
                    })
                    result.quality_score -= 2

            # Check security issues
            for pattern, message in self.patterns['security']:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    result.issues.append({
                        'type': 'security',
                        'line': line_num,
                        'message': message,
                        'severity': 'critical'
                    })
                    result.quality_score -= 10

            # Check performance issues
            for pattern, message in self.patterns['performance']:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    result.issues.append({
                        'type': 'performance',
                        'line': line_num,
                        'message': message,
                        'severity': 'info'
                    })
                    result.quality_score -= 1

            # Check best practices (bonus points)
            for pattern, message, is_good in self.patterns['best_practices']:
                if re.search(pattern, content):
                    result.suggestions.append({
                        'type': 'best_practice',
                        'message': f"✅ {message}",
                        'positive': True
                    })
                    result.quality_score = min(100, result.quality_score + 1)

            # Set complexity rating
            result.complexity_rating = metrics['complexity_rating']
            result.maintainability_score = metrics['maintainability']

            # Generate test coverage suggestion
            if metrics['has_functions'] and not metrics['has_tests']:
                result.test_coverage_suggestion = f"Consider adding tests for {metrics['function_count']} functions"

            # Ensure score is within bounds
            result.quality_score = max(0, min(100, result.quality_score))

        except Exception as e:
            logger.error(f"Error reviewing {file_path}: {e}")
            result.issues.append({
                'type': 'error',
                'message': str(e),
                'severity': 'error'
            })

        return result

    def _analyze_metrics(self, content: str, lines: list) -> dict:
        """Analyze code metrics."""
        # Count functions/classes
        functions = re.findall(r'^(?:async\s+)?def\s+(\w+)', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)

        # Calculate cyclomatic complexity approximation
        complexity_indicators = len(re.findall(r'\b(if|elif|for|while|except|and|or)\b', content))

        # Determine complexity rating
        if complexity_indicators < 10:
            complexity_rating = "Low"
        elif complexity_indicators < 25:
            complexity_rating = "Medium"
        elif complexity_indicators < 50:
            complexity_rating = "High"
        else:
            complexity_rating = "Very High"

        # Calculate maintainability
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        comments = len([l for l in lines if l.strip().startswith('#')])
        docstrings = len(re.findall(r'"""[\s\S]*?"""', content))

        doc_ratio = (comments + docstrings * 3) / max(loc, 1)
        maintainability = min(100, 50 + doc_ratio * 100)

        # Check for tests
        has_tests = 'test_' in content.lower() or 'pytest' in content.lower()

        return {
            'function_count': len(functions),
            'class_count': len(classes),
            'loc': loc,
            'complexity_rating': complexity_rating,
            'maintainability': maintainability,
            'has_functions': len(functions) > 0,
            'has_tests': has_tests
        }

    async def review_project(self, path: Optional[Path] = None) -> dict:
        """Review entire project."""
        target = path or self.project_root
        results = []

        # Find all Python files
        py_files = list(target.rglob("*.py"))

        # Filter out unwanted directories
        exclude_dirs = {'venv', 'env', '.venv', 'node_modules', '__pycache__', '.git', 'migrations'}
        py_files = [f for f in py_files if not any(d in f.parts for d in exclude_dirs)]

        print(f"  🔍 Reviewing {len(py_files)} files...")

        # Review files concurrently
        tasks = [self.review_file(f) for f in py_files[:100]]  # Limit to 100 files
        results = await asyncio.gather(*tasks)

        self.reviews = results

        # Calculate summary
        avg_quality = sum(r.quality_score for r in results) / max(len(results), 1)
        total_issues = sum(len(r.issues) for r in results)
        critical_issues = sum(1 for r in results for i in r.issues if i.get('severity') == 'critical')

        return {
            'files_reviewed': len(results),
            'average_quality': round(avg_quality, 1),
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'results': results
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate a detailed review report."""
        output = output_path or self.project_root / "reports" / "ai_code_review.md"
        output.parent.mkdir(parents=True, exist_ok=True)

        # Sort results by quality score
        sorted_results = sorted(self.reviews, key=lambda x: x.quality_score)

        avg_quality = sum(r.quality_score for r in self.reviews) / max(len(self.reviews), 1)

        report = """# 🧠 AI Code Review Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | {len(self.reviews)} |
| Average Quality | {avg_quality:.1f}/100 |
| Critical Issues | {sum(1 for r in self.reviews for i in r.issues if i.get('severity') == 'critical')} |
| Total Issues | {sum(len(r.issues) for r in self.reviews)} |

## Quality Grade

"""
        # Add grade
        if avg_quality >= 90:
            report += "### 🏆 A - Excellent\n"
        elif avg_quality >= 80:
            report += "### ✅ B - Good\n"
        elif avg_quality >= 70:
            report += "### ⚠️ C - Needs Improvement\n"
        elif avg_quality >= 60:
            report += "### ❌ D - Poor\n"
        else:
            report += "### 🚨 F - Critical\n"

        # Top issues
        report += "\n## Top Issues to Fix\n\n"

        issue_count = 0
        for result in sorted_results:
            for issue in result.issues:
                if issue.get('severity') in ('critical', 'warning') and issue_count < 20:
                    severity_icon = "🔴" if issue['severity'] == 'critical' else "🟠"
                    report += f"- {severity_icon} **{Path(result.file_path).name}** (line {issue.get('line', '?')}): {issue['message']}\n"
                    issue_count += 1

        # Files needing attention
        report += "\n## Files Needing Attention\n\n"
        for result in sorted_results[:10]:
            if result.quality_score < 80:
                report += f"- **{result.file_path}** - Score: {result.quality_score:.0f}/100 ({len(result.issues)} issues)\n"

        # Best practices found
        report += "\n## Best Practices Detected ✅\n\n"
        practices = set()
        for result in self.reviews:
            for sug in result.suggestions:
                if sug.get('positive'):
                    practices.add(sug['message'])

        for practice in list(practices)[:15]:
            report += f"- {practice}\n"

        report += "\n---\n*Report generated by AI Code Reviewer*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_reviewer: Optional[AICodeReviewer] = None

def get_reviewer(project_root: Optional[Path] = None) -> AICodeReviewer:
    """Get or create reviewer instance."""
    global _reviewer
    if _reviewer is None:
        _reviewer = AICodeReviewer(project_root)
    return _reviewer



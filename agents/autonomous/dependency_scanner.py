"""
🔍 Dependency Scanner
Scans project dependencies for vulnerabilities and updates.
"""
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """A project dependency."""
    name: str
    version: str
    latest_version: str = ""
    has_update: bool = False
    is_vulnerable: bool = False
    vulnerability_info: str = ""
    severity: str = "none"  # none, low, medium, high, critical


@dataclass
class ScanResult:
    """Result of dependency scan."""
    total_packages: int = 0
    outdated_count: int = 0
    vulnerable_count: int = 0
    dependencies: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)


class DependencyScanner:
    """
    Scans project dependencies for security vulnerabilities
    and available updates.
    """

    # Known vulnerable packages (sample - in production, use a real vulnerability database)
    KNOWN_VULNERABILITIES = {
        'urllib3': {'affected': '<1.26.5', 'severity': 'high', 'info': 'CRLF injection vulnerability'},
        'requests': {'affected': '<2.20.0', 'severity': 'medium', 'info': 'Session fixation vulnerability'},
        'flask': {'affected': '<2.0.0', 'severity': 'medium', 'info': 'Cookie parsing vulnerability'},
        'django': {'affected': '<3.2.0', 'severity': 'high', 'info': 'Multiple security fixes'},
        'pyyaml': {'affected': '<5.4', 'severity': 'critical', 'info': 'Arbitrary code execution'},
        'pillow': {'affected': '<9.0.0', 'severity': 'high', 'info': 'Multiple security fixes'},
        'cryptography': {'affected': '<3.4.0', 'severity': 'high', 'info': 'Security vulnerability'},
        'numpy': {'affected': '<1.22.0', 'severity': 'low', 'info': 'Buffer overflow in some cases'},
        'jinja2': {'affected': '<3.0.0', 'severity': 'medium', 'info': 'XSS vulnerability'},
        'werkzeug': {'affected': '<2.0.0', 'severity': 'medium', 'info': 'Cookie parsing issue'},
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.result = ScanResult()

    def _parse_version(self, version_str: str) -> tuple:
        """Parse version string into comparable tuple."""
        try:
            # Remove any non-numeric prefix
            clean = re.sub(r'^[^0-9]*', '', version_str)
            parts = clean.split('.')
            return tuple(int(p) for p in parts[:3] if p.isdigit())
        except Exception:
            return (0, 0, 0)

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        t1 = self._parse_version(v1)
        t2 = self._parse_version(v2)

        if t1 < t2:
            return -1
        elif t1 > t2:
            return 1
        return 0

    def _is_vulnerable(self, name: str, version: str) -> tuple:
        """Check if a package version is vulnerable."""
        name_lower = name.lower()

        if name_lower in self.KNOWN_VULNERABILITIES:
            vuln = self.KNOWN_VULNERABILITIES[name_lower]
            affected = vuln['affected']

            # Parse affected version range
            if affected.startswith('<'):
                safe_version = affected[1:]
                if self._compare_versions(version, safe_version) < 0:
                    return True, vuln['severity'], vuln['info']

        return False, 'none', ''

    def scan_requirements(self, req_file: Optional[Path] = None) -> ScanResult:
        """Scan requirements.txt for vulnerabilities."""
        req_path = req_file or self.project_root / "requirements.txt"

        if not req_path.exists():
            logger.warning(f"Requirements file not found: {req_path}")
            return self.result

        try:
            content = req_path.read_text(encoding='utf-8')
            lines = content.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('-'):
                    continue

                # Parse package name and version
                match = re.match(r'^([a-zA-Z0-9_-]+)(?:[=<>!]+)?(.*)$', line)
                if match:
                    name = match.group(1)
                    version = match.group(2).strip('=<>! ') or 'latest'

                    # Check for vulnerability
                    is_vuln, severity, info = self._is_vulnerable(name, version)

                    dep = Dependency(
                        name=name,
                        version=version,
                        is_vulnerable=is_vuln,
                        vulnerability_info=info,
                        severity=severity
                    )

                    self.result.dependencies.append(dep)
                    self.result.total_packages += 1

                    if is_vuln:
                        self.result.vulnerable_count += 1
                        self.result.recommendations.append({
                            'priority': severity,
                            'package': name,
                            'message': f'Update {name} - {info}'
                        })

        except Exception as e:
            logger.error(f"Error scanning requirements: {e}")

        return self.result

    def check_outdated(self) -> list:
        """Check for outdated packages using pip."""
        outdated = []

        try:
            result = subprocess.run(
                ['pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                packages = json.loads(result.stdout)

                for pkg in packages:
                    outdated.append({
                        'name': pkg['name'],
                        'current': pkg['version'],
                        'latest': pkg['latest_version']
                    })

                    # Update dependency info
                    for dep in self.result.dependencies:
                        if dep.name.lower() == pkg['name'].lower():
                            dep.latest_version = pkg['latest_version']
                            dep.has_update = True
                            self.result.outdated_count += 1

        except subprocess.TimeoutExpired:
            logger.warning("Pip outdated check timed out")
        except Exception as e:
            logger.error(f"Error checking outdated packages: {e}")

        return outdated

    def full_scan(self) -> ScanResult:
        """Perform full dependency scan."""
        print("  🔍 Scanning dependencies...")

        # Scan requirements.txt
        self.scan_requirements()

        # Check for updates
        self.check_outdated()

        return self.result

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate dependency scan report."""
        output = output_path or Path("reports/dependency_scan.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        report = """# 🔍 Dependency Scan Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Packages | {self.result.total_packages} |
| Outdated | {self.result.outdated_count} |
| Vulnerable | {self.result.vulnerable_count} |

## Security Status

"""
        if self.result.vulnerable_count == 0:
            report += "✅ **No known vulnerabilities detected!**\n\n"
        else:
            report += f"⚠️ **{self.result.vulnerable_count} vulnerable packages found!**\n\n"

            report += "### Vulnerable Packages\n\n"
            report += "| Package | Version | Severity | Issue |\n"
            report += "|---------|---------|----------|-------|\n"

            for dep in self.result.dependencies:
                if dep.is_vulnerable:
                    severity_icon = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(dep.severity, '⚪')

                    report += f"| {dep.name} | {dep.version} | {severity_icon} {dep.severity} | {dep.vulnerability_info} |\n"

        # Outdated packages
        outdated_deps = [d for d in self.result.dependencies if d.has_update]
        if outdated_deps:
            report += "\n## Outdated Packages\n\n"
            report += "| Package | Current | Latest |\n"
            report += "|---------|---------|--------|\n"

            for dep in outdated_deps[:20]:  # Show top 20
                report += f"| {dep.name} | {dep.version} | {dep.latest_version} |\n"

        # Recommendations
        if self.result.recommendations:
            report += "\n## Recommendations\n\n"

            for rec in sorted(self.result.recommendations,
                            key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['priority'], 4)):
                priority_icon = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(rec['priority'], '⚪')

                report += f"- {priority_icon} **{rec['package']}**: {rec['message']}\n"

        report += "\n---\n*Report generated by Dependency Scanner*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)

    def auto_update_safe(self) -> list:
        """Auto-update packages with only patch/minor updates (safe)."""
        updated = []

        for dep in self.result.dependencies:
            if dep.has_update and not dep.is_vulnerable:
                current = self._parse_version(dep.version)
                latest = self._parse_version(dep.latest_version)

                # Only update if major version is same (safe update)
                if current and latest and current[0] == latest[0]:
                    try:
                        result = subprocess.run(
                            ['pip', 'install', '--upgrade', f'{dep.name}=={dep.latest_version}'],
                            capture_output=True,
                            timeout=120
                        )
                        if result.returncode == 0:
                            updated.append(dep.name)
                    except Exception as e:
                        logger.error(f"Error updating {dep.name}: {e}")

        return updated


# Singleton instance
_scanner: Optional[DependencyScanner] = None

def get_dependency_scanner(project_root: Optional[Path] = None) -> DependencyScanner:
    """Get or create dependency scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = DependencyScanner(project_root)
    return _scanner



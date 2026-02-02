"""
Watchdog Agent
==============

Continuously monitors the codebase for:
- File changes
- New errors/issues
- Performance degradation
- Security vulnerabilities

Can trigger automated responses when issues are detected.
"""

import time
import hashlib
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class FileState:
    """Tracks the state of a file."""
    path: str
    hash: str
    size: int
    modified_at: datetime
    issues_count: int = 0

@dataclass
class WatchEvent:
    """Represents a detected event."""
    event_type: str  # file_changed, file_created, file_deleted, issue_found, error
    file_path: Optional[str]
    description: str
    severity: str  # info, warning, error, critical
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)

class WatchdogAgent:
    """
    Monitors the codebase and triggers actions on changes.

    Capabilities:
    - File change detection
    - Automatic issue scanning on changes
    - Error log monitoring
    - Performance tracking
    - Automated fix triggering
    """

    def __init__(self):
        self.name = "watchdog"
        self.project_root = Path(__file__).parent.parent.parent

        # State tracking
        self.file_states: Dict[str, FileState] = {}
        self.events: List[WatchEvent] = []
        self.last_scan: Optional[datetime] = None

        # Configuration
        self.config = {
            "scan_interval_seconds": 60,
            "watch_patterns": ["*.py", "*.html", "*.js", "*.css"],
            "ignore_patterns": [".git", "__pycache__", "node_modules", ".venv", "venv"],
            "max_events": 1000,
            "auto_fix_on_change": True,
            "auto_scan_on_change": True,
        }

        # Event handlers
        self.handlers: Dict[str, List[Callable]] = {
            "file_changed": [],
            "file_created": [],
            "file_deleted": [],
            "issue_found": [],
            "error": [],
        }

        # Running state
        self.running = False
        self.stats = {
            "files_watched": 0,
            "changes_detected": 0,
            "issues_auto_fixed": 0,
            "errors_caught": 0,
        }

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        if event_type in self.handlers:
            self.handlers[event_type].append(handler)

    async def start_watching(self) -> None:
        """Start the watchdog monitoring loop."""
        self.running = True

        # Initial scan
        await self._full_scan()

        logger.info(f"Watchdog started, monitoring {self.stats['files_watched']} files")

        while self.running:
            try:
                # Check for changes
                changes = await self._check_for_changes()

                if changes:
                    await self._process_changes(changes)

                await asyncio.sleep(self.config["scan_interval_seconds"])

            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                self._add_event(WatchEvent(
                    event_type="error",
                    file_path=None,
                    description=f"Watchdog error: {e}",
                    severity="error",
                ))
                await asyncio.sleep(5)

    def stop_watching(self) -> None:
        """Stop the watchdog."""
        self.running = False
        logger.info("Watchdog stopped")

    async def _full_scan(self) -> None:
        """Perform a full scan of all watched files."""
        self.file_states.clear()

        for pattern in self.config["watch_patterns"]:
            for file_path in self.project_root.rglob(pattern.replace("*", "**/*")):
                if self._should_ignore(file_path):
                    continue

                try:
                    state = self._get_file_state(file_path)
                    self.file_states[str(file_path)] = state
                except Exception as e:
                    logger.debug(f"Error scanning {file_path}: {e}")

        self.stats["files_watched"] = len(self.file_states)
        self.last_scan = datetime.now(timezone.utc)

    async def _check_for_changes(self) -> List[WatchEvent]:
        """Check for file changes since last scan."""
        changes = []
        current_files: Set[str] = set()

        for pattern in self.config["watch_patterns"]:
            for file_path in self.project_root.rglob(pattern.replace("*", "**/*")):
                if self._should_ignore(file_path):
                    continue

                path_str = str(file_path)
                current_files.add(path_str)

                try:
                    new_state = self._get_file_state(file_path)

                    if path_str not in self.file_states:
                        # New file
                        changes.append(WatchEvent(
                            event_type="file_created",
                            file_path=str(file_path.relative_to(self.project_root)),
                            description=f"New file created: {file_path.name}",
                            severity="info",
                        ))
                        self.file_states[path_str] = new_state

                    elif self.file_states[path_str].hash != new_state.hash:
                        # File changed
                        changes.append(WatchEvent(
                            event_type="file_changed",
                            file_path=str(file_path.relative_to(self.project_root)),
                            description=f"File modified: {file_path.name}",
                            severity="info",
                            data={
                                "old_hash": self.file_states[path_str].hash,
                                "new_hash": new_state.hash,
                                "size_change": new_state.size - self.file_states[path_str].size,
                            }
                        ))
                        self.file_states[path_str] = new_state

                except Exception as e:
                    logger.debug(f"Error checking {file_path}: {e}")

        # Check for deleted files
        for path_str in list(self.file_states.keys()):
            if path_str not in current_files:
                relative_path = Path(path_str).relative_to(self.project_root)
                changes.append(WatchEvent(
                    event_type="file_deleted",
                    file_path=str(relative_path),
                    description=f"File deleted: {Path(path_str).name}",
                    severity="warning",
                ))
                del self.file_states[path_str]

        self.stats["changes_detected"] += len(changes)
        return changes

    async def _process_changes(self, changes: List[WatchEvent]) -> None:
        """Process detected changes."""
        for change in changes:
            self._add_event(change)

            # Trigger handlers
            for handler in self.handlers.get(change.event_type, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(change)
                    else:
                        handler(change)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

            # Auto-scan changed files for issues
            if self.config["auto_scan_on_change"] and change.event_type == "file_changed":
                await self._scan_file_for_issues(change.file_path)

            # Auto-fix if enabled
            if self.config["auto_fix_on_change"] and change.event_type == "file_changed":
                await self._auto_fix_file(change.file_path)

    async def _scan_file_for_issues(self, relative_path: str) -> None:
        """Scan a specific file for issues."""
        try:
            from agents.autonomous.smart_analyzer import SmartAnalyzer

            analyzer = SmartAnalyzer()
            full_path = self.project_root / relative_path

            if not full_path.exists():
                return

            analysis = analyzer.analyze_file(full_path)

            for issue in analysis.issues:
                self._add_event(WatchEvent(
                    event_type="issue_found",
                    file_path=relative_path,
                    description=f"{issue.title}: {issue.description}",
                    severity=issue.severity,
                    data={
                        "line": issue.line_number,
                        "category": issue.category,
                        "auto_fixable": issue.auto_fixable,
                    }
                ))

        except Exception as e:
            logger.error(f"Error scanning file: {e}")

    async def _auto_fix_file(self, relative_path: str) -> None:
        """Automatically fix issues in a file."""
        if not relative_path.endswith('.py'):
            return

        try:
            from agents.autonomous.fixer import FixerAgent

            fixer = FixerAgent()
            full_path = self.project_root / relative_path

            if not full_path.exists():
                return

            original = full_path.read_text(encoding='utf-8')
            fixed = original

            # Apply safe fixes
            fixed = fixer._fix_bare_except(fixed, None)
            fixed = fixer._fix_deprecated_code(fixed, None)

            if fixed != original:
                import ast
                try:
                    ast.parse(fixed)
                    full_path.write_text(fixed, encoding='utf-8')
                    self.stats["issues_auto_fixed"] += 1

                    self._add_event(WatchEvent(
                        event_type="file_changed",
                        file_path=relative_path,
                        description=f"Auto-fixed issues in {Path(relative_path).name}",
                        severity="info",
                    ))
                except SyntaxError:
                    pass

        except Exception as e:
            logger.error(f"Auto-fix error: {e}")

    def _get_file_state(self, file_path: Path) -> FileState:
        """Get the current state of a file."""
        content = file_path.read_bytes()
        return FileState(
            path=str(file_path),
            hash=hashlib.md5(content).hexdigest(),
            size=len(content),
            modified_at=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc),
        )

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        path_str = str(file_path)
        return any(pattern in path_str for pattern in self.config["ignore_patterns"])

    def _add_event(self, event: WatchEvent) -> None:
        """Add an event to the log."""
        self.events.append(event)

        # Trim old events
        if len(self.events) > self.config["max_events"]:
            self.events = self.events[-self.config["max_events"]:]

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        return [
            {
                "type": e.event_type,
                "file": e.file_path,
                "description": e.description,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat(),
                "data": e.data,
            }
            for e in sorted(self.events, key=lambda x: x.timestamp, reverse=True)[:limit]
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get watchdog status."""
        return {
            "running": self.running,
            "files_watched": self.stats["files_watched"],
            "changes_detected": self.stats["changes_detected"],
            "issues_auto_fixed": self.stats["issues_auto_fixed"],
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "recent_events": len(self.events),
            "config": self.config,
        }

    async def quick_scan(self) -> Dict[str, Any]:
        """Perform a quick scan and return status."""
        await self._full_scan()
        changes = await self._check_for_changes()

        return {
            "files_scanned": self.stats["files_watched"],
            "changes_found": len(changes),
            "changes": [
                {
                    "type": c.event_type,
                    "file": c.file_path,
                    "description": c.description,
                }
                for c in changes
            ],
        }


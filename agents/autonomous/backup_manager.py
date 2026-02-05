"""
💾 Backup Manager
Automated backup system for code and data.
"""
import os
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """Information about a backup."""
    name: str
    path: str
    created: str
    size_mb: float
    type: str  # 'full', 'incremental', 'code', 'data'
    files_count: int = 0


@dataclass
class BackupConfig:
    """Backup configuration."""
    backup_dir: str = "backups"
    max_backups: int = 10
    include_patterns: list = field(default_factory=lambda: ['*.py', '*.js', '*.html', '*.css', '*.json', '*.yaml', '*.yml', '*.md'])
    exclude_dirs: list = field(default_factory=lambda: ['venv', 'env', '.venv', 'node_modules', '__pycache__', '.git', 'backups', '.cursor'])
    auto_cleanup: bool = True


class BackupManager:
    """
    Manages automated backups of project files.
    """

    def __init__(self, project_root: Optional[Path] = None, config: Optional[BackupConfig] = None):
        self.project_root = project_root or Path.cwd()
        self.config = config or BackupConfig()
        self.backup_dir = self.project_root / self.config.backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.backup_dir / "backup_history.json"
        self.history = self._load_history()

    def _load_history(self) -> list:
        """Load backup history."""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except Exception:
                pass
        return []

    def _save_history(self):
        """Save backup history."""
        try:
            self.history_file.write_text(json.dumps(self.history, indent=2))
        except Exception as e:
            logger.error(f"Error saving backup history: {e}")

    def _should_include(self, path: Path) -> bool:
        """Check if path should be included in backup."""
        # Check excluded directories
        for exclude in self.config.exclude_dirs:
            if exclude in path.parts:
                return False

        # Check file patterns
        if path.is_file():
            for pattern in self.config.include_patterns:
                if path.match(pattern):
                    return True
            return False

        return True

    def create_backup(self, backup_type: str = "full", name: Optional[str] = None) -> Optional[BackupInfo]:
        """Create a new backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"backup_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.zip"

        print(f"  💾 Creating {backup_type} backup...")

        try:
            files_count = 0

            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for path in self.project_root.rglob("*"):
                    if path.is_file() and self._should_include(path):
                        try:
                            arcname = path.relative_to(self.project_root)
                            zf.write(path, arcname)
                            files_count += 1
                        except Exception as e:
                            logger.debug(f"Skipping {path}: {e}")

            # Get backup size
            size_mb = backup_path.stat().st_size / (1024 * 1024)

            backup_info = BackupInfo(
                name=backup_name,
                path=str(backup_path),
                created=datetime.now().isoformat(),
                size_mb=round(size_mb, 2),
                type=backup_type,
                files_count=files_count
            )

            # Add to history
            self.history.append({
                'name': backup_info.name,
                'path': backup_info.path,
                'created': backup_info.created,
                'size_mb': backup_info.size_mb,
                'type': backup_info.type,
                'files_count': backup_info.files_count
            })
            self._save_history()

            # Cleanup old backups
            if self.config.auto_cleanup:
                self._cleanup_old_backups()

            print(f"     ✅ Backup created: {backup_name} ({size_mb:.1f} MB, {files_count} files)")

            return backup_info

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            print(f"     ❌ Backup failed: {e}")
            return None

    def _cleanup_old_backups(self):
        """Remove old backups beyond max_backups limit."""
        if len(self.history) > self.config.max_backups:
            # Sort by creation date
            sorted_history = sorted(self.history, key=lambda x: x['created'])

            # Remove oldest backups
            to_remove = sorted_history[:len(self.history) - self.config.max_backups]

            for backup in to_remove:
                try:
                    backup_path = Path(backup['path'])
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.info(f"Removed old backup: {backup['name']}")
                except Exception as e:
                    logger.error(f"Error removing backup: {e}")

                self.history.remove(backup)

            self._save_history()

    def restore_backup(self, backup_name: str, target_dir: Optional[Path] = None) -> bool:
        """Restore from a backup."""
        # Find backup in history
        backup = next((b for b in self.history if b['name'] == backup_name), None)

        if not backup:
            print(f"     ❌ Backup not found: {backup_name}")
            return False

        backup_path = Path(backup['path'])
        if not backup_path.exists():
            print(f"     ❌ Backup file missing: {backup_path}")
            return False

        target = target_dir or (self.project_root / "restored")
        target.mkdir(parents=True, exist_ok=True)

        print(f"  🔄 Restoring backup: {backup_name}...")

        try:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(target)

            print(f"     ✅ Restored to: {target}")
            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            print(f"     ❌ Restore failed: {e}")
            return False

    def list_backups(self) -> list:
        """List all available backups."""
        return sorted(self.history, key=lambda x: x['created'], reverse=True)

    def get_latest_backup(self) -> Optional[dict]:
        """Get the most recent backup."""
        if not self.history:
            return None
        return max(self.history, key=lambda x: x['created'])

    def schedule_backup(self, interval_hours: int = 24) -> dict:
        """Check if backup is needed based on schedule."""
        latest = self.get_latest_backup()

        if not latest:
            return {'needed': True, 'reason': 'No backups exist'}

        last_backup = datetime.fromisoformat(latest['created'])
        time_since = datetime.now() - last_backup

        if time_since > timedelta(hours=interval_hours):
            return {
                'needed': True,
                'reason': f'Last backup was {time_since.days} days, {time_since.seconds // 3600} hours ago'
            }

        return {
            'needed': False,
            'next_backup': (last_backup + timedelta(hours=interval_hours)).isoformat()
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate backup status report."""
        output = output_path or Path("reports/backup_status.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        backups = self.list_backups()
        total_size = sum(b['size_mb'] for b in backups)

        report = """# 💾 Backup Status Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Backups | {len(backups)} |
| Total Size | {total_size:.1f} MB |
| Max Backups | {self.config.max_backups} |

## Recent Backups

| Name | Created | Size | Files |
|------|---------|------|-------|
"""
        for backup in backups[:10]:
            created = datetime.fromisoformat(backup['created']).strftime('%Y-%m-%d %H:%M')
            report += f"| {backup['name']} | {created} | {backup['size_mb']:.1f} MB | {backup.get('files_count', 'N/A')} |\n"

        # Schedule info
        schedule = self.schedule_backup()
        report += "\n## Schedule\n\n"
        if schedule['needed']:
            report += f"⚠️ **Backup needed**: {schedule['reason']}\n"
        else:
            report += f"✅ Next backup scheduled: {schedule.get('next_backup', 'N/A')}\n"

        report += "\n---\n*Report generated by Backup Manager*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_manager: Optional[BackupManager] = None

def get_backup_manager(project_root: Optional[Path] = None) -> BackupManager:
    """Get or create backup manager instance."""
    global _manager
    if _manager is None:
        _manager = BackupManager(project_root)
    return _manager



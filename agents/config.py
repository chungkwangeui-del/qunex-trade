"""
Agent Configuration
===================

Central configuration for all agents.
Edit this file to customize agent behavior.
"""

import json
from pathlib import Path
from typing import Dict, Any
from typing import Any

# Configuration file location
CONFIG_FILE = Path(__file__).parent.parent / "data" / "agents" / "config.json"


# Default configuration
DEFAULT_CONFIG = {
    # Git Settings
    "git": {
        "auto_commit": True,      # Commit changes after fixes
        "auto_push": True,        # Push to GitHub after commits
        "commit_prefix": "[Agent]",
        "branch_prefix": "agent/",
    },

    # Pipeline Settings
    "pipeline": {
        "cycle_interval_seconds": 300,  # 5 minutes between cycles
        "max_tasks_per_cycle": 5,
        "auto_apply_fixes": True,
        "require_review": True,
        "min_review_score": 70,
    },

    # Self-Healing Settings
    "healing": {
        "enabled": True,
        "max_heal_attempts": 3,
        "heal_cooldown_seconds": 300,
    },

    # Scheduler Settings
    "scheduler": {
        "enabled": True,
        "health_check_interval": 3600,  # 1 hour
        "daily_analysis_hour": 2,       # 2 AM
        "daily_fix_hour": 3,            # 3 AM
    },

    # Memory Settings
    "memory": {
        "forget_after_days": 30,
        "max_memories": 10000,
    },

    # Safety Settings
    "safety": {
        "dry_run": False,             # If True, don't actually modify files
        "backup_before_fix": False,   # Create backup before modifying
        "max_files_per_fix": 10,      # Don't fix more than this many files at once
    },
}


class AgentConfig:
    """Agent configuration manager."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self._load()

    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Get a configuration value."""
        if section not in self.config:
            return default

        if key is None:
            return self.config[section]

        return self.config[section].get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value."""
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration."""
        return self.config.copy()

    def reset(self) -> None:
        """Reset to default configuration."""
        self.config = DEFAULT_CONFIG.copy()
        self._save()

    def _load(self) -> None:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                saved = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))

                # Merge with defaults (to handle new config options)
                for section, values in saved.items():
                    if section in self.config:
                        self.config[section].update(values)
                    else:
                        self.config[section] = values

            except Exception:
                pass  # Use defaults

    def _save(self) -> None:
        """Save configuration to file."""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(
                json.dumps(self.config, indent=2),
                encoding='utf-8'
            )
        except Exception:
            pass


def get_config() -> AgentConfig:
    """Get the global config instance."""
    return AgentConfig.get_instance()


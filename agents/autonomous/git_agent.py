"""
Git Agent
=========

Autonomous version control management.
Handles commits, branches, and change tracking automatically.
"""

import subprocess
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class GitChange:
    """Represents a file change."""
    file_path: str
    status: str  # added, modified, deleted, renamed
    additions: int = 0
    deletions: int = 0


@dataclass
class GitCommit:
    """Represents a commit."""
    hash: str
    message: str
    author: str
    date: datetime
    files_changed: int = 0


class GitAgent:
    """
    Autonomous Git management.

    Capabilities:
    - Auto-commit with smart messages
    - Create feature branches
    - Track changes made by agents
    - Generate changelogs
    - Safe rollback of changes
    """

    def __init__(self):
        self.name = "git"
        self.project_root = Path(__file__).parent.parent.parent

        # Configuration
        self.config = {
            "auto_commit": True,
            "auto_push": True,  # Automatically push to GitHub after commits
            "commit_prefix": "[Agent]",
            "branch_prefix": "agent/",
            "max_files_per_commit": 10,
            "require_message": True,
        }

        # Track agent changes
        self.pending_changes: List[GitChange] = []
        self.commits_made: List[GitCommit] = []

    def is_git_repo(self) -> bool:
        """Check if project is a git repository."""
        return (self.project_root / ".git").exists()

    def run_git(self, *args, check: bool = True) -> Tuple[bool, str]:
        """Run a git command."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding='utf-8',
            )

            if check and result.returncode != 0:
                return False, result.stderr.strip()

            return True, result.stdout.strip()

        except FileNotFoundError:
            return False, "Git is not installed"
        except Exception as e:
            return False, str(e)

    def get_status(self) -> Dict[str, Any]:
        """Get git repository status."""
        if not self.is_git_repo():
            return {"error": "Not a git repository"}

        # Get current branch
        success, branch = self.run_git("rev-parse", "--abbrev-ref", "HEAD")
        if not success:
            branch = "unknown"

        # Get status
        success, status_output = self.run_git("status", "--porcelain")

        changes = {
            "added": [],
            "modified": [],
            "deleted": [],
            "untracked": [],
        }

        if success:
            for line in status_output.split('\n'):
                if not line.strip():
                    continue

                status = line[:2]
                file_path = line[3:].strip()

                if status.startswith('?'):
                    changes["untracked"].append(file_path)
                elif status.startswith('A'):
                    changes["added"].append(file_path)
                elif status.startswith('M') or status.endswith('M'):
                    changes["modified"].append(file_path)
                elif status.startswith('D'):
                    changes["deleted"].append(file_path)

        # Get last commit
        success, last_commit = self.run_git("log", "-1", "--oneline")

        return {
            "branch": branch,
            "changes": changes,
            "total_changes": sum(len(v) for v in changes.values()),
            "last_commit": last_commit if success else None,
            "is_clean": sum(len(v) for v in changes.values()) == 0,
        }

    def get_changed_files(self) -> List[GitChange]:
        """Get list of changed files."""
        if not self.is_git_repo():
            return []

        changes = []
        success, output = self.run_git("status", "--porcelain")

        if success:
            for line in output.split('\n'):
                if not line.strip():
                    continue

                status_code = line[:2].strip()
                file_path = line[3:].strip()

                status = "modified"
                if status_code == "??":
                    status = "untracked"
                elif "A" in status_code:
                    status = "added"
                elif "D" in status_code:
                    status = "deleted"
                elif "R" in status_code:
                    status = "renamed"

                changes.append(GitChange(
                    file_path=file_path,
                    status=status,
                ))

        return changes

    def stage_files(self, file_paths: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Stage files for commit."""
        if not self.is_git_repo():
            return False, "Not a git repository"

        if file_paths:
            for file_path in file_paths:
                success, msg = self.run_git("add", file_path)
                if not success:
                    return False, f"Failed to stage {file_path}: {msg}"
            return True, f"Staged {len(file_paths)} file(s)"
        else:
            return self.run_git("add", "-A")

    def commit(self, message: str, files: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Create a commit."""
        if not self.is_git_repo():
            return False, "Not a git repository"

        # Add prefix
        full_message = f"{self.config['commit_prefix']} {message}"

        # Stage files
        if files:
            success, msg = self.stage_files(files)
            if not success:
                return False, msg

        # Commit
        success, output = self.run_git("commit", "-m", full_message)

        if success:
            # Get commit hash
            hash_success, commit_hash = self.run_git("rev-parse", "--short", "HEAD")

            self.commits_made.append(GitCommit(
                hash=commit_hash if hash_success else "unknown",
                message=message,
                author="Agent",
                date=datetime.now(timezone.utc),
                files_changed=len(files) if files else 0,
            ))

        return success, output

    def auto_commit_agent_changes(self, agent_name: str, action: str) -> Tuple[bool, str]:
        """Automatically commit changes made by an agent."""
        if not self.config["auto_commit"]:
            return False, "Auto-commit disabled"

        status = self.get_status()
        if status.get("is_clean"):
            return False, "No changes to commit"

        changes = status.get("changes", {})
        total_changes = status.get("total_changes", 0)

        # Generate commit message
        if total_changes == 1:
            # Single file change
            changed_file = None
            for change_type, files in changes.items():
                if files:
                    changed_file = files[0]
                    break
            message = f"{agent_name}: {action} - {Path(changed_file).name}"
        else:
            message = f"{agent_name}: {action} - {total_changes} files"

        # Stage all agent-related changes
        self.stage_files()

        return self.commit(message)

    def create_branch(self, branch_name: str, checkout: bool = True) -> Tuple[bool, str]:
        """Create a new branch."""
        if not self.is_git_repo():
            return False, "Not a git repository"

        full_name = f"{self.config['branch_prefix']}{branch_name}"

        success, msg = self.run_git("branch", full_name)
        if not success:
            return False, msg

        if checkout:
            return self.run_git("checkout", full_name)

        return True, f"Created branch {full_name}"

    def create_feature_branch(self, feature_name: str) -> Tuple[bool, str]:
        """Create a branch for a new feature."""
        # Sanitize feature name
        safe_name = re.sub(r'[^a-zA-Z0-9-]', '-', feature_name.lower())[:50]
        branch_name = f"feature/{safe_name}"

        return self.create_branch(branch_name)

    def create_fix_branch(self, issue_id: str) -> Tuple[bool, str]:
        """Create a branch for a fix."""
        branch_name = f"fix/{issue_id}"
        return self.create_branch(branch_name)

    def rollback_last_commit(self) -> Tuple[bool, str]:
        """Rollback the last commit (keeps changes)."""
        if not self.is_git_repo():
            return False, "Not a git repository"

        return self.run_git("reset", "--soft", "HEAD~1")

    def get_diff(self, file_path: Optional[str] = None) -> str:
        """Get diff of changes."""
        if file_path:
            success, diff = self.run_git("diff", "--", file_path)
        else:
            success, diff = self.run_git("diff")

        return diff if success else ""

    def get_recent_commits(self, limit: int = 10) -> List[GitCommit]:
        """Get recent commits."""
        if not self.is_git_repo():
            return []

        success, output = self.run_git(
            "log", f"-{limit}",
            "--format=%H|%s|%an|%aI|%f"
        )

        commits = []
        if success:
            for line in output.split('\n'):
                if not line.strip():
                    continue

                parts = line.split('|')
                if len(parts) >= 4:
                    commits.append(GitCommit(
                        hash=parts[0][:7],
                        message=parts[1],
                        author=parts[2],
                        date=datetime.fromisoformat(parts[3].replace('Z', '+00:00')),
                    ))

        return commits

    def stash_changes(self, message: Optional[str] = None) -> Tuple[bool, str]:
        """Stash current changes."""
        if message:
            return self.run_git("stash", "push", "-m", message)
        return self.run_git("stash")

    def apply_stash(self, stash_index: int = 0) -> Tuple[bool, str]:
        """Apply stashed changes."""
        return self.run_git("stash", "apply", f"stash@{{{stash_index}}}")

    def generate_changelog(self, since: Optional[str] = None) -> str:
        """Generate changelog from commits."""
        args = ["log", "--oneline", "--no-merges"]

        if since:
            args.append(f"{since}..HEAD")
        else:
            args.extend(["-20"])  # Last 20 commits

        success, output = self.run_git(*args)

        if not success:
            return ""

        changelog = "# Changelog\n\n"

        for line in output.split('\n'):
            if not line.strip():
                continue

            parts = line.split(' ', 1)
            if len(parts) == 2:
                hash_val, message = parts

                # Categorize by prefix
                if message.startswith('[Agent]'):
                    message = message.replace('[Agent]', '🤖')
                elif message.startswith('fix'):
                    message = f"🔧 {message}"
                elif message.startswith('feat'):
                    message = f"✨ {message}"
                elif message.startswith('docs'):
                    message = f"📚 {message}"

                changelog += f"- {message} ({hash_val})\n"

        return changelog

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
        """Push commits to remote repository."""
        if not self.is_git_repo():
            return False, "Not a git repository"

        # Get current branch if not specified
        if not branch:
            success, branch = self.run_git("rev-parse", "--abbrev-ref", "HEAD")
            if not success:
                branch = "main"

        return self.run_git("push", remote, branch)

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
        """Pull from remote repository."""
        if not self.is_git_repo():
            return False, "Not a git repository"

        if branch:
            return self.run_git("pull", remote, branch)
        return self.run_git("pull")

    async def commit_and_push(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Commit changes and push to GitHub."""
        result = {
            "committed": False,
            "pushed": False,
            "message": "",
        }

        # First commit
        success, commit_msg = self.commit(message, files)

        if not success:
            if "nothing to commit" in commit_msg.lower():
                result["message"] = "No changes to commit"
                return result
            result["message"] = f"Commit failed: {commit_msg}"
            return result

        result["committed"] = True

        # Then push
        push_success, push_msg = self.push()

        if push_success:
            result["pushed"] = True
            result["message"] = "Changes committed and pushed to GitHub"
        else:
            result["message"] = f"Committed but push failed: {push_msg}"

        return result

    async def smart_commit_session(self) -> Dict[str, Any]:
        """
        Intelligently commit all agent changes from a session.
        Groups related changes and creates meaningful commits.
        """
        if not self.is_git_repo():
            return {"error": "Not a git repository"}

        changes = self.get_changed_files()

        if not changes:
            return {"message": "No changes to commit", "commits": 0}

        # Group changes by directory/type
        groups = {}
        for change in changes:
            # Determine group
            path = Path(change.file_path)

            if 'agents' in str(path):
                group = "agents"
            elif 'web' in str(path):
                if 'templates' in str(path):
                    group = "templates"
                elif 'static' in str(path):
                    group = "static"
                elif 'api_' in str(path.name):
                    group = "api"
                else:
                    group = "web"
            elif 'tests' in str(path):
                group = "tests"
            else:
                group = "other"

            if group not in groups:
                groups[group] = []
            groups[group].append(change)

        commits = []

        # Commit each group
        for group, group_changes in groups.items():
            files = [c.file_path for c in group_changes]

            # Generate message
            change_types = set(c.status for c in group_changes)
            if len(change_types) == 1:
                action = list(change_types)[0]
            else:
                action = "updated"

            message = f"Update {group}: {action} {len(files)} file(s)"

            success, output = self.commit(message, files)

            if success:
                commits.append({
                    "group": group,
                    "files": len(files),
                    "message": message,
                })

        # Auto-push if enabled
        pushed = False
        push_message = ""

        if self.config.get("auto_push", False) and commits:
            push_success, push_msg = self.push()
            pushed = push_success
            push_message = push_msg

        return {
            "message": f"Created {len(commits)} commit(s)" + (" and pushed" if pushed else ""),
            "commits": commits,
            "pushed": pushed,
            "push_message": push_message,
        }


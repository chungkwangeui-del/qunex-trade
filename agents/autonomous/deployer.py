"""
Deployment Agent
================

Automatically deploys code to production.
Handles git push, server sync, database migrations, and health checks.
"""

import os
import subprocess
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    stage: str  # 'git', 'sync', 'migrate', 'restart', 'verify'
    message: str
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class DeploymentPlan:
    """Plan for deployment."""
    steps: List[str]
    files_changed: List[str]
    requires_migration: bool
    requires_restart: bool
    estimated_downtime: int  # seconds
    risks: List[str]


class DeployerAgent:
    """
    Automated deployment agent.

    Features:
    - Git operations (commit, push)
    - Remote server sync (SSH/SCP)
    - Database migrations
    - Service restart
    - Health verification
    - Rollback capability
    """

    def __init__(self):
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.config = self._load_config()
        self.deployment_history: List[Dict] = []
        self.last_successful_commit: Optional[str] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration."""
        config_path = self.project_root / 'deploy.json'

        default_config = {
            'enabled': False,
            'auto_deploy': False,
            'production_branch': 'main',
            'remote_host': '',
            'remote_user': '',
            'remote_path': '/var/www/app',
            'ssh_key_path': '~/.ssh/id_rsa',
            'pre_deploy_commands': [],
            'post_deploy_commands': [],
            'health_check_url': '',
            'health_check_timeout': 30,
            'rollback_on_failure': True,
            'notify_on_deploy': False,
            'environments': {
                'staging': {
                    'host': '',
                    'path': '/var/www/staging'
                },
                'production': {
                    'host': '',
                    'path': '/var/www/production'
                }
            }
        }

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception as e:
                logger.warning(f"Could not load deploy.json: {e}")

        return default_config

    def save_config(self) -> bool:
        """Save deployment configuration."""
        config_path = self.project_root / 'deploy.json'
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Could not save deploy.json: {e}")
            return False

    def analyze_changes(self) -> DeploymentPlan:
        """
        Analyze pending changes and create deployment plan.

        Returns:
            DeploymentPlan with steps and risk assessment
        """
        steps = []
        risks = []
        files_changed = []
        requires_migration = False
        requires_restart = False

        # Get git diff
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            files_changed = [f for f in result.stdout.strip().split('\n') if f]
        except Exception:
            pass

        # Analyze files
        for file in files_changed:
            # Check for migration files
            if 'migration' in file.lower() or 'alembic' in file.lower():
                requires_migration = True
                steps.append('Run database migrations')
                risks.append('Database schema changes - backup recommended')

            # Check for config changes
            if 'config' in file.lower() or file.endswith('.env'):
                risks.append('Configuration changes detected')

            # Check for requirements changes
            if 'requirements' in file.lower():
                steps.append('Install new dependencies')
                requires_restart = True

            # Check for Flask/app changes
            if 'app.py' in file or 'wsgi' in file.lower():
                requires_restart = True

        # Build standard steps
        if files_changed:
            steps.insert(0, 'Commit pending changes')
            steps.insert(1, 'Push to remote repository')
            steps.append('Sync files to server')

            if requires_restart:
                steps.append('Restart application service')

            steps.append('Run health check')

        # Estimate downtime
        estimated_downtime = 0
        if requires_restart:
            estimated_downtime += 10
        if requires_migration:
            estimated_downtime += 30

        return DeploymentPlan(
            steps=steps,
            files_changed=files_changed,
            requires_migration=requires_migration,
            requires_restart=requires_restart,
            estimated_downtime=estimated_downtime,
            risks=risks
        )

    async def deploy(self, environment: str = 'production', dry_run: bool = False) -> List[DeploymentResult]:
        """
        Execute full deployment.

        Args:
            environment: Target environment ('staging' or 'production')
            dry_run: If True, only simulate deployment

        Returns:
            List of DeploymentResult for each stage
        """
        results = []
        start_time = datetime.now()

        logger.info(f"Starting deployment to {environment} (dry_run={dry_run})")

        # Analyze changes first
        plan = self.analyze_changes()

        if not plan.files_changed:
            return [DeploymentResult(
                success=True,
                stage='analyze',
                message='No changes to deploy',
                details={'files_changed': 0}
            )]

        # Stage 1: Git commit
        if not dry_run:
            result = await self._git_commit()
            results.append(result)
            if not result.success:
                return results
        else:
            results.append(DeploymentResult(
                success=True,
                stage='git',
                message='[DRY RUN] Would commit changes',
                details={'files': plan.files_changed}
            ))

        # Stage 2: Git push
        if not dry_run:
            result = await self._git_push()
            results.append(result)
            if not result.success:
                return results
        else:
            results.append(DeploymentResult(
                success=True,
                stage='push',
                message='[DRY RUN] Would push to remote'
            ))

        # Stage 3: Sync to server (if configured)
        env_config = self.config.get('environments', {}).get(environment, {})
        if env_config.get('host'):
            if not dry_run:
                result = await self._sync_to_server(env_config)
                results.append(result)
                if not result.success and self.config.get('rollback_on_failure'):
                    await self._rollback()
                    return results
            else:
                results.append(DeploymentResult(
                    success=True,
                    stage='sync',
                    message=f'[DRY RUN] Would sync to {env_config["host"]}'
                ))

        # Stage 4: Run migrations (if needed)
        if plan.requires_migration:
            if not dry_run:
                result = await self._run_migrations(env_config)
                results.append(result)
            else:
                results.append(DeploymentResult(
                    success=True,
                    stage='migrate',
                    message='[DRY RUN] Would run database migrations'
                ))

        # Stage 5: Restart service (if needed)
        if plan.requires_restart and env_config.get('host'):
            if not dry_run:
                result = await self._restart_service(env_config)
                results.append(result)
            else:
                results.append(DeploymentResult(
                    success=True,
                    stage='restart',
                    message='[DRY RUN] Would restart application service'
                ))

        # Stage 6: Health check
        if self.config.get('health_check_url'):
            if not dry_run:
                result = await self._health_check()
                results.append(result)
                if not result.success and self.config.get('rollback_on_failure'):
                    await self._rollback()
            else:
                results.append(DeploymentResult(
                    success=True,
                    stage='verify',
                    message='[DRY RUN] Would run health check'
                ))

        # Record deployment
        duration = (datetime.now() - start_time).total_seconds()
        self.deployment_history.append({
            'timestamp': start_time.isoformat(),
            'environment': environment,
            'dry_run': dry_run,
            'duration_seconds': duration,
            'success': all(r.success for r in results),
            'files_changed': len(plan.files_changed)
        })

        return results

    async def _git_commit(self) -> DeploymentResult:
        """Commit pending changes."""
        start = datetime.now()
        try:
            # Stage all changes
            subprocess.run(
                ['git', 'add', '-A'],
                check=True,
                cwd=self.project_root
            )

            # Create commit
            result = subprocess.run(
                ['git', 'commit', '-m', f'Auto-deploy: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode != 0 and 'nothing to commit' in result.stdout:
                return DeploymentResult(
                    success=True,
                    stage='git',
                    message='No changes to commit',
                    duration_seconds=(datetime.now() - start).total_seconds()
                )

            # Get commit hash
            commit_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            commit_hash = commit_result.stdout.strip()[:8]

            return DeploymentResult(
                success=True,
                stage='git',
                message=f'Committed changes ({commit_hash})',
                duration_seconds=(datetime.now() - start).total_seconds(),
                details={'commit': commit_hash}
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='git',
                message='Failed to commit changes',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error=str(e)
            )

    async def _git_push(self) -> DeploymentResult:
        """Push to remote repository."""
        start = datetime.now()
        try:
            # Save current commit for rollback
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            self.last_successful_commit = result.stdout.strip()

            # Push
            branch = self.config.get('production_branch', 'main')
            result = subprocess.run(
                ['git', 'push', 'origin', branch],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode != 0:
                return DeploymentResult(
                    success=False,
                    stage='push',
                    message='Failed to push to remote',
                    duration_seconds=(datetime.now() - start).total_seconds(),
                    error=result.stderr
                )

            return DeploymentResult(
                success=True,
                stage='push',
                message=f'Pushed to origin/{branch}',
                duration_seconds=(datetime.now() - start).total_seconds()
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='push',
                message='Failed to push',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error=str(e)
            )

    async def _sync_to_server(self, env_config: Dict) -> DeploymentResult:
        """Sync files to remote server via rsync/scp."""
        start = datetime.now()
        try:
            host = env_config.get('host')
            user = env_config.get('user', self.config.get('remote_user', 'root'))
            path = env_config.get('path', self.config.get('remote_path'))
            key = os.path.expanduser(self.config.get('ssh_key_path', '~/.ssh/id_rsa'))

            # Use rsync for efficient sync
            cmd = [
                'rsync', '-avz', '--delete',
                '--exclude', '.git',
                '--exclude', '__pycache__',
                '--exclude', '*.pyc',
                '--exclude', 'venv',
                '--exclude', '.env',
                '-e', f'ssh -i {key}',
                f'{self.project_root}/',
                f'{user}@{host}:{path}/'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return DeploymentResult(
                    success=False,
                    stage='sync',
                    message='Failed to sync files',
                    duration_seconds=(datetime.now() - start).total_seconds(),
                    error=result.stderr
                )

            return DeploymentResult(
                success=True,
                stage='sync',
                message=f'Synced to {host}:{path}',
                duration_seconds=(datetime.now() - start).total_seconds()
            )

        except FileNotFoundError:
            return DeploymentResult(
                success=False,
                stage='sync',
                message='rsync not installed',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error='Install rsync to enable remote deployment'
            )
        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='sync',
                message='Sync failed',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error=str(e)
            )

    async def _run_migrations(self, env_config: Dict) -> DeploymentResult:
        """Run database migrations on remote server."""
        start = datetime.now()
        try:
            host = env_config.get('host')
            user = env_config.get('user', self.config.get('remote_user', 'root'))
            path = env_config.get('path', self.config.get('remote_path'))
            key = os.path.expanduser(self.config.get('ssh_key_path', '~/.ssh/id_rsa'))

            # Run Flask-Migrate on remote
            cmd = [
                'ssh', '-i', key,
                f'{user}@{host}',
                f'cd {path} && flask db upgrade'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return DeploymentResult(
                    success=False,
                    stage='migrate',
                    message='Migration failed',
                    duration_seconds=(datetime.now() - start).total_seconds(),
                    error=result.stderr
                )

            return DeploymentResult(
                success=True,
                stage='migrate',
                message='Database migrations completed',
                duration_seconds=(datetime.now() - start).total_seconds()
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='migrate',
                message='Migration error',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error=str(e)
            )

    async def _restart_service(self, env_config: Dict) -> DeploymentResult:
        """Restart application service on remote server."""
        start = datetime.now()
        try:
            host = env_config.get('host')
            user = env_config.get('user', self.config.get('remote_user', 'root'))
            key = os.path.expanduser(self.config.get('ssh_key_path', '~/.ssh/id_rsa'))

            # Restart gunicorn/systemd service
            cmd = [
                'ssh', '-i', key,
                f'{user}@{host}',
                'sudo systemctl restart gunicorn || sudo supervisorctl restart all'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            return DeploymentResult(
                success=True,
                stage='restart',
                message='Application service restarted',
                duration_seconds=(datetime.now() - start).total_seconds()
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='restart',
                message='Restart failed',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error=str(e)
            )

    async def _health_check(self) -> DeploymentResult:
        """Verify application is healthy after deployment."""
        start = datetime.now()
        try:
            import urllib.request

            url = self.config.get('health_check_url')
            timeout = self.config.get('health_check_timeout', 30)

            # Try multiple times
            for attempt in range(3):
                try:
                    response = urllib.request.urlopen(url, timeout=timeout)
                    if response.getcode() == 200:
                        return DeploymentResult(
                            success=True,
                            stage='verify',
                            message='Health check passed',
                            duration_seconds=(datetime.now() - start).total_seconds(),
                            details={'status_code': 200, 'attempts': attempt + 1}
                        )
                except Exception:
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(5)

            return DeploymentResult(
                success=False,
                stage='verify',
                message='Health check failed after 3 attempts',
                duration_seconds=(datetime.now() - start).total_seconds()
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='verify',
                message='Health check error',
                duration_seconds=(datetime.now() - start).total_seconds(),
                error=str(e)
            )

    async def _rollback(self) -> DeploymentResult:
        """Rollback to last successful deployment."""
        if not self.last_successful_commit:
            return DeploymentResult(
                success=False,
                stage='rollback',
                message='No previous commit to rollback to'
            )

        try:
            subprocess.run(
                ['git', 'reset', '--hard', self.last_successful_commit],
                check=True,
                cwd=self.project_root
            )

            subprocess.run(
                ['git', 'push', '-f', 'origin', self.config.get('production_branch', 'main')],
                check=True,
                cwd=self.project_root
            )

            return DeploymentResult(
                success=True,
                stage='rollback',
                message=f'Rolled back to {self.last_successful_commit[:8]}'
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                stage='rollback',
                message='Rollback failed',
                error=str(e)
            )

    def get_deployment_history(self) -> List[Dict]:
        """Get deployment history."""
        return self.deployment_history

    def get_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        plan = self.analyze_changes()

        return {
            'enabled': self.config.get('enabled', False),
            'auto_deploy': self.config.get('auto_deploy', False),
            'pending_changes': len(plan.files_changed),
            'requires_migration': plan.requires_migration,
            'requires_restart': plan.requires_restart,
            'estimated_downtime': plan.estimated_downtime,
            'risks': plan.risks,
            'last_deployment': self.deployment_history[-1] if self.deployment_history else None,
            'environments': list(self.config.get('environments', {}).keys())
        }


# Singleton instance
_deployer_instance: Optional[DeployerAgent] = None


def get_deployer() -> DeployerAgent:
    """Get the deployer singleton."""
    global _deployer_instance
    if _deployer_instance is None:
        _deployer_instance = DeployerAgent()
    return _deployer_instance



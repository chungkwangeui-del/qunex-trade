#!/usr/bin/env python
"""
Agent Cron Job
==============

Run all agent status checks via cron.
Add to Render/Heroku as a scheduled job running every 5-15 minutes.

Usage:
    python scripts/cron_run_agents.py
    python scripts/cron_run_agents.py --check-only
    python scripts/cron_run_agents.py --fix
"""

import asyncio
import sys
import os
import logging
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

async def run_agent_checks(check_only: bool = False, fix: bool = False):
    """Run agent status checks."""
    from agents.orchestrator import AgentOrchestrator, quick_status, quick_diagnose, quick_fix
    from agents.notifications import NotificationManager, AgentNotification, NotificationPriority, NotificationChannel, setup_notifications
    from agents.metrics import MetricsCollector

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Starting agent cron job")
    logger.info("=" * 60)

    # Setup notifications
    setup_notifications()
    notifier = NotificationManager.get_instance()
    metrics = MetricsCollector.get_instance()

    try:
        # Run status checks
        logger.info("Running status checks on all agents...")
        status_result = await quick_status()

        overall_status = status_result.get('overall', {}).get('overall_status', 'unknown')
        total_errors = status_result.get('overall', {}).get('total_errors', 0)
        total_warnings = status_result.get('overall', {}).get('total_warnings', 0)

        logger.info(f"Overall status: {overall_status.upper()}")
        logger.info(f"Errors: {total_errors}, Warnings: {total_warnings}")

        # Log individual agent results
        for agent_name, agent_result in status_result.get('agents', {}).items():
            status = agent_result.get('status', 'unknown')
            message = agent_result.get('message', '')

            if status in ['error', 'critical']:
                logger.error(f"  [{status.upper()}] {agent_name}: {message}")
            elif status == 'warning':
                logger.warning(f"  [{status.upper()}] {agent_name}: {message}")
            else:
                logger.info(f"  [{status.upper()}] {agent_name}: {message}")

        # Send notification if there are errors
        if total_errors > 0:
            await notifier.notify(AgentNotification(
                agent_name="cron",
                title="Agent Errors Detected",
                message=f"Found {total_errors} error(s) and {total_warnings} warning(s)",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.LOG, NotificationChannel.SLACK, NotificationChannel.EMAIL]
            ))

        if check_only:
            logger.info("Check-only mode - skipping diagnostics")
            return overall_status != 'error' and overall_status != 'critical'

        # Run diagnostics if there are issues
        if total_errors > 0 or total_warnings > 0:
            logger.info("\nRunning diagnostics...")
            diag_result = await quick_diagnose()

            for issue in diag_result.get('issues', []):
                logger.warning(f"  Issue: {issue}")

            for suggestion in diag_result.get('suggestions', [])[:5]:
                logger.info(f"  Suggestion: {suggestion}")

        # Attempt fixes if requested
        if fix and (total_errors > 0 or total_warnings > 0):
            logger.info("\nAttempting auto-fix...")
            fix_result = await quick_fix(auto_fix=True)

            for agent_name, result in fix_result.get('results', {}).items():
                if result.get('data', {}).get('fixes_applied'):
                    for fix_applied in result['data']['fixes_applied']:
                        logger.info(f"  Fixed [{agent_name}]: {fix_applied}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nCompleted in {elapsed:.2f} seconds")

        return overall_status not in ['error', 'critical']

    except Exception as e:
        logger.error(f"Agent cron job failed: {e}")

        await notifier.notify(AgentNotification(
            agent_name="cron",
            title="Agent Cron Job Failed",
            message=str(e),
            priority=NotificationPriority.CRITICAL,
            channels=[NotificationChannel.LOG, NotificationChannel.SLACK, NotificationChannel.EMAIL]
        ))

        return False

def main():
    parser = argparse.ArgumentParser(description="Run agent checks via cron")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only run status checks, skip diagnostics"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-fix any detected issues"
    )

    args = parser.parse_args()

    success = asyncio.run(run_agent_checks(
        check_only=args.check_only,
        fix=args.fix
    ))

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

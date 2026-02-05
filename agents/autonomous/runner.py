"""
Autonomous Agent Runner
=======================

Entry point for running the autonomous agents.
Can be run as a background service or one-shot.
"""

import asyncio
import signal
import sys

from datetime import datetime, timezone
from pathlib import Path
from datetime import timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.autonomous.pipeline import AutoPipeline
import logging

logger = logging.getLogger(__name__)

class AgentRunner:
    """
    Manages running the autonomous agent pipeline.
    """

    def __init__(self):
        self.pipeline = AutoPipeline()
        self.shutdown_requested = False

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info("\n\nShutdown signal received...")
        self.shutdown_requested = True
        self.pipeline.stop()

    async def run_once(self) -> dict:
        """Run a single automation cycle"""
        logger.info("\n" + "=" * 60)
        logger.info("  AUTONOMOUS AGENT - SINGLE CYCLE")
        logger.info("=" * 60)
        logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60 + "\n")

        report = await self.pipeline.run_single_cycle()

        self._print_report(report)

        return report

    async def run_continuous(self, cycles: int = None, interval: int = 300):
        """
        Run continuous automation.

        Args:
            cycles: Number of cycles (None for infinite)
            interval: Seconds between cycles
        """
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        self.pipeline.config["cycle_interval_seconds"] = interval

        logger.info("\n" + "=" * 60)
        logger.info("  AUTONOMOUS AGENT - CONTINUOUS MODE")
        logger.info("=" * 60)
        logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  Interval: {interval} seconds")
        logger.info(f"  Cycles: {'Unlimited' if cycles is None else cycles}")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 60 + "\n")

        completed = await self.pipeline.run_continuous(max_cycles=cycles)

        logger.info("\n" + "=" * 60)
        logger.info("  AUTOMATION STOPPED")
        logger.info("=" * 60)
        logger.info(f"  Cycles completed: {completed}")
        logger.info(f"  Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

    def _print_report(self, report: dict):
        """Print a formatted report"""
        logger.info("\n" + "-" * 60)
        logger.info("  CYCLE REPORT")
        logger.info("-" * 60)

        # Analysis phase
        if "analysis" in report.get("phases", {}):
            analysis = report["phases"]["analysis"]
            logger.info("\n  Analysis:")
            logger.info(f"    Health Score: {analysis.get('health_score', 'N/A')}%")
            logger.info(f"    Issues Found: {analysis.get('issues_found', 0)}")
            logger.info(f"    Opportunities: {analysis.get('opportunities_found', 0)}")

        # Task creation
        if "task_creation" in report.get("phases", {}):
            creation = report["phases"]["task_creation"]
            logger.info("\n  Task Creation:")
            logger.info(f"    Tasks Created: {creation.get('tasks_created', 0)}")

        # Processing
        logger.info("\n  Processing:")
        logger.info(f"    Tasks Processed: {report.get('tasks_processed', 0)}")
        logger.info(f"    Tasks Completed: {report.get('tasks_completed', 0)}")
        logger.info(f"    Tasks Failed: {report.get('tasks_failed', 0)}")

        # Changes
        logger.info("\n  Changes:")
        logger.info(f"    Applied: {report.get('changes_applied', 0)}")
        logger.info(f"    Rolled Back: {report.get('changes_rolled_back', 0)}")

        # Auto fixes
        if "auto_fixes" in report.get("phases", {}):
            fixes = report["phases"]["auto_fixes"]
            logger.info("\n  Auto Fixes:")
            logger.info(f"    Files Scanned: {fixes.get('scanned_files', 0)}")
            logger.info(f"    Files Fixed: {fixes.get('fixed_files', 0)}")

        # Errors
        if report.get("errors"):
            logger.info("\n  Errors:")
            for error in report["errors"][:5]:
                logger.info(f"    - {error}")

        # Duration
        logger.info(f"\n  Duration: {report.get('duration_seconds', 0):.2f}s")
        logger.info("-" * 60)

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agents.autonomous.runner --once       Run single cycle
  python -m agents.autonomous.runner              Run continuously
  python -m agents.autonomous.runner --cycles 5   Run 5 cycles
  python -m agents.autonomous.runner --interval 60  Check every 60s
        """
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit"
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Number of cycles to run (default: unlimited)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between cycles (default: 300)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit"
    )

    args = parser.parse_args()

    runner = AgentRunner()

    if args.status:
        status = runner.pipeline.get_status()
        logger.info("\n" + "=" * 50)
        logger.info("  AUTONOMOUS AGENT STATUS")
        logger.info("=" * 50)
        logger.info(f"  Running: {status['running']}")
        logger.info(f"  Cycles: {status['cycle_count']}")
        logger.info(f"  Last Cycle: {status['last_cycle'] or 'Never'}")
        logger.info("\n  Task Queue:")
        logger.info(f"    Pending: {status['queue']['pending']}")
        logger.info(f"    In Progress: {status['queue']['in_progress']}")
        logger.info(f"    Completed: {status['queue']['completed']}")
        logger.info(f"    Failed: {status['queue']['failed']}")
        logger.info("=" * 50)
        return

    if args.once:
        asyncio.run(runner.run_once())
    else:
        asyncio.run(runner.run_continuous(
            cycles=args.cycles,
            interval=args.interval
        ))

if __name__ == "__main__":
    main()


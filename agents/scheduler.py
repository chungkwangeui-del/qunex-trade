"""
Agent Scheduler
===============

Background task scheduler for running agents automatically.
Can run as a standalone process or integrated with the Flask app.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading

logger = logging.getLogger(__name__)


class AgentScheduler:
    """
    Background scheduler for running agent tasks automatically.
    
    Usage:
        # As standalone script
        python -m agents.scheduler
        
        # Programmatically
        scheduler = AgentScheduler()
        scheduler.start()
    """
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize scheduler.
        
        Args:
            check_interval: How often to check for due tasks (seconds)
        """
        self.check_interval = check_interval
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[datetime] = None
        self._tasks_run = 0
        
    def start(self, blocking: bool = True) -> None:
        """
        Start the scheduler.
        
        Args:
            blocking: If True, run in foreground. If False, run in background thread.
        """
        if self._is_running:
            logger.warning("Scheduler is already running")
            return
        
        if blocking:
            self._run_blocking()
        else:
            self._run_in_thread()
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._is_running = False
        logger.info("Scheduler stop requested")
        
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
    
    def _run_blocking(self) -> None:
        """Run scheduler in foreground (blocking)."""
        logger.info("Starting agent scheduler (blocking mode)")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self._is_running = True
        self._start_time = datetime.now(timezone.utc)
        
        try:
            asyncio.run(self._scheduler_loop())
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
        finally:
            self._is_running = False
            logger.info("Scheduler stopped")
    
    def _run_in_thread(self) -> None:
        """Run scheduler in background thread."""
        logger.info("Starting agent scheduler (background mode)")
        
        self._thread = threading.Thread(target=self._thread_runner, daemon=True)
        self._thread.start()
    
    def _thread_runner(self) -> None:
        """Thread target for background mode."""
        self._is_running = True
        self._start_time = datetime.now(timezone.utc)
        
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._scheduler_loop())
        finally:
            self._loop.close()
            self._is_running = False
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        from agents.orchestrator import AgentOrchestrator
        from agents.notifications import NotificationManager, AgentNotification, NotificationPriority, NotificationChannel
        from agents.metrics import MetricsCollector
        
        orchestrator = AgentOrchestrator.get_instance()
        notifier = NotificationManager.get_instance()
        metrics = MetricsCollector.get_instance()
        
        logger.info(f"Scheduler loop started, checking every {self.check_interval}s")
        
        while self._is_running:
            try:
                current_time = datetime.now(timezone.utc)
                tasks_due = []
                
                # Find due tasks
                for agent in orchestrator.registry.get_all():
                    for task_id, task in agent.tasks.items():
                        if not task.enabled or not task.interval_seconds:
                            continue
                        
                        if task.last_run is None:
                            tasks_due.append((agent, task_id, task))
                        else:
                            elapsed = (current_time - task.last_run).total_seconds()
                            if elapsed >= task.interval_seconds:
                                tasks_due.append((agent, task_id, task))
                
                # Run due tasks
                for agent, task_id, task in tasks_due:
                    try:
                        logger.debug(f"Running scheduled task: {agent.name}/{task_id}")
                        result = await agent.run_task(task_id)
                        self._tasks_run += 1
                        
                        # Record metrics
                        metrics.record_from_result(agent.name, task_id, result)
                        
                        # Send notification for errors
                        if not result.success or result.status.value in ['error', 'critical']:
                            await notifier.notify(AgentNotification(
                                agent_name=agent.name,
                                title=f"Task Failed: {task.name}",
                                message=result.message,
                                priority=NotificationPriority.HIGH if result.status.value == 'critical' else NotificationPriority.MEDIUM,
                                data={"task_id": task_id, "errors": result.errors},
                                channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
                            ))
                        
                    except Exception as e:
                        logger.error(f"Scheduled task error {agent.name}/{task_id}: {e}")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(self.check_interval)
        
        logger.info(f"Scheduler loop ended. Total tasks run: {self._tasks_run}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        uptime = None
        if self._start_time:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        
        return {
            "is_running": self._is_running,
            "check_interval": self.check_interval,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "tasks_run": self._tasks_run,
        }


def main():
    """Main entry point for running scheduler as standalone process."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Scheduler")
    parser.add_argument(
        "--interval", 
        type=int, 
        default=30,
        help="Check interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    AGENT SCHEDULER                            ║
║                                                               ║
║  Running background task scheduler for Qunex Trade agents.   ║
║  Press Ctrl+C to stop.                                        ║
║                                                               ║
║  Check interval: {args.interval} seconds                                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    scheduler = AgentScheduler(check_interval=args.interval)
    scheduler.start(blocking=True)


if __name__ == "__main__":
    main()


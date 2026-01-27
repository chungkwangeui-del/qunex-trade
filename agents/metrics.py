"""
Agent Metrics & History
=======================

Track agent performance over time for analytics and dashboards.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point"""
    timestamp: datetime
    agent: str
    task: str
    status: str
    execution_time_ms: float
    success: bool
    error_count: int = 0
    warning_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent": self.agent,
            "task": self.task,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }


class MetricsCollector:
    """
    Collects and stores agent metrics for analysis.
    
    Provides:
    - Execution time tracking
    - Success/failure rates
    - Error frequency
    - Historical trends
    """
    
    _instance = None
    
    def __init__(self):
        self._metrics: List[MetricPoint] = []
        self._max_history = 10000  # Keep last 10k data points
        self._aggregates: Dict[str, Dict] = defaultdict(lambda: {
            "total_runs": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time_ms": 0,
            "error_count": 0,
            "warning_count": 0,
        })
    
    @classmethod
    def get_instance(cls) -> 'MetricsCollector':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def record(self, point: MetricPoint) -> None:
        """Record a metric data point."""
        self._metrics.append(point)
        
        # Update aggregates
        key = f"{point.agent}:{point.task}"
        agg = self._aggregates[key]
        agg["total_runs"] += 1
        agg["total_time_ms"] += point.execution_time_ms
        agg["error_count"] += point.error_count
        agg["warning_count"] += point.warning_count
        
        if point.success:
            agg["success_count"] += 1
        else:
            agg["failure_count"] += 1
        
        # Trim history
        if len(self._metrics) > self._max_history:
            self._metrics = self._metrics[-self._max_history:]
    
    def record_from_result(self, agent_name: str, task_id: str, result) -> None:
        """Record metrics from an AgentResult."""
        point = MetricPoint(
            timestamp=result.timestamp,
            agent=agent_name,
            task=task_id,
            status=result.status.value,
            execution_time_ms=result.execution_time_ms,
            success=result.success,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
        )
        self.record(point)
    
    def get_agent_metrics(self, agent_name: str) -> Dict[str, Any]:
        """Get metrics for a specific agent."""
        agent_metrics = [m for m in self._metrics if m.agent == agent_name]
        
        if not agent_metrics:
            return {"agent": agent_name, "data_points": 0}
        
        recent = agent_metrics[-100:]  # Last 100 runs
        
        success_rate = sum(1 for m in recent if m.success) / len(recent) * 100
        avg_time = sum(m.execution_time_ms for m in recent) / len(recent)
        total_errors = sum(m.error_count for m in recent)
        
        return {
            "agent": agent_name,
            "data_points": len(agent_metrics),
            "recent_runs": len(recent),
            "success_rate": round(success_rate, 2),
            "avg_execution_time_ms": round(avg_time, 2),
            "total_errors_recent": total_errors,
            "last_run": recent[-1].to_dict() if recent else None,
        }
    
    def get_task_metrics(self, agent_name: str, task_id: str) -> Dict[str, Any]:
        """Get metrics for a specific task."""
        key = f"{agent_name}:{task_id}"
        agg = self._aggregates.get(key, {})
        
        if not agg.get("total_runs"):
            return {"agent": agent_name, "task": task_id, "total_runs": 0}
        
        return {
            "agent": agent_name,
            "task": task_id,
            "total_runs": agg["total_runs"],
            "success_rate": round(agg["success_count"] / agg["total_runs"] * 100, 2),
            "avg_execution_time_ms": round(agg["total_time_ms"] / agg["total_runs"], 2),
            "total_errors": agg["error_count"],
            "total_warnings": agg["warning_count"],
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall metrics summary."""
        if not self._metrics:
            return {"total_data_points": 0}
        
        # Last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent = [m for m in self._metrics if m.timestamp >= cutoff]
        
        agents_summary = {}
        for m in recent:
            if m.agent not in agents_summary:
                agents_summary[m.agent] = {
                    "runs": 0,
                    "successes": 0,
                    "errors": 0,
                }
            agents_summary[m.agent]["runs"] += 1
            if m.success:
                agents_summary[m.agent]["successes"] += 1
            agents_summary[m.agent]["errors"] += m.error_count
        
        return {
            "total_data_points": len(self._metrics),
            "last_24h_runs": len(recent),
            "agents_summary": agents_summary,
            "overall_success_rate": round(
                sum(1 for m in recent if m.success) / len(recent) * 100, 2
            ) if recent else 0,
        }
    
    def get_timeline(
        self, 
        hours: int = 24, 
        agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get timeline data for charting."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        metrics = [m for m in self._metrics if m.timestamp >= cutoff]
        if agent:
            metrics = [m for m in metrics if m.agent == agent]
        
        # Group by hour
        hourly = defaultdict(lambda: {"runs": 0, "successes": 0, "errors": 0, "time_sum": 0})
        
        for m in metrics:
            hour_key = m.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly[hour_key]["runs"] += 1
            if m.success:
                hourly[hour_key]["successes"] += 1
            hourly[hour_key]["errors"] += m.error_count
            hourly[hour_key]["time_sum"] += m.execution_time_ms
        
        timeline = []
        for hour, data in sorted(hourly.items()):
            timeline.append({
                "timestamp": hour.isoformat(),
                "runs": data["runs"],
                "success_rate": round(data["successes"] / data["runs"] * 100, 2) if data["runs"] else 0,
                "errors": data["errors"],
                "avg_time_ms": round(data["time_sum"] / data["runs"], 2) if data["runs"] else 0,
            })
        
        return timeline
    
    def export_json(self, path: str) -> None:
        """Export metrics to JSON file."""
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "summary": self.get_summary(),
            "timeline_24h": self.get_timeline(24),
            "raw_data": [m.to_dict() for m in self._metrics[-1000:]],
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported metrics to {path}")


# Integration with agents - wrap the run_task method
def track_metrics(original_run_task):
    """Decorator to track metrics from task execution."""
    async def wrapper(self, task_id: str):
        result = await original_run_task(task_id)
        
        # Record metrics
        try:
            collector = MetricsCollector.get_instance()
            collector.record_from_result(self.name, task_id, result)
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
        
        return result
    
    return wrapper


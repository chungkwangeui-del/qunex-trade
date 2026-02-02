"""
Automated Agents Package
========================

Professional automated agents for monitoring, analyzing, and improving
the Qunex Trade platform.

This package includes:
- Health monitoring agents
- Market data agents
- Trading feature agents
- Analysis agents
- Database agents
- Security agents
- Development agents

Usage:
    from agents import AgentOrchestrator

    orchestrator = AgentOrchestrator.get_instance()
    results = await orchestrator.check_all_status()
"""

# Core components
from agents.base import (
    BaseAgent,
    AgentResult,
    AgentStatus,
    AgentTask,
    TaskType,
    AgentRegistry,
)

# Knowledge systems
from agents.codebase_knowledge import CodebaseKnowledge, get_knowledge
from agents.project_scanner import ProjectScanner, get_scanner

# Orchestrator
from agents.orchestrator import (
    AgentOrchestrator,
    quick_status,
    quick_diagnose,
    quick_fix,
    quick_develop,
)

# Individual agents
from agents.health_agent import HealthAgent
from agents.market_agent import MarketDataAgent
from agents.trading_agent import TradingAgent
from agents.analysis_agent import AnalysisAgent
from agents.database_agent import DatabaseAgent
from agents.security_agent import SecurityAgent
from agents.development_agent import DevelopmentAgent

# Notifications and metrics
from agents.notifications import NotificationManager, AgentNotification as Notification
from agents.metrics import MetricsCollector
from agents.scheduler import AgentScheduler

__version__ = "1.0.0"

__all__ = [
    # Core
    "BaseAgent",
    "AgentResult",
    "AgentStatus",
    "AgentTask",
    "TaskType",
    "AgentRegistry",

    # Knowledge
    "CodebaseKnowledge",
    "get_knowledge",
    "ProjectScanner",
    "get_scanner",

    # Orchestrator
    "AgentOrchestrator",
    "quick_status",
    "quick_diagnose",
    "quick_fix",
    "quick_develop",

    # Agents
    "HealthAgent",
    "MarketDataAgent",
    "TradingAgent",
    "AnalysisAgent",
    "DatabaseAgent",
    "SecurityAgent",
    "DevelopmentAgent",

    # Utilities
    "NotificationManager",
    "Notification",
    "MetricsCollector",
    "AgentScheduler",
]

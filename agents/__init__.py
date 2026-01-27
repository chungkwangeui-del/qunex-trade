"""
Automated Agents for Qunex Trade Platform
==========================================

A modular agent system for automating development, error fixing, and status monitoring
across different categories of the trading platform.

Categories:
- Health: System health and connectivity checks
- Market: Market data feeds and API status
- Trading: Trading features (scalp, swing, paper trading)
- Analysis: Analysis tools (patterns, sentiment, options)
- Database: Database integrity and optimization
- Security: Security monitoring and alerts
- Development: Automated development assistance
"""

from agents.base import BaseAgent, AgentStatus, AgentResult
from agents.orchestrator import AgentOrchestrator
from agents.health_agent import HealthAgent
from agents.market_agent import MarketDataAgent
from agents.trading_agent import TradingAgent
from agents.analysis_agent import AnalysisAgent
from agents.database_agent import DatabaseAgent
from agents.security_agent import SecurityAgent
from agents.development_agent import DevelopmentAgent

__all__ = [
    'BaseAgent',
    'AgentStatus',
    'AgentResult',
    'AgentOrchestrator',
    'HealthAgent',
    'MarketDataAgent',
    'TradingAgent',
    'AnalysisAgent',
    'DatabaseAgent',
    'SecurityAgent',
    'DevelopmentAgent',
]


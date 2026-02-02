"""
Autonomous Agent System
=======================

A fully autonomous development team that maintains and improves
the codebase without human intervention.

The Team:
- MasterAgent: The decision maker and coordinator (CEO)
- DeveloperAgent: Writes and modifies code (Engineer)
- ReviewerAgent: Reviews code for quality (QA Lead)
- FixerAgent: Automatically fixes issues (Support)
- ImproverAgent: Proactively improves code (R&D)

This system can:
- Detect issues automatically
- Plan and prioritize fixes
- Write code changes
- Review and validate changes
- Apply changes safely
- Roll back if needed
- Escalate issues requiring human intervention with clear instructions
"""

from agents.autonomous.master import MasterAgent
from agents.autonomous.developer import DeveloperAgent
from agents.autonomous.reviewer import ReviewerAgent
from agents.autonomous.fixer import FixerAgent
from agents.autonomous.improver import ImproverAgent
from agents.autonomous.watchdog import WatchdogAgent
from agents.autonomous.smart_analyzer import SmartAnalyzer, CodeIssue, FileAnalysis
from agents.autonomous.task_queue import TaskQueue, Task, TaskPriority, TaskStatus
from agents.autonomous.pipeline import AutoPipeline
from agents.autonomous.escalation import (
    EscalationManager, Escalation, EscalationReason, EscalationPriority, ManualStep,
)

# New Advanced Agents
from agents.autonomous.memory import AgentMemory, get_memory, MemoryEntry, FixMemory
from agents.autonomous.git_agent import GitAgent, GitChange, GitCommit
from agents.autonomous.code_generator import CodeGeneratorAgent, GeneratedCode
from agents.autonomous.scheduler import SchedulerAgent, ScheduledTask, ScheduleType
from agents.autonomous.self_healer import SelfHealerAgent, HealthCheck, HealingAction
from agents.autonomous.test_runner import TestRunnerAgent, TestResult, TestReport

__all__ = [
    # Core Agents
    "MasterAgent",
    "DeveloperAgent",
    "ReviewerAgent",
    "FixerAgent",
    "ImproverAgent",
    "WatchdogAgent",

    # Advanced Agents
    "GitAgent",
    "CodeGeneratorAgent",
    "SchedulerAgent",
    "SelfHealerAgent",
    "TestRunnerAgent",

    # Memory System
    "AgentMemory",
    "get_memory",
    "MemoryEntry",
    "FixMemory",

    # Git
    "GitChange",
    "GitCommit",

    # Code Generation
    "GeneratedCode",

    # Scheduler
    "ScheduledTask",
    "ScheduleType",

    # Self Healing
    "HealthCheck",
    "HealingAction",

    # Testing
    "TestResult",
    "TestReport",

    # Analysis
    "SmartAnalyzer",
    "CodeIssue",
    "FileAnalysis",

    # Task Management
    "TaskQueue",
    "Task",
    "TaskPriority",
    "TaskStatus",

    # Pipeline
    "AutoPipeline",

    # Escalation
    "EscalationManager",
    "Escalation",
    "EscalationReason",
    "EscalationPriority",
    "ManualStep",
]

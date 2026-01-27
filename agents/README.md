# Automated Agents System

A modular agent framework for automating development, error fixing, and status monitoring across the Qunex Trade platform.

## Overview

The agent system consists of specialized agents that monitor different aspects of the platform:

| Agent | Category | Purpose |
|-------|----------|---------|
| **Health** | System | System health, database connectivity, resources |
| **Market Data** | Market | Market feeds, API status, data freshness |
| **Trading** | Trading | Scalp, swing, paper trading, signals |
| **Analysis** | Analysis | Patterns, sentiment, technical analysis |
| **Database** | System | Table integrity, data freshness, optimization |
| **Security** | Security | Auth, rate limiting, configuration |
| **Development** | Development | Code quality, tests, feature suggestions |

## Usage

### Command Line Interface

```bash
# Check all system statuses
python -m agents.cli status

# Verbose status with details
python -m agents.cli status -v

# Run diagnostics to find issues
python -m agents.cli diagnose

# Get fix suggestions
python -m agents.cli fix

# Auto-fix issues (use with caution)
python -m agents.cli fix --auto

# Get development suggestions
python -m agents.cli develop

# Check specific agent
python -m agents.cli agent health
python -m agents.cli agent market_data

# Run specific task
python -m agents.cli task health db_health

# List all agents and tasks
python -m agents.cli list
```

### Web Dashboard

Access the agents dashboard at `/agents` (admin only):
- Real-time status of all agents
- Run checks, diagnostics, and fixes
- View development suggestions
- Monitor individual agent tasks

### REST API

All endpoints require admin authentication.

```
GET  /api/agents/status          # All agent statuses
GET  /api/agents/diagnose        # Run diagnostics
POST /api/agents/fix             # Fix issues (body: {auto_fix: bool})
GET  /api/agents/develop         # Development suggestions
GET  /api/agents/list            # List all agents
GET  /api/agents/summary         # Comprehensive summary
GET  /api/agents/health          # Quick health (no auth)

# Per-agent endpoints
GET  /api/agents/<name>          # Agent status
GET  /api/agents/<name>/diagnose # Agent diagnostics
POST /api/agents/<name>/fix      # Fix agent issues
GET  /api/agents/<name>/suggestions  # Agent dev suggestions
POST /api/agents/<name>/task/<task_id>  # Run specific task
```

## Architecture

```
agents/
├── __init__.py          # Package exports
├── base.py              # BaseAgent, AgentResult, AgentTask classes
├── orchestrator.py      # AgentOrchestrator - central coordinator
├── cli.py               # Command-line interface
├── health_agent.py      # System health monitoring
├── market_agent.py      # Market data monitoring
├── trading_agent.py     # Trading features monitoring
├── analysis_agent.py    # Analysis tools monitoring
├── database_agent.py    # Database health/optimization
├── security_agent.py    # Security monitoring
└── development_agent.py # Dev assistance
```

## Creating a New Agent

1. Create a new file `agents/my_agent.py`:

```python
from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="my_agent",
            category="Custom",
            description="My custom agent"
        )
    
    def _register_tasks(self):
        self.register_task(AgentTask(
            id="my_task",
            name="My Task",
            task_type=TaskType.STATUS_CHECK,
            description="Performs my custom check",
            handler=self._my_check,
            interval_seconds=300,
        ))
    
    async def check_status(self) -> AgentResult:
        # Run all status check tasks
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)
        # Return aggregated result
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message="All checks passed"
        )
    
    async def diagnose_issues(self) -> AgentResult:
        # Return list of found issues
        return AgentResult(...)
    
    async def fix_errors(self, auto_fix=False) -> AgentResult:
        # Attempt to fix issues
        return AgentResult(...)
    
    async def get_development_suggestions(self) -> AgentResult:
        # Return improvement suggestions
        return AgentResult(...)
    
    async def _my_check(self) -> AgentResult:
        # Your custom check logic
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message="Check passed"
        )
```

2. Register in `agents/__init__.py`
3. Add to orchestrator in `agents/orchestrator.py`

## Task Types

- `STATUS_CHECK` - Health/status monitoring
- `ERROR_FIX` - Error detection and fixing
- `DEVELOPMENT` - Development assistance
- `MAINTENANCE` - Maintenance tasks
- `MONITORING` - Continuous monitoring

## Status Levels

- `HEALTHY` - Everything is working
- `WARNING` - Non-critical issues detected
- `ERROR` - Errors that need attention
- `CRITICAL` - Severe issues requiring immediate action
- `UNKNOWN` - Status cannot be determined
- `RUNNING` - Agent is actively running
- `STOPPED` - Agent is stopped

## Scheduling

Agents can run tasks on a schedule using the orchestrator:

```python
from agents.orchestrator import AgentOrchestrator
import asyncio

orchestrator = AgentOrchestrator.get_instance()

# Start scheduler (checks every 60 seconds)
await orchestrator.start_scheduler(interval_seconds=60)

# Tasks will run according to their interval_seconds
# e.g., a task with interval_seconds=300 runs every 5 minutes
```

## Best Practices

1. **Non-blocking**: Use async/await for I/O operations
2. **Graceful failures**: Always catch exceptions and return AgentResult
3. **Meaningful messages**: Provide clear, actionable messages
4. **Suggestions**: Include helpful suggestions for warnings/errors
5. **Data**: Return relevant data in the `data` field for debugging


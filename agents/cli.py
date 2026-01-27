#!/usr/bin/env python
"""
Agent CLI
=========

Command-line interface for interacting with the automated agents.

Usage:
    python -m agents.cli status           # Check all agent statuses
    python -m agents.cli diagnose         # Run diagnostics
    python -m agents.cli fix              # Get fix suggestions
    python -m agents.cli fix --auto       # Auto-fix issues
    python -m agents.cli develop          # Get development suggestions
    python -m agents.cli agent <name>     # Check specific agent
    python -m agents.cli task <agent> <task_id>  # Run specific task
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

# Add parent directory for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def colorize(text: str, color: str) -> str:
    """Add ANSI color codes to text."""
    colors = {
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'bold': '\033[1m',
        'reset': '\033[0m',
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def status_color(status: str) -> str:
    """Get color for status."""
    status_colors = {
        'healthy': 'green',
        'warning': 'yellow',
        'error': 'red',
        'critical': 'red',
        'unknown': 'blue',
        'running': 'cyan',
        'stopped': 'yellow',
    }
    return status_colors.get(status.lower(), 'reset')


def print_header(title: str) -> None:
    """Print a formatted header."""
    print()
    print(colorize("=" * 60, 'cyan'))
    print(colorize(f"  {title}", 'bold'))
    print(colorize("=" * 60, 'cyan'))
    print()


def print_section(title: str) -> None:
    """Print a section header."""
    print(colorize(f"\n▶ {title}", 'bold'))
    print(colorize("-" * 40, 'cyan'))


def print_status_line(name: str, status: str, message: str = "") -> None:
    """Print a status line with color."""
    status_icon = {
        'healthy': '✓',
        'warning': '⚠',
        'error': '✗',
        'critical': '✗',
        'unknown': '?',
        'running': '●',
        'stopped': '○',
    }.get(status.lower(), '•')
    
    colored_status = colorize(f"{status_icon} {status.upper()}", status_color(status))
    print(f"  {name:30} {colored_status:20} {message}")


async def cmd_status(args) -> int:
    """Check status of all agents."""
    from agents.orchestrator import AgentOrchestrator, quick_status
    
    print_header("Agent Status Check")
    
    result = await quick_status()
    overall = result['overall']
    
    # Overall status
    print_section("Overall System Status")
    print_status_line("System", overall['overall_status'], 
                      f"({overall['total_agents']} agents)")
    
    if overall['total_errors'] > 0:
        print(colorize(f"  ⚠ {overall['total_errors']} error(s) detected", 'red'))
    if overall['total_warnings'] > 0:
        print(colorize(f"  ⚠ {overall['total_warnings']} warning(s) detected", 'yellow'))
    
    # By category
    for category, agents in overall['agents_by_category'].items():
        print_section(f"Category: {category}")
        for agent in agents:
            task_summary = f"({len(agent['tasks'])} tasks)"
            print_status_line(agent['name'], agent['status'], task_summary)
    
    # Agent details
    if args.verbose:
        print_section("Agent Details")
        for name, agent_result in result['agents'].items():
            print(f"\n  {colorize(name.upper(), 'bold')}")
            print(f"    Message: {agent_result['message']}")
            if agent_result.get('warnings'):
                for w in agent_result['warnings'][:3]:
                    print(colorize(f"    ⚠ {w}", 'yellow'))
            if agent_result.get('errors'):
                for e in agent_result['errors'][:3]:
                    print(colorize(f"    ✗ {e}", 'red'))
    
    print()
    return 0 if overall['overall_status'] == 'healthy' else 1


async def cmd_diagnose(args) -> int:
    """Run diagnostics on all agents."""
    from agents.orchestrator import quick_diagnose
    
    print_header("System Diagnostics")
    
    result = await quick_diagnose()
    
    print_section("Issues Found")
    if result['issues']:
        for issue in result['issues']:
            print(colorize(f"  ✗ {issue}", 'red'))
    else:
        print(colorize("  ✓ No issues found", 'green'))
    
    print_section("Suggestions")
    if result['suggestions']:
        for suggestion in result['suggestions']:
            print(colorize(f"  → {suggestion}", 'cyan'))
    else:
        print("  No suggestions at this time")
    
    print()
    return 0 if result['issues_count'] == 0 else 1


async def cmd_fix(args) -> int:
    """Attempt to fix issues."""
    from agents.orchestrator import quick_fix
    
    action = "Auto-fixing" if args.auto else "Getting fix suggestions for"
    print_header(f"{action} Issues")
    
    result = await quick_fix(auto_fix=args.auto)
    
    for agent_name, agent_result in result['results'].items():
        print_section(f"Agent: {agent_name}")
        
        if agent_result.get('suggestions'):
            for suggestion in agent_result['suggestions']:
                icon = "→" if not args.auto else "✓"
                color = "cyan" if not args.auto else "green"
                print(colorize(f"  {icon} {suggestion}", color))
        
        if agent_result.get('data', {}).get('fixes_applied'):
            for fix in agent_result['data']['fixes_applied']:
                print(colorize(f"  ✓ Applied: {fix}", 'green'))
        
        if not agent_result.get('suggestions') and not agent_result.get('data', {}).get('fixes_applied'):
            print(colorize("  ✓ No fixes needed", 'green'))
    
    print()
    return 0


async def cmd_develop(args) -> int:
    """Get development suggestions."""
    from agents.orchestrator import quick_develop
    
    print_header("Development Suggestions")
    
    result = await quick_develop()
    
    # Group by agent category
    by_category = {}
    for item in result['suggestions']:
        agent = item['agent']
        if agent not in by_category:
            by_category[agent] = []
        by_category[agent].append(item['suggestion'])
    
    for agent, suggestions in by_category.items():
        print_section(f"Category: {agent.replace('_', ' ').title()}")
        for suggestion in suggestions[:10]:  # Limit per category
            print(f"  • {suggestion}")
    
    print(f"\n{colorize(f'Total: {result[\"total_suggestions\"]} suggestions', 'bold')}")
    print()
    return 0


async def cmd_agent(args) -> int:
    """Check specific agent status."""
    from agents.orchestrator import AgentOrchestrator
    
    orchestrator = AgentOrchestrator.get_instance()
    agent = orchestrator.get_agent_by_name(args.name)
    
    if not agent:
        print(colorize(f"Agent '{args.name}' not found", 'red'))
        print("Available agents:")
        for a in orchestrator.registry.get_all():
            print(f"  - {a.name}")
        return 1
    
    print_header(f"Agent: {agent.name}")
    
    # Run status check
    result = await agent.check_status()
    
    print_section("Status")
    print_status_line("Status", result.status.value, result.message)
    
    print_section("Tasks")
    for task_id, task in agent.tasks.items():
        last_status = task.last_result.status.value if task.last_result else "not run"
        last_run = task.last_run.strftime("%Y-%m-%d %H:%M") if task.last_run else "never"
        enabled = "enabled" if task.enabled else "disabled"
        print(f"  {task_id:25} {last_status:12} (last: {last_run}, {enabled})")
    
    if args.verbose and result.data:
        print_section("Data")
        print(json.dumps(result.data, indent=2, default=str))
    
    print()
    return 0 if result.success else 1


async def cmd_task(args) -> int:
    """Run specific task on an agent."""
    from agents.orchestrator import AgentOrchestrator
    
    orchestrator = AgentOrchestrator.get_instance()
    
    print_header(f"Running Task: {args.agent}/{args.task_id}")
    
    result = await orchestrator.run_agent_task(args.agent, args.task_id)
    
    print_section("Result")
    print_status_line("Status", result.status.value, result.message)
    print(f"  Execution time: {result.execution_time_ms:.2f}ms")
    
    if result.warnings:
        print_section("Warnings")
        for w in result.warnings:
            print(colorize(f"  ⚠ {w}", 'yellow'))
    
    if result.errors:
        print_section("Errors")
        for e in result.errors:
            print(colorize(f"  ✗ {e}", 'red'))
    
    if result.suggestions:
        print_section("Suggestions")
        for s in result.suggestions:
            print(colorize(f"  → {s}", 'cyan'))
    
    if args.verbose and result.data:
        print_section("Data")
        print(json.dumps(result.data, indent=2, default=str))
    
    print()
    return 0 if result.success else 1


async def cmd_list(args) -> int:
    """List all agents and tasks."""
    from agents.orchestrator import AgentOrchestrator
    
    orchestrator = AgentOrchestrator.get_instance()
    
    print_header("Available Agents and Tasks")
    
    for agent in orchestrator.registry.get_all():
        print_section(f"{agent.name} ({agent.category})")
        print(f"  {agent.description}")
        print()
        for task_id, task in agent.tasks.items():
            interval = f"every {task.interval_seconds}s" if task.interval_seconds else "manual"
            enabled = "✓" if task.enabled else "✗"
            print(f"  {enabled} {task_id:25} - {task.name}")
            print(f"      {task.description} ({interval})")
    
    print()
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Agent Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agents.cli status              Check all systems
  python -m agents.cli status -v           Verbose status
  python -m agents.cli diagnose            Find issues
  python -m agents.cli fix                 Get fix suggestions
  python -m agents.cli fix --auto          Auto-fix issues
  python -m agents.cli develop             Development suggestions
  python -m agents.cli agent health        Check health agent
  python -m agents.cli task health db_health  Run specific task
  python -m agents.cli list                List all agents/tasks
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check all agent statuses')
    status_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Run diagnostics')
    diagnose_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Fix issues')
    fix_parser.add_argument('--auto', action='store_true', help='Auto-fix issues')
    fix_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Develop command
    develop_parser = subparsers.add_parser('develop', help='Get development suggestions')
    develop_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Agent command
    agent_parser = subparsers.add_parser('agent', help='Check specific agent')
    agent_parser.add_argument('name', help='Agent name')
    agent_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Task command
    task_parser = subparsers.add_parser('task', help='Run specific task')
    task_parser.add_argument('agent', help='Agent name')
    task_parser.add_argument('task_id', help='Task ID')
    task_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all agents and tasks')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Map commands to functions
    commands = {
        'status': cmd_status,
        'diagnose': cmd_diagnose,
        'fix': cmd_fix,
        'develop': cmd_develop,
        'agent': cmd_agent,
        'task': cmd_task,
        'list': cmd_list,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        return asyncio.run(cmd_func(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())


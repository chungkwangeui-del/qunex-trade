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
import os
import logging
from typing import List

# Suppress all logging output for clean CLI
logging.disable(logging.CRITICAL)

# Redirect stderr to suppress warnings
class SuppressOutput:
    def __enter__(self):
        self._original_stderr = sys.stderr
        self._original_stdout_write = None
        sys.stderr = open(os.devnull, 'w')
        return self

    def __exit__(self, *args):
        sys.stderr.close()
        sys.stderr = self._original_stderr

# Add parent directory for imports
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
        'white': '\033[97m',
        'gray': '\033[90m',
        'bold': '\033[1m',
        'dim': '\033[2m',
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
    return status_colors.get(status.lower(), 'white')


def status_icon(status: str) -> str:
    """Get icon for status."""
    icons = {
        'healthy': '[OK]',
        'warning': '[!!]',
        'error': '[XX]',
        'critical': '[!!]',
        'unknown': '[??]',
        'running': '[>>]',
        'stopped': '[--]',
    }
    return icons.get(status.lower(), '[..]')


def print_banner(title: str) -> None:
    """Print a clean banner."""
    width = 60
    print()
    print(colorize("+" + "=" * (width - 2) + "+", 'cyan'))
    print(colorize("|", 'cyan') + colorize(f"  {title}".ljust(width - 3), 'bold') + colorize("|", 'cyan'))
    print(colorize("+" + "=" * (width - 2) + "+", 'cyan'))
    print()


def print_section(title: str, icon: str = ">>") -> None:
    """Print a section header."""
    print()
    print(colorize(f"  {icon} {title}", 'bold'))
    print(colorize("  " + "-" * 50, 'gray'))


def print_status_line(name: str, status: str, details: str = "") -> None:
    """Print a clean status line."""
    icon = status_icon(status)
    colored_icon = colorize(icon, status_color(status))
    details_text = colorize(f"  {details}", 'gray') if details else ""
    print(f"     {colored_icon}  {name:28}{details_text}")


def print_item(text: str, indent: int = 5, bullet: str = "*", color: str = "white") -> None:
    """Print a list item."""
    print(" " * indent + colorize(f"{bullet} {text}", color))


def print_error(text: str) -> None:
    """Print an error item."""
    print(colorize(f"     [X] {text}", 'red'))


def print_warning(text: str) -> None:
    """Print a warning item."""
    print(colorize(f"     [!] {text}", 'yellow'))


def print_suggestion(text: str) -> None:
    """Print a suggestion item."""
    print(colorize(f"     --> {text}", 'cyan'))


def print_success(text: str) -> None:
    """Print a success item."""
    print(colorize(f"     [+] {text}", 'green'))


def print_summary_box(stats: dict) -> None:
    """Print a summary statistics box."""
    print()
    print(colorize("  +--------------------------------+", 'gray'))
    print(colorize("  |", 'gray') + colorize("  SUMMARY".ljust(31), 'bold') + colorize("|", 'gray'))
    print(colorize("  +--------------------------------+", 'gray'))

    for key, value in stats.items():
        label = key.replace("_", " ").title()
        if "error" in key.lower():
            val_color = 'red' if value > 0 else 'green'
        elif "warning" in key.lower():
            val_color = 'yellow' if value > 0 else 'green'
        elif "healthy" in key.lower() or "success" in key.lower():
            val_color = 'green'
        else:
            val_color = 'white'

        print(colorize("  |", 'gray') + f"  {label:20}" + colorize(f"{value:>6}", val_color) + colorize("   |", 'gray'))

    print(colorize("  +--------------------------------+", 'gray'))


async def cmd_status(args) -> int:
    """Check status of all agents."""
    with SuppressOutput():
        from agents.orchestrator import AgentOrchestrator, quick_status
        result = await quick_status()

    overall = result['overall']

    print_banner("SYSTEM STATUS REPORT")

    # Overall status with big indicator
    overall_status = overall['overall_status']
    if overall_status == 'healthy':
        status_text = colorize("  ALL SYSTEMS OPERATIONAL", 'green')
    elif overall_status == 'warning':
        status_text = colorize("  WARNINGS DETECTED", 'yellow')
    else:
        status_text = colorize("  ISSUES DETECTED", 'red')

    print(colorize("  System Status:", 'bold'))
    print(status_text)
    print()

    # Summary box
    print_summary_box({
        "total_agents": overall['total_agents'],
        "healthy": sum(1 for cat in overall['agents_by_category'].values()
                      for a in cat if a['status'] == 'healthy'),
        "warnings": overall['total_warnings'],
        "errors": overall['total_errors'],
    })

    # Agents by category
    for category, agents in overall['agents_by_category'].items():
        print_section(f"{category}")
        for agent in agents:
            task_count = len(agent['tasks'])
            print_status_line(
                agent['name'].replace("_", " ").title(),
                agent['status'],
                f"{task_count} tasks"
            )

    # Show issues if verbose
    if args.verbose:
        print_section("Details", "##")
        for name, agent_result in result['agents'].items():
            if agent_result.get('warnings') or agent_result.get('errors'):
                print(f"\n     {colorize(name.upper(), 'bold')}:")
                for w in (agent_result.get('warnings') or [])[:3]:
                    print_warning(w)
                for e in (agent_result.get('errors') or [])[:3]:
                    print_error(e)

    print()
    return 0 if overall_status == 'healthy' else 1


async def cmd_diagnose(args) -> int:
    """Run diagnostics on all agents."""
    with SuppressOutput():
        from agents.orchestrator import quick_diagnose
        result = await quick_diagnose()

    print_banner("SYSTEM DIAGNOSTICS")

    issues = result.get('issues', [])
    suggestions = result.get('suggestions', [])

    # Summary
    if not issues:
        print(colorize("  No issues found - system is healthy!", 'green'))
    else:
        print(colorize(f"  Found {len(issues)} issue(s) requiring attention", 'yellow'))

    print()

    # Issues grouped by agent
    if issues:
        print_section("Issues Found", "!!")

        issues_by_agent = {}
        for issue in issues:
            # Parse [agent] prefix
            if issue.startswith('[') and ']' in issue:
                agent = issue[1:issue.index(']')]
                msg = issue[issue.index(']')+2:]
            else:
                agent = "general"
                msg = issue

            if agent not in issues_by_agent:
                issues_by_agent[agent] = []
            issues_by_agent[agent].append(msg)

        for agent, agent_issues in issues_by_agent.items():
            print(f"\n     {colorize(agent.upper(), 'bold')}:")
            for issue in agent_issues[:5]:  # Limit per agent
                print_error(issue)

    # Suggestions
    if suggestions:
        print_section("Recommendations", ">>")

        # Group suggestions
        suggestions_by_agent = {}
        for suggestion in suggestions:
            if suggestion.startswith('[') and ']' in suggestion:
                agent = suggestion[1:suggestion.index(']')]
                msg = suggestion[suggestion.index(']')+2:]
            else:
                agent = "general"
                msg = suggestion

            if agent not in suggestions_by_agent:
                suggestions_by_agent[agent] = []
            suggestions_by_agent[agent].append(msg)

        for agent, agent_suggestions in suggestions_by_agent.items():
            print(f"\n     {colorize(agent.upper(), 'cyan')}:")
            for sugg in agent_suggestions[:5]:  # Limit per agent
                print_suggestion(sugg)

    print()
    return 0 if len(issues) == 0 else 1


async def cmd_fix(args) -> int:
    """Attempt to fix issues."""
    action = "AUTO-FIX" if args.auto else "FIX RECOMMENDATIONS"

    with SuppressOutput():
        from agents.orchestrator import quick_fix
        result = await quick_fix(auto_fix=args.auto)

    print_banner(action)

    total_fixes = 0
    total_applied = 0

    for agent_name, agent_result in result['results'].items():
        if agent_result is None:
            continue

        suggestions = agent_result.get('suggestions', [])
        data = agent_result.get('data', {}) or {}
        fixes_applied = data.get('fixes_applied', [])

        if suggestions or fixes_applied:
            print_section(agent_name.replace("_", " ").title())

            for suggestion in suggestions:
                total_fixes += 1
                print_suggestion(suggestion)

            for fix in fixes_applied:
                total_applied += 1
                print_success(f"Applied: {fix}")

    # Summary
    print()
    if args.auto:
        print_summary_box({
            "fixes_available": total_fixes + total_applied,
            "fixes_applied": total_applied,
        })
    else:
        if total_fixes == 0:
            print(colorize("  No fixes needed - everything looks good!", 'green'))
        else:
            print(colorize(f"  {total_fixes} fix(es) available. Run with --auto to apply.", 'yellow'))

    print()
    return 0


async def cmd_develop(args) -> int:
    """Get development suggestions."""
    with SuppressOutput():
        from agents.orchestrator import quick_develop
        result = await quick_develop()

    print_banner("DEVELOPMENT ROADMAP")

    # Group by agent/category
    by_category = {}
    for item in result['suggestions']:
        agent = item['agent']
        category = agent.replace("_", " ").title()
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(item['suggestion'])

    # Priority order
    priority_order = ['Development', 'Security', 'Trading', 'Market', 'Analysis', 'Health', 'Database']

    for category in priority_order:
        if category in by_category:
            suggestions = by_category[category]
            print_section(f"{category}", ">>")

            for i, suggestion in enumerate(suggestions[:8], 1):  # Limit to 8 per category
                # Highlight priority items
                if any(p in suggestion.lower() for p in ['high priority', 'critical', 'important']):
                    print(colorize(f"     {i}. {suggestion}", 'yellow'))
                else:
                    print(f"     {i}. {suggestion}")

    # Summary
    total = result.get('total_suggestions', len(result['suggestions']))
    print()
    print_summary_box({
        "total_suggestions": total,
        "categories": len(by_category),
    })

    print()
    return 0


async def cmd_agent(args) -> int:
    """Check specific agent status."""
    with SuppressOutput():
        from agents.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator.get_instance()
        agent = orchestrator.get_agent_by_name(args.name)

    if not agent:
        print(colorize(f"\n  Agent '{args.name}' not found\n", 'red'))
        print("  Available agents:")
        with SuppressOutput():
            for a in orchestrator.registry.get_all():
                print(f"    - {a.name}")
        return 1

    print_banner(f"AGENT: {agent.name.upper()}")

    print(f"  {colorize('Category:', 'gray')} {agent.category}")
    print(f"  {colorize('Description:', 'gray')} {agent.description}")

    # Run status check
    with SuppressOutput():
        result = await agent.check_status()

    print_section("Status")
    print_status_line("Overall", result.status.value, result.message)

    print_section("Tasks")
    for task_id, task in agent.tasks.items():
        last_status = task.last_result.status.value if task.last_result else "pending"
        last_run = task.last_run.strftime("%H:%M") if task.last_run else "never"
        enabled = colorize("ON", 'green') if task.enabled else colorize("OFF", 'red')

        print(f"     [{enabled}] {task_id:22} {colorize(last_status.upper(), status_color(last_status)):>20}  ({last_run})")

    if args.verbose and result.data:
        print_section("Data")
        print(json.dumps(result.data, indent=6, default=str))

    print()
    return 0 if result.success else 1


async def cmd_task(args) -> int:
    """Run specific task on an agent."""
    with SuppressOutput():
        from agents.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator.get_instance()
        result = await orchestrator.run_agent_task(args.agent, args.task_id)

    print_banner(f"TASK: {args.task_id}")

    print_section("Result")
    print_status_line("Status", result.status.value, result.message)
    print(f"     {colorize('Execution time:', 'gray')} {result.execution_time_ms:.2f}ms")

    if result.warnings:
        print_section("Warnings", "!!")
        for w in result.warnings:
            print_warning(w)

    if result.errors:
        print_section("Errors", "XX")
        for e in result.errors:
            print_error(e)

    if result.suggestions:
        print_section("Suggestions", ">>")
        for s in result.suggestions:
            print_suggestion(s)

    if args.verbose and result.data:
        print_section("Data")
        print(json.dumps(result.data, indent=6, default=str))

    print()
    return 0 if result.success else 1


async def cmd_list(args) -> int:
    """List all agents and tasks."""
    with SuppressOutput():
        from agents.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator.get_instance()

    print_banner("AVAILABLE AGENTS")

    for agent in orchestrator.registry.get_all():
        print_section(f"{agent.name} ({agent.category})")
        print(f"     {colorize(agent.description, 'gray')}")
        print()

        for task_id, task in agent.tasks.items():
            interval = f"every {task.interval_seconds}s" if task.interval_seconds else "manual"
            enabled = colorize("[ON]", 'green') if task.enabled else colorize("[OFF]", 'red')
            print(f"     {enabled} {task_id:25} - {task.name}")
            print(f"           {colorize(task.description, 'gray')} ({interval})")

    print()
    return 0


# ============ AUTONOMOUS AGENT COMMANDS ============

async def cmd_auto(args) -> int:
    """Run autonomous agent cycle."""
    with SuppressOutput():
        from agents.autonomous.pipeline import AutoPipeline
        pipeline = AutoPipeline()

    print_banner("AUTONOMOUS AGENT CYCLE")

    print(colorize("  Starting autonomous cycle...", 'cyan'))
    print(colorize("  This will analyze, create tasks, and apply fixes.", 'gray'))
    print()

    with SuppressOutput():
        report = await pipeline.run_single_cycle()

    # Analysis
    print_section("Analysis")
    if "analysis" in report.get("phases", {}):
        analysis = report["phases"]["analysis"]
        print_status_line("Health Score",
            "healthy" if analysis.get("health_score", 0) >= 70 else "warning",
            f"{analysis.get('health_score', 0)}%")
        print(f"     Issues Found: {analysis.get('issues_found', 0)}")
        print(f"     Opportunities: {analysis.get('opportunities_found', 0)}")

    # Tasks
    print_section("Task Processing")
    print(f"     Tasks Created: {report.get('phases', {}).get('task_creation', {}).get('tasks_created', 0)}")
    print(f"     Tasks Processed: {report.get('tasks_processed', 0)}")
    print(f"     Tasks Completed: {report.get('tasks_completed', 0)}")
    print(f"     Tasks Failed: {report.get('tasks_failed', 0)}")

    # Changes
    print_section("Changes")
    print_success(f"Applied: {report.get('changes_applied', 0)}")
    if report.get('changes_rolled_back', 0) > 0:
        print_warning(f"Rolled Back: {report.get('changes_rolled_back', 0)}")

    # Auto fixes
    if "auto_fixes" in report.get("phases", {}):
        fixes = report["phases"]["auto_fixes"]
        if fixes.get("fixed_files", 0) > 0:
            print_section("Auto Fixes Applied")
            for fix_file in fixes.get("fixes", [])[:5]:
                print_success(fix_file)

    # Errors
    if report.get("errors"):
        print_section("Errors", "XX")
        for error in report["errors"][:5]:
            print_error(error)

    # Git status
    if "git" in report.get("phases", {}):
        git_info = report["phases"]["git"]
        print_section("Git Status")
        if git_info.get("error"):
            print_warning(f"Git error: {git_info['error']}")
        else:
            if git_info.get("committed"):
                print_success(f"Committed: {git_info.get('commits', 0)} commit(s)")
            if git_info.get("pushed"):
                print_success("Pushed to GitHub!")
            elif git_info.get("committed"):
                print_warning("Committed but not pushed")

    # Human action required
    human_actions = report.get("human_action_required", [])
    escalations_created = report.get("escalations_created", 0)

    if human_actions or escalations_created > 0:
        print_section("Needs YOUR Action", "!!")
        print(colorize(f"     {escalations_created} issue(s) need manual intervention", 'yellow'))
        for action in human_actions[:3]:
            print(f"     [{colorize(action['priority'], 'yellow')}] {action['title'][:50]}")
        print()
        print(colorize("     Run: python -m agents.cli helpme", 'cyan'))

    # Summary
    print_summary_box({
        "duration_sec": round(report.get("duration_seconds", 0), 1),
        "tasks_done": report.get("tasks_completed", 0),
        "changes": report.get("changes_applied", 0),
        "needs_you": escalations_created,
    })

    print()
    return 0


async def cmd_queue(args) -> int:
    """View task queue status."""
    with SuppressOutput():
        from agents.autonomous.task_queue import TaskQueue
        queue = TaskQueue.get_instance()

    print_banner("TASK QUEUE")

    stats = queue.get_stats()

    # Summary
    print_summary_box({
        "total_tasks": stats["total_tasks"],
        "pending": stats["pending"],
        "in_progress": stats["in_progress"],
        "completed": stats["completed"],
        "failed": stats["failed"],
    })

    # Pending tasks
    pending = queue.get_pending_tasks()
    if pending:
        print_section("Pending Tasks")
        for task in pending[:10]:
            priority_color = 'red' if task.priority.value <= 2 else 'yellow' if task.priority.value <= 3 else 'white'
            print(f"     [{colorize(task.priority.name, priority_color)}] {task.title[:50]}")
            print(f"           {colorize(task.task_type.value, 'gray')} - {task.id}")
    else:
        print(colorize("\n  No pending tasks!", 'green'))

    # Recent completed
    if args.verbose:
        completed = queue.get_completed_tasks(5)
        if completed:
            print_section("Recently Completed")
            for task in completed:
                status_icon = "[OK]" if task.success else "[XX]"
                color = 'green' if task.success else 'red'
                print(f"     {colorize(status_icon, color)} {task.title[:50]}")

    print()
    return 0


async def cmd_work(args) -> int:
    """Start continuous autonomous work."""
    from agents.autonomous.runner import AgentRunner

    print_banner("AUTONOMOUS WORK MODE")

    print(colorize("  Starting continuous autonomous operation...", 'cyan'))
    print(colorize(f"  Interval: {args.interval} seconds", 'gray'))
    print(colorize(f"  Cycles: {'Unlimited' if not args.cycles else args.cycles}", 'gray'))
    print(colorize("  Press Ctrl+C to stop", 'yellow'))
    print()

    runner = AgentRunner()
    await runner.run_continuous(cycles=args.cycles, interval=args.interval)

    return 0


async def cmd_help_me(args) -> int:
    """Show issues that require human intervention with clear instructions."""
    with SuppressOutput():
        from agents.autonomous.master import MasterAgent
        from agents.autonomous.escalation import (
            EscalationManager, escalate_missing_api_key, escalate_security_issue,
            EscalationReason, EscalationPriority, ManualStep,
        )
        from agents.orchestrator import quick_diagnose

        master = MasterAgent()
        escalation_mgr = master.escalation_manager  # Use master's manager

    print_banner("MANUAL ACTIONS REQUIRED")

    # First, run a quick analysis to find issues
    if args.scan:
        print(colorize("  Scanning for issues...", 'cyan'))
        escalation_count = 0

        with SuppressOutput():
            # Run full diagnosis
            diag_result = await quick_diagnose()

            # Process issues to find those needing human action
            for issue_str in diag_result.get('issues', []):
                issue_lower = issue_str.lower()

                # API Key issues
                if 'polygon' in issue_lower and ('api' in issue_lower or 'key' in issue_lower or 'not configured' in issue_lower):
                    escalate_missing_api_key('Polygon', 'scanner')
                    escalation_count += 1
                elif 'alpha' in issue_lower and 'vantage' in issue_lower:
                    escalate_missing_api_key('Alpha Vantage', 'scanner')
                    escalation_count += 1
                elif 'finnhub' in issue_lower and 'api' in issue_lower:
                    escalate_missing_api_key('Finnhub', 'scanner')
                    escalation_count += 1

                # Database issues that need manual action
                elif 'database' in issue_lower and ('stale' in issue_lower or 'no' in issue_lower):
                    # Create manual action for stale data
                    escalation_mgr.create_escalation(
                        title="Database Data Needs Refresh",
                        description=issue_str,
                        reason=EscalationReason.REQUIRES_EXTERNAL,
                        priority=EscalationPriority.MEDIUM,
                        source_agent="scanner",
                        why_not_auto="Running data refresh scripts requires your verification.",
                        manual_steps=[
                            ManualStep(1, "Run the data refresh scripts",
                                      command="python scripts/refresh_all_data.py"),
                            ManualStep(2, "Or run specific refresh scripts for the affected data"),
                            ManualStep(3, "Verify the data was updated successfully"),
                        ]
                    )
                    escalation_count += 1

                # Security issues
                elif 'security' in issue_lower or 'secret' in issue_lower:
                    escalate_security_issue(issue_str, "unknown", "scanner")
                    escalation_count += 1

        print(colorize(f"  Scan complete. Found {escalation_count} issue(s) needing your action.\n",
                      'green' if escalation_count == 0 else 'yellow'))

    # Get pending escalations
    pending = escalation_mgr.get_pending_escalations()

    if not pending:
        print(colorize("  No manual actions required!", 'green'))
        print(colorize("  The agents can handle everything automatically.", 'gray'))
        print()
        return 0

    # Group by priority
    critical = [e for e in pending if e.priority.value == 1]
    high = [e for e in pending if e.priority.value == 2]
    medium = [e for e in pending if e.priority.value == 3]
    low = [e for e in pending if e.priority.value >= 4]

    # Summary
    print_summary_box({
        "total_issues": len(pending),
        "critical": len(critical),
        "high": len(high),
        "medium": len(medium),
        "low": len(low),
    })

    def print_escalation(esc, show_steps=True):
        """Print a single escalation with steps."""
        # Header
        reason_icons = {
            "requires_credentials": "[KEY]",
            "requires_payment": "[$$$]",
            "requires_decision": "[???]",
            "requires_external": "[EXT]",
            "complex_refactor": "[COD]",
            "security_sensitive": "[SEC]",
            "database_migration": "[DB]",
            "config_change": "[CFG]",
            "permission_needed": "[PRM]",
            "unclear_intent": "[???]",
        }
        icon = reason_icons.get(esc.reason.value, "[...]")

        print()
        print(f"     {colorize(icon, 'yellow')} {colorize(esc.title, 'bold')}")
        print(f"        {colorize(esc.description[:100], 'gray')}")

        if esc.affected_files:
            files_str = ", ".join(esc.affected_files[:3])
            print(f"        {colorize('Files:', 'gray')} {files_str}")

        if esc.why_not_auto:
            print()
            print(f"        {colorize('Why manual:', 'yellow')} {esc.why_not_auto[:80]}")

        # Steps
        if show_steps and esc.manual_steps:
            print()
            print(f"        {colorize('HOW TO FIX:', 'cyan')}")
            for step in esc.manual_steps:
                print(f"        {colorize(f'{step.step_number}.', 'cyan')} {step.description}")
                if step.command:
                    print(f"           {colorize('Command:', 'green')} {colorize(step.command, 'white')}")
                if step.code_snippet:
                    print(f"           {colorize('Add code:', 'green')}")
                    for line in step.code_snippet.split('\n')[:3]:
                        print(f"              {colorize(line, 'white')}")
                if step.file_to_edit:
                    print(f"           {colorize('In file:', 'gray')} {step.file_to_edit}")
                if step.notes:
                    print(f"           {colorize('Note:', 'gray')} {step.notes}")

        print(f"        {colorize(f'ID: {esc.id}', 'dim')}")

    # Critical issues first
    if critical:
        print_section("CRITICAL - Fix Immediately!", "!!")
        print(colorize("     These issues are blocking the system!", 'red'))
        for esc in critical:
            print_escalation(esc, show_steps=True)

    # High priority
    if high:
        print_section("HIGH PRIORITY", ">>")
        for esc in high:
            print_escalation(esc, show_steps=args.verbose)

    # Medium priority
    if medium and (args.verbose or not high):
        print_section("MEDIUM PRIORITY", "--")
        for esc in medium[:5]:  # Limit
            print_escalation(esc, show_steps=args.verbose)
        if len(medium) > 5:
            print(f"\n     {colorize(f'... and {len(medium) - 5} more', 'gray')}")

    # Low priority (only if verbose)
    if low and args.verbose:
        print_section("LOW PRIORITY", "..")
        for esc in low[:3]:
            print_escalation(esc, show_steps=False)
        if len(low) > 3:
            print(f"\n     {colorize(f'... and {len(low) - 3} more', 'gray')}")

    # Footer
    print()
    print(colorize("  " + "-" * 58, 'gray'))
    print()
    print(colorize("  After fixing an issue, run:", 'cyan'))
    print(colorize("    python -m agents.cli resolve <ID>", 'white'))
    print()
    print(colorize("  To see detailed steps for all issues:", 'cyan'))
    print(colorize("    python -m agents.cli helpme -v", 'white'))
    print()

    return 0 if not critical else 1


async def cmd_resolve(args) -> int:
    """Mark an escalation as resolved."""
    with SuppressOutput():
        from agents.autonomous.escalation import EscalationManager
        mgr = EscalationManager.get_instance()

    if mgr.resolve_escalation(args.id):
        print(colorize(f"\n  [OK] Marked {args.id} as resolved!\n", 'green'))
        return 0
    else:
        print(colorize(f"\n  [X] Escalation {args.id} not found.\n", 'red'))
        print("  Run 'python -m agents.cli helpme' to see pending issues.")
        return 1


# ============ ADVANCED COMMANDS ============

async def cmd_git(args):
    """Git automation command."""
    from agents.autonomous.git_agent import GitAgent

    git = GitAgent()

    if not git.is_git_repo():
        print_banner("GIT")
        print(colorize("  Not a git repository", 'red'))
        return 1

    if args.action == "status":
        print_banner("GIT STATUS")

        status = git.get_status()

        print(f"  {colorize('Branch:', 'gray')} {colorize(status['branch'], 'cyan')}")
        print(f"  {colorize('Last commit:', 'gray')} {status['last_commit']}")
        print()

        if status['is_clean']:
            print(colorize("  Working directory is clean", 'green'))
        else:
            changes = status['changes']

            if changes['modified']:
                print_section("Modified", "!!")
                for f in changes['modified'][:10]:
                    print(f"     {colorize('M', 'yellow')} {f}")

            if changes['added']:
                print_section("Added", "++")
                for f in changes['added'][:10]:
                    print(f"     {colorize('A', 'green')} {f}")

            if changes['deleted']:
                print_section("Deleted", "--")
                for f in changes['deleted'][:10]:
                    print(f"     {colorize('D', 'red')} {f}")

            if changes['untracked']:
                print_section("Untracked", "??")
                for f in changes['untracked'][:10]:
                    print(f"     {colorize('?', 'gray')} {f}")

            print()
            print(f"  {colorize('Total changes:', 'gray')} {status['total_changes']}")

    elif args.action == "commit":
        print_banner("GIT AUTO-COMMIT")

        # Temporarily disable auto-push if --no-push flag
        if args.no_push:
            git.config["auto_push"] = False

        result = await git.smart_commit_session()

        if "error" in result:
            print(colorize(f"  Error: {result['error']}", 'red'))
        elif result.get("commits"):
            print(colorize(f"  {result['message']}", 'green'))
            print()
            for commit in result['commits']:
                print(f"     {colorize('[+]', 'green')} {commit['group']}: {commit['files']} file(s)")

            if result.get("pushed"):
                print()
                print(colorize("  Changes pushed to GitHub!", 'cyan'))
            elif not args.no_push:
                print()
                print(colorize("  Push failed or not configured", 'yellow'))
                if result.get("push_message"):
                    print(f"     {result['push_message']}")
        else:
            print(colorize("  No changes to commit", 'yellow'))

    elif args.action == "push":
        print_banner("GIT PUSH")

        success, message = git.push()

        if success:
            print(colorize("  Changes pushed to GitHub!", 'green'))
        else:
            print(colorize(f"  Push failed: {message}", 'red'))

    elif args.action == "changelog":
        print_banner("CHANGELOG")

        changelog = git.generate_changelog()
        print(changelog)

    print()
    return 0


async def cmd_generate(args):
    """Code generation command."""
    from agents.autonomous.code_generator import CodeGeneratorAgent

    print_banner("CODE GENERATOR")

    generator = CodeGeneratorAgent()

    if args.type == "feature":
        print(colorize(f"  Generating feature: {args.name}", 'cyan'))
        print()

        # Generate with default fields
        fields = [
            {"name": "name", "type": "string", "required": True},
            {"name": "description", "type": "text"},
            {"name": "status", "type": "string"},
        ]

        generated = generator.generate_feature(
            name=args.name,
            description=args.description or f"Feature: {args.name}",
            fields=fields,
        )

        print_section("Generated Files")
        for gen in generated:
            print(f"     {colorize('[+]', 'green')} {gen.file_path}")
            print(f"           {colorize(gen.description, 'gray')}")

        print()
        print(colorize("  Files generated in memory. Run with --apply to write to disk.", 'yellow'))

    elif args.type == "api":
        print(colorize(f"  Generating API endpoint: {args.name}", 'cyan'))

        endpoint = generator.generate_api_endpoint(
            path=args.name,
            method="GET",
            description=args.description or f"API endpoint for {args.name}",
        )

        print()
        print(colorize("  Generated endpoint:", 'gray'))
        print(endpoint.content[:500] + "...")

    elif args.type == "model":
        print(colorize(f"  Generating model: {args.name}", 'cyan'))
        print(colorize("  Use 'generate feature' for complete model + routes + templates", 'yellow'))

    print()
    return 0


async def cmd_schedule(args):
    """Scheduler command."""
    from agents.autonomous.scheduler import SchedulerAgent

    scheduler = SchedulerAgent()

    if args.action == "list":
        print_banner("SCHEDULED TASKS")

        status = scheduler.get_status()
        print(f"  {colorize('Status:', 'gray')} {'Running' if status['running'] else 'Stopped'}")
        print(f"  {colorize('Tasks:', 'gray')} {status['enabled_tasks']} enabled / {status['total_tasks']} total")
        print()

        upcoming = scheduler.get_upcoming_tasks(10)

        if upcoming:
            print_section("Upcoming Tasks")
            for task in upcoming:
                next_run = task['next_run'][:19] if task['next_run'] else 'N/A'
                print(f"     {colorize(task['id'], 'cyan'):25} {next_run}")
                print(f"           {colorize(task['name'], 'gray')}")
        else:
            print(colorize("  No scheduled tasks", 'yellow'))

    elif args.action == "run":
        if not args.task:
            print(colorize("  --task ID required", 'red'))
            return 1

        print_banner(f"RUNNING TASK: {args.task}")

        result = scheduler.run_task_now(args.task)

        if result.get('success'):
            print(colorize(f"  Task completed successfully", 'green'))
            if result.get('result'):
                print(f"  {colorize('Result:', 'gray')} {result['result']}")
        else:
            print(colorize(f"  Task failed: {result.get('error')}", 'red'))

    elif args.action in ["enable", "disable"]:
        if not args.task:
            print(colorize("  --task ID required", 'red'))
            return 1

        if args.action == "enable":
            scheduler.enable_task(args.task)
            print(colorize(f"  Task {args.task} enabled", 'green'))
        else:
            scheduler.disable_task(args.task)
            print(colorize(f"  Task {args.task} disabled", 'yellow'))

    print()
    return 0


async def cmd_heal(args):
    """Self-healing command."""
    from agents.autonomous.self_healer import SelfHealerAgent

    healer = SelfHealerAgent()

    print_banner("SELF-HEALING SYSTEM")

    # Run health checks
    print(colorize("  Running health checks...", 'cyan'))
    checks = await healer.run_health_checks()

    print()
    print_section("Health Status")

    for name, check in checks.items():
        if check.status == "healthy":
            icon = colorize("[OK]", 'green')
        elif check.status == "degraded":
            icon = colorize("[!!]", 'yellow')
        else:
            icon = colorize("[XX]", 'red')

        print(f"     {icon} {name:20} {colorize(check.message[:50], 'gray')}")

    # Count status
    healthy = len([c for c in checks.values() if c.status == "healthy"])
    degraded = len([c for c in checks.values() if c.status == "degraded"])
    failed = len([c for c in checks.values() if c.status == "failed"])

    print()
    print_summary_box({
        "Healthy": (healthy, 'green'),
        "Degraded": (degraded, 'yellow'),
        "Failed": (failed, 'red'),
    })

    # Auto-heal if requested
    if args.auto and (degraded > 0 or failed > 0):
        print()
        print(colorize("  Attempting auto-heal...", 'cyan'))

        result = await healer.auto_heal()

        if result['healed'] > 0:
            print(colorize(f"  Healed {result['healed']} issue(s)", 'green'))

            for action in result.get('actions', []):
                if action['success']:
                    print(f"     {colorize('[+]', 'green')} {action['component']}: {action['details']}")

        if result['failed'] > 0:
            print(colorize(f"  Could not heal {result['failed']} issue(s)", 'red'))
    elif not args.check and (degraded > 0 or failed > 0):
        print()
        print(colorize("  Run with --auto to attempt automatic healing", 'yellow'))

    print()
    return 0


async def cmd_memory(args):
    """Agent memory command."""
    from agents.autonomous.memory import get_memory

    memory = get_memory()

    print_banner("AGENT MEMORY")

    if args.action == "stats":
        stats = memory.get_stats()

        print_section("Memory Statistics")
        print(f"     {colorize('Total memories:', 'gray')} {stats['total_memories']}")
        print(f"     {colorize('Active memories:', 'gray')} {stats['active_memories']}")
        print(f"     {colorize('Fixes learned:', 'gray')} {stats['fixes_learned']}")
        print(f"     {colorize('Fixes applied:', 'gray')} {stats['fixes_applied']}")
        print(f"     {colorize('Errors encountered:', 'gray')} {stats['errors_encountered']}")
        print(f"     {colorize('Errors solved:', 'gray')} {stats['errors_solved']}")
        print(f"     {colorize('Patterns learned:', 'gray')} {stats['patterns_learned']}")

    elif args.action == "search":
        if not args.query:
            print(colorize("  --query required for search", 'red'))
            return 1

        results = memory.search(args.query, limit=10)

        print_section(f"Search: {args.query}")

        if results:
            for mem in results:
                print(f"     {colorize(mem.category, 'cyan')}: {mem.key}")
                print(f"           {colorize(str(mem.value)[:80], 'gray')}")
        else:
            print(colorize("  No results found", 'yellow'))

    elif args.action == "clear":
        forgotten = memory.forget_old(days=30)
        print(colorize(f"  Cleared {forgotten} old memories", 'green'))

    print()
    return 0


async def cmd_test(args):
    """Test command."""
    from agents.autonomous.test_runner import TestRunnerAgent

    runner = TestRunnerAgent()

    print_banner("TEST RUNNER")

    if args.quick:
        check = await runner.quick_check()

        print_section("Quick Check")
        print(f"     {colorize('Test files:', 'gray')} {check['test_files']}")

        if check.get('uncovered_modules'):
            print(f"     {colorize('Uncovered modules:', 'yellow')} {', '.join(check['uncovered_modules'][:5])}")

        if check.get('last_result'):
            result = check['last_result']
            print(f"     {colorize('Last run:', 'gray')} {result['passed']} passed, {result['failed']} failed")
            if result.get('coverage'):
                print(f"     {colorize('Coverage:', 'gray')} {result['coverage']}%")
    else:
        print(colorize("  Running tests...", 'cyan'))
        print()

        report = await runner.run_all_tests()

        print_section("Test Results")

        if report.total_tests == 0:
            print(colorize("  No tests found or test run failed", 'yellow'))
            if report.results:
                for r in report.results:
                    if r.error_message:
                        print(f"     {colorize('[X]', 'red')} {r.error_message}")
        else:
            passed_color = 'green' if report.passed == report.total_tests else 'yellow'

            print(f"     {colorize('Total:', 'gray')} {report.total_tests}")
            print(f"     {colorize('Passed:', passed_color)} {report.passed}")

            if report.failed > 0:
                print(f"     {colorize('Failed:', 'red')} {report.failed}")

            if report.errors > 0:
                print(f"     {colorize('Errors:', 'red')} {report.errors}")

            if report.coverage_percent:
                cov_color = 'green' if report.coverage_percent >= 80 else 'yellow' if report.coverage_percent >= 50 else 'red'
                print(f"     {colorize('Coverage:', cov_color)} {report.coverage_percent:.1f}%")

            print(f"     {colorize('Duration:', 'gray')} {report.duration_seconds:.2f}s")

    print()
    return 0


async def cmd_welcome(args):
    """Show welcome dashboard."""
    from agents.welcome import main as welcome_main
    welcome_main()
    return 0


async def cmd_fixall(args):
    """Aggressively fix ALL errors."""
    from agents.autonomous.real_fixer import RealFixerAgent

    print_banner("FIX ALL ERRORS")

    print(colorize("  Scanning and fixing ALL errors in the codebase...", 'cyan'))
    print(colorize("  This may take a moment...", 'gray'))
    print()

    fixer = RealFixerAgent()
    result = await fixer.fix_all_errors()

    # Show results
    print_section("Scan Results")
    print(f"     {colorize('Files scanned:', 'gray')} {result['files_scanned']}")
    print(f"     {colorize('Errors found:', 'yellow')} {result['errors_found']}")
    print(f"     {colorize('Errors fixed:', 'green')} {result['errors_fixed']}")

    if result['errors_not_fixed'] > 0:
        print(f"     {colorize('Could not fix:', 'red')} {result['errors_not_fixed']}")

    if result['fixed_files']:
        print()
        print_section("Fixed Files")
        for f in result['fixed_files'][:20]:
            print(f"     {colorize('[+]', 'green')} {f}")

        if len(result['fixed_files']) > 20:
            remaining = len(result['fixed_files']) - 20
            print(f"     {colorize('... and ' + str(remaining) + ' more', 'gray')}")

    # Check if website can run
    if args.check:
        print()
        print_section("Website Check")
        check_result = await fixer.run_and_check_website()

        if check_result['can_run']:
            print(colorize("     Website can run! No import errors.", 'green'))
        else:
            print(colorize("     Website has issues:", 'red'))
            for error in check_result['errors_remaining'][:5]:
                print(f"     {colorize('[X]', 'red')} {error}")

    # Summary
    print()
    if result['errors_fixed'] > 0:
        print_summary_box({
            "Errors Fixed": (result['errors_fixed'], 'green'),
            "Files Changed": (len(result['fixed_files']), 'cyan'),
        })

        print()
        print(colorize("  Now run: python -m agents.cli git commit", 'cyan'))
        print(colorize("  to save and push changes to GitHub", 'gray'))
    else:
        print(colorize("  No errors to fix or all errors require manual attention.", 'yellow'))

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
  python -m agents.cli diagnose            Find issues
  python -m agents.cli fix --auto          Auto-fix issues
  python -m agents.cli develop             Development suggestions
  python -m agents.cli auto                Run autonomous cycle (analyze + fix)
  python -m agents.cli work                Start continuous autonomous work
  python -m agents.cli queue               View pending tasks
  python -m agents.cli list                List all agents/tasks

  python -m agents.cli helpme              Show what YOU need to fix manually
  python -m agents.cli helpme --scan -v    Scan and show all details
  python -m agents.cli resolve ESC-0001    Mark issue as fixed
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

    # ===== AUTONOMOUS COMMANDS =====

    # Auto command - run single autonomous cycle
    auto_parser = subparsers.add_parser('auto', help='Run autonomous agent cycle')
    auto_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    # Queue command - view task queue
    queue_parser = subparsers.add_parser('queue', help='View task queue')
    queue_parser.add_argument('-v', '--verbose', action='store_true', help='Show completed tasks')

    # Work command - start continuous work
    work_parser = subparsers.add_parser('work', help='Start continuous autonomous work')
    work_parser.add_argument('--cycles', type=int, default=None, help='Number of cycles (default: unlimited)')
    work_parser.add_argument('--interval', type=int, default=300, help='Seconds between cycles (default: 300)')

    # Help me command - show what needs manual fixing
    helpme_parser = subparsers.add_parser('helpme', help='Show issues requiring YOUR action')
    helpme_parser.add_argument('-v', '--verbose', action='store_true', help='Show all details')
    helpme_parser.add_argument('--scan', action='store_true', help='Scan for new issues first')

    # Resolve command - mark escalation as fixed
    resolve_parser = subparsers.add_parser('resolve', help='Mark an issue as fixed')
    resolve_parser.add_argument('id', help='Escalation ID (e.g., ESC-0001)')

    # ===== ADVANCED COMMANDS =====

    # Git command - version control
    git_parser = subparsers.add_parser('git', help='Git automation')
    git_parser.add_argument('action', choices=['status', 'commit', 'push', 'changelog'], help='Git action')
    git_parser.add_argument('-m', '--message', help='Commit message')
    git_parser.add_argument('--no-push', action='store_true', help='Commit without pushing')

    # Generate command - code generation
    gen_parser = subparsers.add_parser('generate', help='Generate code')
    gen_parser.add_argument('type', choices=['feature', 'api', 'model'], help='What to generate')
    gen_parser.add_argument('name', help='Name of the thing to generate')
    gen_parser.add_argument('--description', '-d', help='Description')

    # Schedule command - view/manage scheduled tasks
    schedule_parser = subparsers.add_parser('schedule', help='Scheduled tasks')
    schedule_parser.add_argument('action', choices=['list', 'run', 'enable', 'disable'], nargs='?', default='list')
    schedule_parser.add_argument('--task', help='Task ID for run/enable/disable')

    # Heal command - self-healing
    heal_parser = subparsers.add_parser('heal', help='Self-healing system')
    heal_parser.add_argument('--check', action='store_true', help='Run health checks only')
    heal_parser.add_argument('--auto', action='store_true', help='Auto-heal issues')

    # Memory command - agent memory
    memory_parser = subparsers.add_parser('memory', help='Agent memory system')
    memory_parser.add_argument('action', choices=['stats', 'search', 'clear'], nargs='?', default='stats')
    memory_parser.add_argument('--query', '-q', help='Search query')

    # Test command - run tests
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.add_argument('--quick', action='store_true', help='Quick check only')

    # Fix-all command - aggressively fix ALL errors
    fixall_parser = subparsers.add_parser('fixall', help='Aggressively fix ALL errors in the codebase')
    fixall_parser.add_argument('--check', action='store_true', help='Check if website can run after fixes')

    # Welcome command - show welcome dashboard
    welcome_parser = subparsers.add_parser('welcome', help='Show welcome dashboard')

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
        'auto': cmd_auto,
        'queue': cmd_queue,
        'work': cmd_work,
        'helpme': cmd_help_me,
        'resolve': cmd_resolve,
        # Advanced commands
        'git': cmd_git,
        'generate': cmd_generate,
        'schedule': cmd_schedule,
        'heal': cmd_heal,
        'memory': cmd_memory,
        'test': cmd_test,
        'fixall': cmd_fixall,
        'welcome': cmd_welcome,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return asyncio.run(cmd_func(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

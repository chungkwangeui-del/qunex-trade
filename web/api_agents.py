"""
Agent API Endpoints
===================

REST API for interacting with automated agents.
Provides endpoints for status checking, diagnostics, and management.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import asyncio
import logging
from typing import List
import json
from functools import wraps

from agents.orchestrator import (
    quick_status,
    quick_diagnose,
    quick_fix,
    quick_develop,
    AgentOrchestrator
)
from agents.autonomous.statistics import get_statistics
from agents.autonomous.ai_integration import get_ai
from agents.autonomous.deployer import get_deployer
from agents.autonomous.log_analyzer import get_log_analyzer

logger = logging.getLogger(__name__)

api_agents = Blueprint("api_agents", __name__, url_prefix="/api/agents")


def run_async(coro):
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def require_admin(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        # Check if user is admin (developer tier or admin email)
        if not (current_user.email.endswith("@admin.com") or
                current_user.subscription_tier == "developer"):
            return jsonify({"success": False, "error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


@api_agents.route("/status", methods=["GET"])
@login_required
@require_admin
def get_all_status():
    """Get status of all agents."""
    try:
        from agents.orchestrator import quick_status

        result = run_async(quick_status())

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/diagnose", methods=["GET"])
@login_required
@require_admin
def diagnose_all():
    """Run diagnostics on all agents."""
    try:
        from agents.orchestrator import quick_diagnose

        result = run_async(quick_diagnose())

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Error running diagnostics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/fix", methods=["POST"])
@login_required
@require_admin
def fix_all():
    """Attempt to fix issues."""
    try:
        from agents.orchestrator import quick_fix

        data = request.get_json() or {}
        auto_fix = data.get("auto_fix", False)

        result = run_async(quick_fix(auto_fix=auto_fix))

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Error fixing issues: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/develop", methods=["GET"])
@login_required
@require_admin
def get_development_suggestions():
    """Get development suggestions from all agents."""
    try:
        from agents.orchestrator import quick_develop

        result = run_async(quick_develop())

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/list", methods=["GET"])
@login_required
@require_admin
def list_agents():
    """List all available agents."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()

        agents = []
        for agent in orchestrator.registry.get_all():
            agents.append({
                "name": agent.name,
                "category": agent.category,
                "description": agent.description,
                "status": agent.status.value,
                "tasks": [
                    {
                        "id": task_id,
                        "name": task.name,
                        "description": task.description,
                        "enabled": task.enabled,
                        "interval_seconds": task.interval_seconds,
                    }
                    for task_id, task in agent.tasks.items()
                ]
            })

        return jsonify({
            "success": True,
            "data": {
                "agents": agents,
                "total": len(agents)
            }
        })
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/<agent_name>", methods=["GET"])
@login_required
@require_admin
def get_agent_status(agent_name: str):
    """Get status of a specific agent."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()
        agent = orchestrator.get_agent_by_name(agent_name)

        if not agent:
            return jsonify({
                "success": False,
                "error": f"Agent '{agent_name}' not found"
            }), 404

        result = run_async(agent.check_status())

        return jsonify({
            "success": True,
            "data": {
                "agent": agent.to_dict(),
                "status_check": result.to_dict()
            }
        })
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/<agent_name>/diagnose", methods=["GET"])
@login_required
@require_admin
def diagnose_agent(agent_name: str):
    """Run diagnostics on a specific agent."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()
        agent = orchestrator.get_agent_by_name(agent_name)

        if not agent:
            return jsonify({
                "success": False,
                "error": f"Agent '{agent_name}' not found"
            }), 404

        result = run_async(agent.diagnose_issues())

        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
    except Exception as e:
        logger.error(f"Error diagnosing agent: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/<agent_name>/fix", methods=["POST"])
@login_required
@require_admin
def fix_agent(agent_name: str):
    """Attempt to fix issues for a specific agent."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()
        agent = orchestrator.get_agent_by_name(agent_name)

        if not agent:
            return jsonify({
                "success": False,
                "error": f"Agent '{agent_name}' not found"
            }), 404

        data = request.get_json() or {}
        auto_fix = data.get("auto_fix", False)

        result = run_async(agent.fix_errors(auto_fix=auto_fix))

        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
    except Exception as e:
        logger.error(f"Error fixing agent: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/<agent_name>/suggestions", methods=["GET"])
@login_required
@require_admin
def get_agent_suggestions(agent_name: str):
    """Get development suggestions for a specific agent."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()
        agent = orchestrator.get_agent_by_name(agent_name)

        if not agent:
            return jsonify({
                "success": False,
                "error": f"Agent '{agent_name}' not found"
            }), 404

        result = run_async(agent.get_development_suggestions())

        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/<agent_name>/task/<task_id>", methods=["POST"])
@login_required
@require_admin
def run_task(agent_name: str, task_id: str):
    """Run a specific task on an agent."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()

        result = run_async(orchestrator.run_agent_task(agent_name, task_id))

        return jsonify({
            "success": result.success,
            "data": result.to_dict()
        })
    except Exception as e:
        logger.error(f"Error running task: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/summary", methods=["GET"])
@login_required
@require_admin
def get_summary():
    """Get comprehensive summary of all agents."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()

        return jsonify({
            "success": True,
            "data": orchestrator.get_comprehensive_status()
        })
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/health", methods=["GET"])
def agent_health():
    """Quick health check for agents (no auth required)."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator.get_instance()
        status = orchestrator.get_comprehensive_status()

        return jsonify({
            "status": status["overall_status"],
            "agents": status["total_agents"],
            "errors": status["total_errors"],
            "warnings": status["total_warnings"],
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD API
# ═══════════════════════════════════════════════════════════════════════════

@api_agents.route("/dashboard", methods=["GET"])
@login_required
@require_admin
def get_dashboard_data():
    """Get comprehensive dashboard data."""
    try:
        from agents.autonomous.statistics import get_statistics

        stats = get_statistics()
        data = stats.get_dashboard_data()

        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/reports/<report_type>", methods=["GET"])
@login_required
@require_admin
def get_report(report_type: str):
    """Generate a report."""
    try:
        from agents.autonomous.statistics import get_statistics

        stats = get_statistics()
        report = stats.generate_report(report_type)

        format_type = request.args.get('format', 'json')
        content = stats.export_report(report, format_type)

        return jsonify({
            "success": True,
            "data": {
                "report": content if format_type == 'json' else None,
                "markdown": content if format_type == 'markdown' else None
            }
        })
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# AI INTEGRATION API
# ═══════════════════════════════════════════════════════════════════════════

@api_agents.route("/ai/status", methods=["GET"])
@login_required
@require_admin
def get_ai_status():
    """Get AI integration status."""
    try:
        from agents.autonomous.ai_integration import get_ai

        ai = get_ai()

        return jsonify({
            "success": True,
            "data": ai.get_usage_stats()
        })
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/ai/analyze", methods=["POST"])
@login_required
@require_admin
def ai_analyze():
    """Analyze code with AI."""
    try:
        from agents.autonomous.ai_integration import get_ai

        data = request.get_json() or {}
        code = data.get('query', '')
        context = data.get('context', '')

        ai = get_ai()
        result = run_async(ai.analyze_code(code, context))

        return jsonify({
            "success": result.success,
            "data": {
                "content": result.content,
                "model": result.model,
                "tokens": result.tokens_used,
                "cost": result.cost
            }
        })
    except Exception as e:
        logger.error(f"Error in AI analyze: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/ai/generate", methods=["POST"])
@login_required
@require_admin
def ai_generate():
    """Generate code with AI."""
    try:
        from agents.autonomous.ai_integration import get_ai

        data = request.get_json() or {}
        description = data.get('description', '')

        ai = get_ai()
        result = run_async(ai.generate_feature(description))

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Error in AI generate: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/ai/explain", methods=["POST"])
@login_required
@require_admin
def ai_explain():
    """Explain error with AI."""
    try:
        from agents.autonomous.ai_integration import get_ai

        data = request.get_json() or {}
        error = data.get('error', '')
        code = data.get('code', '')

        ai = get_ai()
        explanation = run_async(ai.explain_error(error, code))

        return jsonify({
            "success": True,
            "data": {
                "explanation": explanation
            }
        })
    except Exception as e:
        logger.error(f"Error in AI explain: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/ai/tests", methods=["POST"])
@login_required
@require_admin
def ai_tests():
    """Generate tests with AI."""
    try:
        from agents.autonomous.ai_integration import get_ai

        data = request.get_json() or {}
        code = data.get('code', '')
        file_path = data.get('file_path', 'unknown.py')

        ai = get_ai()
        tests = run_async(ai.generate_tests(code, file_path))

        return jsonify({
            "success": True,
            "data": {
                "tests": tests
            }
        })
    except Exception as e:
        logger.error(f"Error in AI tests: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT API
# ═══════════════════════════════════════════════════════════════════════════

@api_agents.route("/deploy/status", methods=["GET"])
@login_required
@require_admin
def get_deploy_status():
    """Get deployment status."""
    try:
        from agents.autonomous.deployer import get_deployer

        deployer = get_deployer()
        status = deployer.get_status()

        return jsonify({
            "success": True,
            "data": status
        })
    except Exception as e:
        logger.error(f"Error getting deploy status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/deploy", methods=["POST"])
@login_required
@require_admin
def run_deploy():
    """Run deployment."""
    try:
        from agents.autonomous.deployer import get_deployer

        data = request.get_json() or {}
        environment = data.get('environment', 'staging')
        dry_run = data.get('dry_run', True)

        deployer = get_deployer()
        results = run_async(deployer.deploy(environment, dry_run))

        return jsonify({
            "success": all(r.success for r in results),
            "data": {
                "results": [
                    {
                        "stage": r.stage,
                        "success": r.success,
                        "message": r.message,
                        "duration": r.duration_seconds,
                        "error": r.error
                    }
                    for r in results
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error running deploy: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/deploy/history", methods=["GET"])
@login_required
@require_admin
def get_deploy_history():
    """Get deployment history."""
    try:
        from agents.autonomous.deployer import get_deployer

        deployer = get_deployer()
        history = deployer.get_deployment_history()

        return jsonify({
            "success": True,
            "data": {
                "history": history
            }
        })
    except Exception as e:
        logger.error(f"Error getting deploy history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# LOG ANALYSIS API
# ═══════════════════════════════════════════════════════════════════════════

@api_agents.route("/logs/analyze", methods=["GET"])
@login_required
@require_admin
def analyze_logs():
    """Analyze application logs."""
    try:
        from agents.autonomous.log_analyzer import get_log_analyzer

        hours = int(request.args.get('hours', 24))

        analyzer = get_log_analyzer()
        result = run_async(analyzer.analyze_all(hours))

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Error analyzing logs: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/logs/errors", methods=["GET"])
@login_required
@require_admin
def get_log_errors():
    """Get recent errors from logs."""
    try:
        from agents.autonomous.log_analyzer import get_log_analyzer

        limit = int(request.args.get('limit', 20))

        analyzer = get_log_analyzer()
        errors = analyzer.get_recent_errors(limit)

        return jsonify({
            "success": True,
            "data": {
                "errors": errors
            }
        })
    except Exception as e:
        logger.error(f"Error getting log errors: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_agents.route("/logs/alerts", methods=["GET"])
@login_required
@require_admin
def get_log_alerts():
    """Get log-based alerts."""
    try:
        from agents.autonomous.log_analyzer import get_log_analyzer

        analyzer = get_log_analyzer()

        return jsonify({
            "success": True,
            "data": {
                "alerts": [
                    {
                        "id": a.id,
                        "severity": a.severity,
                        "title": a.title,
                        "message": a.message,
                        "count": a.count,
                        "suggested_action": a.suggested_action,
                        "auto_fixable": a.auto_fixable
                    }
                    for a in analyzer.alerts
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error getting log alerts: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


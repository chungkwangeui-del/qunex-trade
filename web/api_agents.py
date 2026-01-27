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
    from functools import wraps
    
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


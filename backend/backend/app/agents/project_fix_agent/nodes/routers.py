"""
Routers and terminal nodes  (Project Fix agent)
────────────────────────────────────────────────
"""
import logging
from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import RunnableConfig
from app.agents.project_fix_agent.state import AgentState

logger = logging.getLogger(__name__)

_STUCK_THRESHOLD = 10   # how many times the same fingerprint before "stuck"


# ── Conditional router: after parse_errors ─────────────────────────────────────

def route_check_success(state: AgentState) -> str:
    """Route: success → build_context → abort."""
    if state.get("compiler_success"):
        return "success"
    if state.get("iteration", 0) >= state.get("max_iterations", 20):
        return "abort"
    errors = state.get("errors", [])
    if not errors:
        return "success"
    return "build_context"


# ── Conditional router: after pre_compile_check ────────────────────────────────

def route_pre_compile(state: AgentState) -> str:
    if state.get("status") == "pre_compile_failed":
        logger.warning("[router:pre_compile] Pre-existing errors — routing to escalate")
        return "pre_compile_escalate"
    return "pom_update"


# ── Conditional router: after build_context ────────────────────────────────────

def route_check_stuck(state: AgentState) -> str:
    """Escalate if the same fingerprint keeps repeating past the threshold."""
    counts: dict = state.get("fingerprint_counts") or {}
    if any(v >= _STUCK_THRESHOLD for v in counts.values()):
        return "escalate"
    return "llm_fix"


# ── Terminal nodes ─────────────────────────────────────────────────────────────

def success_node(state: AgentState, config: RunnableConfig) -> AgentState:
    logger.info("[project_fix] SUCCESS — compilation succeeded.")
    dispatch_custom_event(
        "project_fix_trace",
        {"id": "terminal", "status": "completed",
         "title": "Compilation Successful",
         "detail": f"All errors resolved after {state.get('iteration', 1)} iteration(s)."},
        config=config,
    )
    return {
        **state,
        "status":        "success",
        "final_message": (
            f"✅ Compilation succeeded after {state.get('iteration', 1)} iteration(s). "
            "Your fixed project is ready for download."
        ),
    }


def abort_node(state: AgentState, config: RunnableConfig) -> AgentState:
    remaining = len(state.get("errors", []))
    logger.warning(f"[project_fix] ABORT — max iterations reached, {remaining} error(s) left.")
    dispatch_custom_event(
        "project_fix_trace",
        {"id": "terminal", "status": "error",
         "title": "Max Iterations Reached",
         "detail": f"{remaining} error(s) still unresolved."},
        config=config,
    )
    return {
        **state,
        "status":        "abort",
        "final_message": (
            f"⚠️ Max iterations ({state.get('max_iterations', 20)}) reached. "
            f"{remaining} error(s) remain. Partial fixes applied — download available."
        ),
    }


def escalate_node(state: AgentState, config: RunnableConfig) -> AgentState:
    logger.warning("[project_fix] ESCALATE — agent stuck on repeating errors.")
    dispatch_custom_event(
        "project_fix_trace",
        {"id": "terminal", "status": "error",
         "title": "Agent Escalating",
         "detail": "Repeating errors detected — manual review required."},
        config=config,
    )
    return {
        **state,
        "status":        "escalate",
        "final_message": (
            "⚠️ Agent escalating — the same errors repeated too many times. "
            "Manual intervention required. Partial fixes applied."
        ),
    }


def pre_compile_escalate_node(state: AgentState, config: RunnableConfig) -> AgentState:
    logger.warning("[project_fix] PRE-COMPILE ESCALATE — pre-existing errors detected.")
    dispatch_custom_event(
        "project_fix_trace",
        {"id": "terminal", "status": "error",
         "title": "Agent Escalating",
         "detail": "Pre-existing errors detected before any changes. Manual review required."},
        config=config,
    )
    return {
        **state,
        "status": "escalate",
    }


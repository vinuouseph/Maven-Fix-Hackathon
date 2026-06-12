"""
graph.py — Project Fix LangGraph
──────────────────────────────────
Topology:

  START
    → compile
    → parse_errors
    ├──(success)──────────► success → END
    ├──(abort)────────────► abort   → END
    └──(build_context)───► build_context
                           ├──(escalate)──► escalate → END
                           └──(llm_fix)──► llm_fix_agent → compile  [loop]
"""

from langgraph.graph import StateGraph, START, END

from app.agents.project_fix_agent.state import AgentState
from app.agents.project_fix_agent.nodes import (
    pom_update_node,
    compile_node,
    parse_errors_node,
    build_context_node,
    llm_fix_agent_node,
    route_check_success,
    route_check_stuck,
    route_pre_compile,
    success_node,
    abort_node,
    escalate_node,
    pre_compile_escalate_node,
    pre_compile_check_node,
)


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    builder.add_node("pom_update",     pom_update_node)
    builder.add_node("pre_compile_check", pre_compile_check_node)
    builder.add_node("pre_compile_escalate", pre_compile_escalate_node)
    builder.add_node("compile",        compile_node)
    builder.add_node("parse_errors",   parse_errors_node)
    builder.add_node("build_context",  build_context_node)
    builder.add_node("llm_fix_agent",  llm_fix_agent_node)
    builder.add_node("success",        success_node)
    builder.add_node("abort",          abort_node)
    builder.add_node("escalate",       escalate_node)

    # ── Edges ──────────────────────────────────────────────────────────────────
    builder.add_edge(START, "pre_compile_check")
    
    builder.add_conditional_edges(
        "pre_compile_check",
        route_pre_compile,
        {
            "pom_update": "pom_update",
            "pre_compile_escalate": "pre_compile_escalate",
        },
    )
    
    builder.add_edge("pre_compile_escalate", END)
    builder.add_edge("pom_update",   "compile")
    builder.add_edge("compile",      "parse_errors")

    builder.add_conditional_edges(
        "parse_errors",
        route_check_success,
        {
            "success":       "success",
            "build_context": "build_context",
            "abort":         "abort",
        },
    )

    builder.add_conditional_edges(
        "build_context",
        route_check_stuck,
        {
            "llm_fix":  "llm_fix_agent",
            "escalate": "escalate",
        },
    )

    # Fix loop: after the LLM makes tool calls, re-compile to check
    builder.add_edge("llm_fix_agent", "compile")

    # Terminal edges
    builder.add_edge("success",  END)
    builder.add_edge("abort",    END)
    builder.add_edge("escalate", END)

    return builder.compile()


# Singleton compiled graph
graph = build_graph()

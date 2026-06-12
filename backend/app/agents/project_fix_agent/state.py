"""
State schema for the Project Fix LangGraph agent.
All nodes read from and write to this shared TypedDict.
"""

from __future__ import annotations
from typing import TypedDict, Optional


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────
    work_dir: str                      # extracted project directory on disk
    build_tool: str                    # "maven" | "gradle"
    build_args: Optional[str]          # extra command line arguments

    # ── Loop control ──────────────────────────────────────────────────────
    iteration: int
    max_iterations: int

    # ── Compiler state ────────────────────────────────────────────────────
    compiler_stdout: str
    compiler_stderr: str
    compiler_success: bool
    errors: list[dict]                 # parsed compiler errors as dicts

    # ── Token-efficient context ───────────────────────────────────────────
    context_window: str
    context_token_estimate: int

    # ── History / tracking ────────────────────────────────────────────────
    patches_applied: list[dict]        # per-iteration summary of tool calls made
    fix_summary: str
    seen_fingerprints: list[str]
    fingerprint_counts: dict

    # ── Terminal ──────────────────────────────────────────────────────────
    status: str                        # "running" | "success" | "abort" | "escalate"
    final_message: str

    # ── Vulnerability scan results ────────────────────────────────────────────
    vuln_summary: str
    vuln_updates: list

    # ── LLM telemetry ─────────────────────────────────────────────────────────
    usage_user_id: Optional[int]
    usage_session_id: Optional[int]
    usage_request_path: Optional[str]
    token_usage: list[dict]
    
    # ── Diff Tracking ─────────────────────────────────────────────────────────
    full_diff: str


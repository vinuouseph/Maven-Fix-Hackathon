"""
Node: parse_errors  (Project Fix agent)
────────────────────────────────────────
Parses javac/maven/gradle error output into structured dicts.
"""

import re
import logging
import hashlib
from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import RunnableConfig
from app.agents.project_fix_agent.state import AgentState

logger = logging.getLogger(__name__)

# Pattern: /path/to/File.java:[line]: error: message
_JAVAC_RE = re.compile(
    r"^(?P<path>[^\s:]+\.java):(?P<line>\d+):(?:\d+:)?\s*(?:error|warning):\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# Maven-style: [ERROR] /abs/path/File.java:[line,col] error message
_MAVEN_RE = re.compile(
    r"\[ERROR\]\s+(?P<path>[^\[\]]+\.java):\[(?P<line>\d+),(?P<col>\d+)\]\s+(?P<msg>.+)",
)


def _fingerprint(file_path: str, line_no: int, error_code: str) -> str:
    return hashlib.md5(
        f"{file_path}:{line_no}:{error_code}".encode()
    ).hexdigest()[:12]


def _rel_path(abs_path: str, work_dir: str) -> str:
    """Convert absolute path to relative-to-work_dir."""
    try:
        from pathlib import Path
        return str(Path(abs_path).relative_to(work_dir))
    except ValueError:
        return abs_path


def _parse_errors(stdout: str, stderr: str, work_dir: str) -> list[dict]:
    combined = stdout + "\n" + stderr
    errors: list[dict] = []
    seen: set[str] = set()

    # Try maven format first (more specific)
    for m in _MAVEN_RE.finditer(combined):
        path = _rel_path(m.group("path").strip(), work_dir)
        line = int(m.group("line"))
        msg  = m.group("msg").strip()
        fp   = _fingerprint(path, line, msg[:60])
        if fp not in seen:
            seen.add(fp)
            errors.append({
                "file_path":   path,
                "line_no":     line,
                "col_no":      int(m.group("col")),
                "error_code":  msg[:120],
                "raw_message": m.group(0).strip(),
                "fingerprint": fp,
            })

    # Fall back to raw javac format
    if not errors:
        for m in _JAVAC_RE.finditer(combined):
            path = _rel_path(m.group("path").strip(), work_dir)
            line = int(m.group("line"))
            msg  = m.group("msg").strip()
            fp   = _fingerprint(path, line, msg[:60])
            if fp not in seen:
                seen.add(fp)
                errors.append({
                    "file_path":   path,
                    "line_no":     line,
                    "col_no":      0,
                    "error_code":  msg[:120],
                    "raw_message": m.group(0).strip(),
                    "fingerprint": fp,
                })

    return errors


def parse_errors_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph node: parse compiler output into structured errors.
    Writes: errors.
    """
    stdout   = state.get("compiler_stdout", "")
    stderr   = state.get("compiler_stderr", "")
    work_dir = state["work_dir"]
    iteration = state.get("iteration", 1)

    if state.get("compiler_success"):
        dispatch_custom_event(
            "project_fix_trace",
            {"id": f"parse_{iteration}", "status": "completed",
             "title": "Parse Errors", "detail": "No errors — compilation successful!"},
            config=config,
        )
        return {**state, "errors": []}

    errors = _parse_errors(stdout, stderr, work_dir)
    logger.info(f"[project_fix/parse_errors] Found {len(errors)} error(s)")

    dispatch_custom_event(
        "project_fix_trace",
        {
            "id":     f"parse_{iteration}",
            "status": "completed",
            "title":  "Parse Errors",
            "detail": f"Found {len(errors)} compiler error(s).",
        },
        config=config,
    )

    return {**state, "errors": errors}

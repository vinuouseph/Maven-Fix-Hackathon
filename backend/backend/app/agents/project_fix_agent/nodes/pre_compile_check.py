"""
Node: pre_compile_check
────────────────────────
Runs a compile BEFORE the vulnerability scan to detect pre-existing build
errors that exist BEFORE any patching or AI fixes are applied.
"""

from __future__ import annotations

import subprocess
import logging
import os
from pathlib import Path
from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.agents.project_fix_agent.state import AgentState
from app.agents.project_fix_agent.nodes.compile import _find_command, TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts"}

def _find_project_root(work_dir: str) -> Path:
    """
    Return the directory that contains pom.xml / build.gradle,
    walking up to 3 levels into work_dir (handles ZIP nesting).
    """
    root = Path(work_dir)
    if any((root / f).exists() for f in _BUILD_FILES):
        return root
    for child in root.iterdir():
        if child.is_dir() and any((child / f).exists() for f in _BUILD_FILES):
            return child
        if child.is_dir():
            for grandchild in child.iterdir():
                if grandchild.is_dir() and any((grandchild / f).exists() for f in _BUILD_FILES):
                    return grandchild
    return root

def pre_compile_check_node(state: AgentState, config: RunnableConfig) -> AgentState:
    work_dir   = state["work_dir"]
    build_tool = state.get("build_tool", "")

    # Resolve the actual build root (handles nested ZIPs)
    project_root = _find_project_root(work_dir)
    project_root_str = str(project_root.resolve())

    # Auto-detect if empty
    if not build_tool:
        if (project_root / "pom.xml").exists():
            build_tool = "maven"
        elif (project_root / "build.gradle").exists() or (project_root / "build.gradle.kts").exists():
            build_tool = "gradle"
        else:
            build_tool = "maven"  # fallback

    logger.info("[pre_compile_check] Running initial compile check (pre-vuln-scan)…")

    dispatch_custom_event(
        "project_fix_trace",
        {
            "id":     "pre_compile_check",
            "status": "running",
            "title":  "Initial Compilation Check",
            "detail": "Compiling the project as-is to detect any pre-existing build errors…",
        },
        config=config,
    )

    cmd = _find_command(build_tool, project_root_str)

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root_str,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "JAVA_TOOL_OPTIONS": "-Dfile.encoding=UTF-8"},
        )
        success = result.returncode == 0
        stdout  = result.stdout
        stderr  = result.stderr
        logger.info(f"[pre_compile_check] Return code: {result.returncode}")
    except FileNotFoundError:
        stdout  = ""
        stderr  = f"Build tool not found: {cmd[0]}. Ensure Maven or Gradle is installed."
        success = False
        logger.error(f"[pre_compile_check] {stderr}")
    except subprocess.TimeoutExpired:
        stdout  = ""
        stderr  = f"Compilation timed out after {TIMEOUT_SECONDS}s."
        success = False
        logger.error("[pre_compile_check] Timeout on initial compile check")

    if success:
        logger.info("[pre_compile_check] ✓ Project compiles clean — no pre-existing errors")
        dispatch_custom_event(
            "project_fix_trace",
            {
                "id":     "pre_compile_check",
                "status": "completed",
                "title":  "Initial Compilation Passed ✓",
                "detail": (
                    "Project compiles clean — no pre-existing build errors found. "
                    "Proceeding to vulnerability scan…"
                ),
            },
            config=config,
        )
        return {
            **state,
            "work_dir":         project_root_str,
            "build_tool":       build_tool,
            "compiler_stdout":  stdout,
            "compiler_stderr":  stderr,
            "compiler_success": True,
        }

    logger.warning("[pre_compile_check] ✗ Project has pre-existing build errors!")

    raw_err = (stderr or stdout or "No output captured.")[:1000]

    dispatch_custom_event(
        "project_fix_trace",
        {
            "id":     "pre_compile_check",
            "status": "error",
            "title":  "⛔ Pre-existing Build Errors Detected",
            "detail": (
                "This project already fails to compile before any changes are made. "
                "Please fix these errors manually and re-upload the project."
            ),
        },
        config=config,
    )

    final_msg = (
        f"⛔ **Pre-existing Build Errors Detected**\n\n"
        f"This project fails to compile **before any vulnerability patches or AI fixes "
        f"were applied**. The Project Fix workflow can only resolve errors introduced by "
        f"dependency changes — it cannot fix fundamental project-level compilation problems "
        f"that exist in the original source.\n\n"
        f"**Please resolve the following errors manually, then re-upload the project:**\n\n"
        f"```\n{raw_err}\n```"
    )

    return {
        **state,
        "work_dir":         project_root_str,
        "build_tool":       build_tool,
        "compiler_stdout":  stdout,
        "compiler_stderr":  stderr,
        "compiler_success": False,
        "status":           "pre_compile_failed",
        "final_message":    final_msg,
    }

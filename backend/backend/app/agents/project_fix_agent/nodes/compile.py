"""
Node: compile  (Project Fix agent)
────────────────────────────────────
Runs mvn compile (or gradle compileJava) inside work_dir.
Also auto-detects the build tool from the project structure.
"""

import subprocess
import logging
import os
from pathlib import Path

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.agents.project_fix_agent.state import AgentState

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120

BUILD_COMMANDS = {
    "maven":  ["mvn", "clean", "compile", "-DskipTests", "-Dmaven.test.skip=true",
                "-B", "--no-transfer-progress"],
    "gradle": ["./gradlew", "clean", "compileJava", "--console=plain", "-x", "test"],
}
WRAPPER_COMMANDS = {
    "maven":  ["./mvnw", "clean", "compile", "-DskipTests", "-Dmaven.test.skip=true",
                "-B", "--no-transfer-progress"],
    "gradle": ["./gradlew", "clean", "compileJava", "--console=plain", "-x", "test"],
}


def _detect_build_tool(work_dir: str) -> str:
    """Detect maven vs gradle from project files."""
    root = Path(work_dir)
    # Search recursively for pom.xml or build.gradle
    if list(root.rglob("pom.xml")):
        return "maven"
    if list(root.rglob("build.gradle")) or list(root.rglob("build.gradle.kts")):
        return "gradle"
    return "maven"  # fallback


def _find_command(build_tool: str, work_dir: str) -> list[str]:
    """Pick the right compile command; prefer wrappers if present."""
    wrapper = WRAPPER_COMMANDS[build_tool]
    wrapper_path = os.path.join(work_dir, wrapper[0])
    if os.path.isfile(wrapper_path):
        os.chmod(wrapper_path, 0o755)
        return wrapper
    return BUILD_COMMANDS[build_tool]


def _find_work_dir(work_dir: str) -> str:
    """
    Return the directory that contains the build file.
    Handles the common case where the ZIP extracts into a nested sub-folder.
    """
    root = Path(work_dir)
    for pom in root.rglob("pom.xml"):
        return str(pom.parent)
    for g in list(root.rglob("build.gradle")) + list(root.rglob("build.gradle.kts")):
        return str(g.parent)
    return work_dir


def compile_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph node: run the compiler.
    Writes: compiler_stdout, compiler_stderr, compiler_success, iteration, build_tool.
    """
    work_dir   = state["work_dir"]
    build_tool = state.get("build_tool") or _detect_build_tool(work_dir)
    iteration  = state.get("iteration", 0) + 1
    build_dir  = _find_work_dir(work_dir)

    logger.info(f"[project_fix/compile] Iteration {iteration} — {build_tool} in {build_dir}")

    cmd = _find_command(build_tool, build_dir)

    build_args = state.get("build_args")
    if build_args:
        cmd.extend(build_args.split())
        
    cmd_str = " ".join(cmd)

    dispatch_custom_event(
        "project_fix_trace",
        {
            "id":     f"compile_{iteration}",
            "status": "running",
            "title":  f"Compile — Iteration {iteration}",
            "detail": f"Executing: {cmd_str}",
            "log_msg": f"⚙️ Executing command: {cmd_str}\n",
        },
        config=config,
    )

    try:
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "JAVA_TOOL_OPTIONS": "-Dfile.encoding=UTF-8"},
        )
        stdout  = result.stdout
        stderr  = result.stderr
        success = result.returncode == 0
        logger.info(f"[project_fix/compile] Return code: {result.returncode}")
    except FileNotFoundError:
        stdout  = ""
        stderr  = f"Build tool not found: {cmd[0]}. Ensure Maven or Gradle is installed."
        success = False
        logger.error(f"[project_fix/compile] {stderr}")
    except subprocess.TimeoutExpired:
        stdout  = ""
        stderr  = f"Compilation timed out after {TIMEOUT_SECONDS}s."
        success = False
        logger.error("[project_fix/compile] Timeout")

    dispatch_custom_event(
        "project_fix_trace",
        {
            "id":     f"compile_{iteration}",
            "status": "completed" if success else "error",
            "title":  f"Compile — Iteration {iteration}",
            "detail": "Build succeeded!" if success else "Build failed — parsing errors…",
        },
        config=config,
    )

    return {
        **state,
        "iteration":        iteration,
        "build_tool":       build_tool,
        "compiler_stdout":  stdout,
        "compiler_stderr":  stderr,
        "compiler_success": success,
    }

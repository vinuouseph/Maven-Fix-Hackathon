"""
Node: build_context  (Project Fix agent)
─────────────────────────────────────────
Assembles the minimal context window for the LLM:
  - Error list with file paths + line numbers
  - ±30 lines around each error site
  - pom.xml / build.gradle brief summary
  - Workspace file tree overview

Also updates seen_fingerprints for stuck-loop detection.
"""

import os
import re
import logging
from pathlib import Path

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.agents.project_fix_agent.state import AgentState

logger = logging.getLogger(__name__)

CONTEXT_LINES_AROUND  = 30
APPROX_CHARS_PER_TOKEN = 4

_SKIP_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__",
    "target", "build", ".gradle", ".idea", ".vscode",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_abs_path(rel_path: str, work_dir: str) -> str:
    """Resolve relative path inside work_dir, walking recursively as fallback."""
    direct = os.path.join(work_dir, rel_path)
    if os.path.isfile(direct):
        return direct
    for root, _, files in os.walk(work_dir):
        for fname in files:
            candidate = os.path.join(root, fname)
            if candidate.endswith(rel_path.replace("/", os.sep)):
                return candidate
    return direct


def _summarise_build_file(work_dir: str) -> str:
    """Extract a brief summary of pom.xml or build.gradle for LLM context."""
    root = Path(work_dir)

    # Try pom.xml first
    for pom in root.rglob("pom.xml"):
        try:
            text = pom.read_text(encoding="utf-8", errors="ignore")
            lines = ["## Build Config (pom.xml)"]

            parent_version = re.search(
                r"<parent>[\s\S]*?<version>(.+?)</version>[\s\S]*?</parent>", text
            )
            if parent_version:
                pv = parent_version.group(1).strip()
                lines.append(f"Spring Boot version: {pv}")
                try:
                    major = int(pv.split(".")[0])
                    ns = "jakarta.*" if major >= 3 else "javax.*"
                    lines.append(f"Use {ns} imports (Spring Boot {'3.x+' if major >= 3 else '2.x'})")
                except (ValueError, IndexError):
                    pass

            dep_blocks = re.findall(r"<dependency>[\s\S]*?</dependency>", text)
            dep_lines = []
            for block in dep_blocks:
                g = re.search(r"<groupId>(.+?)</groupId>", block)
                a = re.search(r"<artifactId>(.+?)</artifactId>", block)
                v = re.search(r"<version>(.+?)</version>", block)
                if g and a:
                    ver_str = v.group(1).strip() if v else "(managed)"
                    dep_lines.append(f"  {g.group(1).strip()}:{a.group(1).strip()}:{ver_str}")
            if dep_lines:
                lines.append("Dependencies:\n" + "\n".join(dep_lines[:30]))
                if len(dep_lines) > 30:
                    lines.append(f"  ... ({len(dep_lines) - 30} more)")
            return "\n".join(lines)
        except Exception:
            pass

    # Try build.gradle
    for gradle in list(root.rglob("build.gradle")) + list(root.rglob("build.gradle.kts")):
        try:
            text = gradle.read_text(encoding="utf-8", errors="ignore")
            return f"## Build Config (build.gradle)\n{text[:800]}"
        except Exception:
            pass

    return ""


def _compact_file_tree(work_dir: str, max_files: int = 80) -> str:
    """Return a brief file tree showing Java source structure."""
    root = Path(work_dir)
    lines = ["## Project File Overview"]
    count = 0

    # Focus on src/ directory
    src_root = root / "src"
    scan_root = src_root if src_root.exists() else root

    for path in sorted(scan_root.rglob("*")):
        parts = path.relative_to(root).parts
        if any(p in _SKIP_DIRS or p.startswith(".") for p in parts):
            continue
        if not path.is_file():
            continue
        if count >= max_files:
            lines.append(f"  ... (showing {max_files} of many files — use list_project_files tool for full tree)")
            break
        rel = str(path.relative_to(root))
        lines.append(f"  {rel}")
        count += 1

    return "\n".join(lines)


# ── Node ──────────────────────────────────────────────────────────────────────

def build_context_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph node: assemble context window for the LLM fix agent.
    Writes: context_window, context_token_estimate, seen_fingerprints, fingerprint_counts.
    """
    errors   = state["errors"]
    work_dir = state["work_dir"]
    iteration = state.get("iteration", 1)

    if not errors:
        return {**state, "context_window": "", "context_token_estimate": 0}

    dispatch_custom_event(
        "project_fix_trace",
        {"id": f"context_{iteration}", "status": "running",
         "title": "Build Context", "detail": "Assembling LLM context window…"},
        config=config,
    )

    # Update fingerprint tracking (needed for stuck-loop detection in router)
    current_fps = {e["fingerprint"] for e in errors}
    updated_fps = list(set(state.get("seen_fingerprints") or []) | current_fps)
    counts: dict = dict(state.get("fingerprint_counts") or {})
    for fp in current_fps:
        counts[fp] = counts.get(fp, 0) + 1

    sections = []

    # Build config summary
    build_summary = _summarise_build_file(work_dir)
    if build_summary:
        sections.append(build_summary)

    # Compact file tree
    file_tree = _compact_file_tree(work_dir)
    if file_tree:
        sections.append(file_tree)

    # Per-file error slices
    by_file: dict[str, list[dict]] = {}
    for err in errors:
        by_file.setdefault(err["file_path"], []).append(err)

    for rel_path, file_errors in by_file.items():
        abs_path = _find_abs_path(rel_path, work_dir)
        error_lines = {e["line_no"] for e in file_errors}

        try:
            with open(abs_path, encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
        except FileNotFoundError:
            sections.append(f"## File: {rel_path}\n# FILE NOT FOUND")
            continue

        total = len(all_lines)

        # Determine if this file is "stuck" (same errors repeating 3+ times)
        max_repeat = max(counts.get(e["fingerprint"], 1) for e in file_errors)
        is_stuck = max_repeat >= 3

        error_notes = "\n".join(
            f"  Line {e['line_no']}: {e['error_code']}"
            for e in sorted(file_errors, key=lambda x: x["line_no"])
        )

        if is_stuck and total <= 200:
            # ── STUCK FILE: include FULL file content for complete rewrite ──
            full_content = "".join(
                f"{i+1:4d} | {line.rstrip()}\n" for i, line in enumerate(all_lines)
            )
            sections.append(
                f"## ⚠️ STUCK FILE: {rel_path} ({total} lines total) — patched {max_repeat}x, STILL has errors\n"
                f"### YOUR PREVIOUS PATCHES ARE NOT WORKING. Read the FULL file and REWRITE it correctly.\n"
                f"### If another file defines the same @Bean, consolidate into ONE file and empty the other.\n"
                f"### Errors:\n{error_notes}\n"
                f"### FULL FILE CONTENT:\n"
                f"```\n{full_content}\n```"
            )
        else:
            # ── Normal context: ±N lines around each error site ──
            ctx = min(CONTEXT_LINES_AROUND * max_repeat, 80)

            # Build merged ranges
            ranges: list[tuple[int, int]] = []
            for ln in sorted(error_lines):
                start = max(1, ln - ctx)
                end   = min(total, ln + ctx)
                if ranges and start <= ranges[-1][1] + 1:
                    ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
                else:
                    ranges.append((start, end))

            slice_parts: list[str] = []
            for (rs, re_) in ranges:
                for i in range(rs - 1, re_):
                    ln_num = i + 1
                    marker = ">>>" if ln_num in error_lines else "   "
                    slice_parts.append(f"{marker} {ln_num:4d} | {all_lines[i].rstrip()}")
                slice_parts.append("")

            sections.append(
                f"## File: {rel_path} ({total} lines total)\n"
                f"### Errors:\n{error_notes}\n"
                f"### Relevant code (>>> marks error lines):\n"
                f"```\n{''.join(slice_parts)}\n```"
            )

    context_window = "\n\n".join(sections)
    token_estimate = len(context_window) // APPROX_CHARS_PER_TOKEN

    logger.info(
        f"[project_fix/build_context] {len(context_window)} chars "
        f"(~{token_estimate} tokens) across {len(by_file)} files"
    )

    dispatch_custom_event(
        "project_fix_trace",
        {"id": f"context_{iteration}", "status": "completed",
         "title": "Build Context",
         "detail": f"Context window ready (~{token_estimate} tokens, {len(by_file)} file(s))."},
        config=config,
    )

    return {
        **state,
        "context_window":        context_window,
        "context_token_estimate": token_estimate,
        "seen_fingerprints":     updated_fps,
        "fingerprint_counts":    counts,
    }

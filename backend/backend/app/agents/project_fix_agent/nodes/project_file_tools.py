"""
Project File Tools
──────────────────
Four LangChain StructuredTools the LLM uses to inspect and patch any file
in the project workspace:

  1. list_project_files   — browse the full directory tree
  2. read_file_lines      — read a specific line range from any file
  3. write_file_lines     — surgically replace a line range in any file
  4. create_new_file      — create a brand-new file (any extension)

All tools are built via build_project_file_tools(work_dir) so the
workspace path is captured in the closure and never exposed to the LLM.
"""

import logging
import os
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MAX_FILE_BYTES  = 128 * 1024   # 128 KB write cap
_MAX_READ_LINES  = 300          # safety cap per read call
_MAX_TREE_FILES  = 500          # max files in directory listing


# ── Input schemas ──────────────────────────────────────────────────────────────

class ListProjectFilesInput(BaseModel):
    subdir: str = Field(
        default="",
        description=(
            "Optional sub-directory path relative to the project root to list. "
            "Leave empty (or pass '') to list the entire project. "
            "Example: 'src/main/java/com/example'"
        ),
    )


class ReadFileLinesInput(BaseModel):
    relative_path: str = Field(
        description=(
            "Path of the file to read, relative to the project root. "
            "Example: src/main/java/com/example/service/UserService.java"
        )
    )
    start_line: int = Field(
        description="1-indexed line number to start reading from (inclusive)."
    )
    end_line: int = Field(
        description="1-indexed line number to stop reading at (inclusive)."
    )


class WriteFileLinesInput(BaseModel):
    relative_path: str = Field(
        description=(
            "Path of the file to patch, relative to the project root. "
            "Example: src/main/java/com/example/config/AppConfig.java"
        )
    )
    start_line: int = Field(
        description="1-indexed line number where the replacement should begin (inclusive)."
    )
    end_line: int = Field(
        description="1-indexed line number where the replacement should end (inclusive)."
    )
    replacement_content: str = Field(
        description=(
            "The new lines to splice in, replacing start_line..end_line. "
            "Everything outside this range is preserved verbatim. "
            "Do NOT wrap in markdown fences."
        )
    )


class CreateNewFileInput(BaseModel):
    relative_path: str = Field(
        description=(
            "Path of the new file relative to the project root. "
            "Example: src/main/java/com/example/dto/UserDTO.java "
            "or src/main/resources/application-dev.properties"
        )
    )
    content: str = Field(
        description=(
            "Full content of the new file. For Java files include the "
            "package declaration, all imports, and the complete class body. "
            "Do NOT wrap in markdown fences."
        )
    )


# ── Tool factory ───────────────────────────────────────────────────────────────

def build_project_file_tools(work_dir: str, state_ref: dict = None) -> list:
    """
    Build the four LangChain tools that operate inside `work_dir`.
    Call once per LLM node invocation with the current project directory.

    Returns a list of StructuredTool instances ready for llm.bind_tools().
    """
    work_path = Path(work_dir)

    # ── TOOL 1: list_project_files ─────────────────────────────────────────────

    def _list_project_files(subdir: str = "") -> str:
        """Return a formatted directory tree of the project workspace."""
        root = work_path / subdir if subdir else work_path
        root = root.resolve()

        # Prevent path traversal outside work_dir
        try:
            root.relative_to(work_path.resolve())
        except ValueError:
            return "ERROR: subdir is outside the project root."

        if not root.exists():
            return f"ERROR: directory not found: {subdir!r}"

        lines = [f"Project tree: {subdir or '/'}\n"]
        file_count = 0

        # Directories to skip
        SKIP_DIRS = {
            ".git", ".svn", ".hg", "node_modules", "__pycache__",
            "target", "build", ".gradle", ".idea", ".vscode",
            "out", ".classpath", ".settings",
        }

        for path in sorted(root.rglob("*")):
            # Skip hidden and build-output directories
            parts = path.relative_to(root).parts
            if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
                continue
            if file_count >= _MAX_TREE_FILES:
                lines.append(f"... (truncated at {_MAX_TREE_FILES} entries)")
                break

            depth = len(parts) - 1
            indent = "  " * depth
            if path.is_dir():
                lines.append(f"{indent}📁 {path.name}/")
            else:
                size_kb = path.stat().st_size // 1024
                size_str = f" ({size_kb} KB)" if size_kb > 0 else ""
                lines.append(f"{indent}📄 {path.name}{size_str}")
                file_count += 1

        logger.info(f"[project_file_tools] list_project_files: {file_count} files under '{subdir or '/'}'")
        return "\n".join(lines)

    # ── TOOL 2: read_file_lines ────────────────────────────────────────────────

    def _read_file_lines(relative_path: str, start_line: int, end_line: int) -> str:
        """Return a numbered line range from any source file."""
        abs_path = work_path / relative_path
        if not abs_path.exists():
            return f"ERROR: file not found: {relative_path}"
        if start_line < 1 or end_line < start_line:
            return "ERROR: start_line must be >= 1 and end_line must be >= start_line"
        if (end_line - start_line + 1) > _MAX_READ_LINES:
            return (
                f"ERROR: requested range spans {end_line - start_line + 1} lines "
                f"(max {_MAX_READ_LINES}). Narrow the range."
            )

        try:
            all_lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
            actual_end = min(end_line, len(all_lines))
            selected = all_lines[start_line - 1: actual_end]

            if not selected:
                return (
                    f"ERROR: line range {start_line}-{end_line} is out of range "
                    f"(file has {len(all_lines)} lines)"
                )

            header = f"// {relative_path}  [lines {start_line}-{actual_end} of {len(all_lines)}]\n"
            numbered = "\n".join(
                f"{start_line + i}: {line}" for i, line in enumerate(selected)
            )
            logger.info(
                f"[project_file_tools] read_file_lines: {relative_path} "
                f"lines {start_line}-{actual_end}"
            )
            return header + numbered
        except Exception as exc:
            logger.error(f"[project_file_tools] read_file_lines failed for {relative_path}: {exc}")
            return f"ERROR: {exc}"

    # ── TOOL 3: write_file_lines ───────────────────────────────────────────────

    def _write_file_lines(
        relative_path: str,
        start_line: int,
        end_line: int,
        replacement_content: str,
    ) -> str:
        """Splice replacement_content into an existing file at the given line range."""
        abs_path = work_path / relative_path
        if not abs_path.exists():
            return f"ERROR: file not found: {relative_path}"
        if start_line < 1 or end_line < start_line:
            return "ERROR: start_line must be >= 1 and end_line must be >= start_line"

        encoded = replacement_content.encode("utf-8")
        if len(encoded) > _MAX_FILE_BYTES:
            return (
                f"ERROR: replacement_content too large "
                f"({len(encoded)} bytes, max {_MAX_FILE_BYTES})"
            )

        try:
            original_text = abs_path.read_text(encoding="utf-8", errors="replace")
            all_lines = original_text.splitlines(keepends=True)
            clamped_end = min(end_line, len(all_lines))

            # Ensure replacement ends with newline so lines stitch cleanly
            new_block = replacement_content
            if new_block and not new_block.endswith("\n"):
                new_block += "\n"

            before  = all_lines[: start_line - 1]
            after   = all_lines[clamped_end:]
            spliced = "".join(before) + new_block + "".join(after)

            abs_path.write_text(spliced, encoding="utf-8")

            replaced_count = clamped_end - (start_line - 1)
            new_line_count = spliced.count("\n")

            if state_ref is not None:
                import difflib
                diff_lines = list(difflib.unified_diff(
                    all_lines,
                    spliced.splitlines(keepends=True),
                    fromfile="a/" + relative_path,
                    tofile="b/" + relative_path,
                    n=3
                ))
                diff_str = "".join(diff_lines)
                if diff_str:
                    current_diff = state_ref.get("full_diff", "")
                    state_ref["full_diff"] = current_diff + "\n" + diff_str if current_diff else diff_str

            logger.info(
                f"[project_file_tools] write_file_lines: {relative_path} "
                f"replaced lines {start_line}-{clamped_end} "
                f"({replaced_count} lines → {new_block.count(chr(10))} lines)"
            )
            return (
                f"OK: replaced lines {start_line}-{clamped_end} in {relative_path}. "
                f"File now has {new_line_count} lines."
            )
        except Exception as exc:
            logger.error(f"[project_file_tools] write_file_lines failed for {relative_path}: {exc}")
            return f"ERROR: {exc}"

    # ── TOOL 4: create_new_file ────────────────────────────────────────────────

    def _create_new_file(relative_path: str, content: str) -> str:
        """Create a brand-new file in the project workspace."""
        abs_path = work_path / relative_path

        # Prevent path traversal
        try:
            abs_path.resolve().relative_to(work_path.resolve())
        except ValueError:
            return "ERROR: relative_path is outside the project root."

        if abs_path.exists():
            return (
                f"SKIPPED: {relative_path} already exists. "
                "Use write_file_lines to modify an existing file."
            )

        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_FILE_BYTES:
            return (
                f"ERROR: content too large ({len(encoded)} bytes, max {_MAX_FILE_BYTES})"
            )

        try:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            
            if state_ref is not None:
                import difflib
                diff_lines = list(difflib.unified_diff(
                    [],
                    content.splitlines(keepends=True),
                    fromfile="/dev/null",
                    tofile="b/" + relative_path,
                    n=3
                ))
                diff_str = "".join(diff_lines)
                if diff_str:
                    current_diff = state_ref.get("full_diff", "")
                    state_ref["full_diff"] = current_diff + "\n" + diff_str if current_diff else diff_str

            logger.info(
                f"[project_file_tools] create_new_file: {relative_path} "
                f"({len(encoded)} bytes)"
            )
            return f"OK: created {relative_path}"
        except Exception as exc:
            logger.error(f"[project_file_tools] create_new_file failed for {relative_path}: {exc}")
            return f"ERROR: {exc}"

    # ── Assemble tools ─────────────────────────────────────────────────────────

    list_tool = StructuredTool.from_function(
        func=_list_project_files,
        name="list_project_files",
        description=(
            "List all files and directories in the project workspace. "
            "Use this first when you need to understand the project structure — "
            "which source files exist, where pom.xml / build.gradle lives, etc. "
            "Pass an optional subdir to narrow the listing (e.g. 'src/main/java'). "
            "Returns a formatted directory tree with file sizes."
        ),
        args_schema=ListProjectFilesInput,
        return_direct=False,
    )

    read_tool = StructuredTool.from_function(
        func=_read_file_lines,
        name="read_file_lines",
        description=(
            "Read a specific range of lines from any file in the project. "
            "Use this BEFORE patching to see the exact current content at a location. "
            "Provide relative_path (relative to project root), start_line and end_line "
            "(both 1-indexed, inclusive). Returns the raw lines with their line numbers "
            "so you can build a precise write_file_lines call. "
            "Maximum 300 lines per call — narrow the range if the file is large."
        ),
        args_schema=ReadFileLinesInput,
        return_direct=False,
    )

    write_tool = StructuredTool.from_function(
        func=_write_file_lines,
        name="write_file_lines",
        description=(
            "Surgically replace a specific line range in an existing file. "
            "Use this after read_file_lines to patch the exact region you need to change. "
            "Provide relative_path, start_line, end_line (1-indexed, inclusive), "
            "and replacement_content (the new lines that replace the old ones). "
            "Lines outside the range are untouched — this is safer than rewriting the whole file."
        ),
        args_schema=WriteFileLinesInput,
        return_direct=False,
    )

    create_tool = StructuredTool.from_function(
        func=_create_new_file,
        name="create_new_file",
        description=(
            "Create a brand-new file in the project workspace. "
            "Use when a compilation error is caused by a missing class, interface, enum, "
            "DTO, config class, or any other file that does not yet exist. "
            "Works for any file type: .java, .xml, .properties, .yml, etc. "
            "For Java files include the full package declaration, imports, and class body. "
            "Returns SKIPPED if the file already exists — use write_file_lines instead."
        ),
        args_schema=CreateNewFileInput,
        return_direct=False,
    )

    return [list_tool, read_tool, write_tool, create_tool]

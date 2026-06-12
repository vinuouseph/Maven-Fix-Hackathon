"""
Node: llm_fix_agent  (Project Fix agent)
──────────────────────────────────────────
Calls the LLM with the four project file tools bound.
The LLM does NOT emit unified diffs — it uses tools exclusively:

  1. list_project_files  — browse workspace structure
  2. read_file_lines     — inspect exact current content
  3. write_file_lines    — splice the fix into the file
  4. create_new_file     — create missing classes / config files

Tool calls are executed IMMEDIATELY (synchronously) in this node so
changes are on disk before the next compile cycle.
"""

import os
import logging
import asyncio
import httpx

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.agents.project_fix_agent.state import AgentState
from app.agents.project_fix_agent.nodes.project_file_tools import build_project_file_tools
from app.llm.llm_registry import build_llm_model

logger = logging.getLogger(__name__)

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_TRACING",    "false")


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert Java / Spring Boot compiler error fixer.

You have FOUR tools available. Use them exclusively — do NOT output unified diffs.

TOOLS:
  list_project_files(subdir?)      → view the workspace directory tree
  read_file_lines(path, start, end)→ read specific lines from any file (numbered output)
  write_file_lines(path, start, end, replacement_content)
                                   → splice fixed lines into an existing file
  create_new_file(path, content)   → create a completely new file (any type)

WORKFLOW — always follow this pattern:
  1. Use list_project_files if you need to understand the project structure.
  2. Use read_file_lines to see the EXACT current content near an error site before patching.
  3. Use write_file_lines to splice in only the changed lines. Preserve everything else.
  4. Use create_new_file only when a required class / config file does not exist yet.

RULES:
  1. FIX ALL ERRORS in this response — do not leave any unaddressed.
  2. After read_file_lines, use the line numbers shown to make a precise write_file_lines call.
  3. When patching imports or a small method, replace ONLY the minimal range of lines.
  4. NEVER delete class fields, entity variables, or getter/setter methods when patching.
  5. JAVAX → JAKARTA: If Spring Boot >= 3.x, replace ALL javax.* with jakarta.* equivalents.
  6. CASCADING ERRORS: Fix every error in the current list — including secondary effects.
  7. IMPORT ERRORS: Fix ALL broken imports in a file in a SINGLE write_file_lines call.
  8. MISSING CLASSES: Use create_new_file for any missing DTOs, configs, or exceptions.
  9. You may call multiple tools in sequence within one response — they execute in order.
 10. Do NOT output any prose, explanation, or markdown fences outside of tool calls.
"""

HUMAN_PROMPT_TEMPLATE = """## Compiler Errors — Iteration {iteration} ({error_count} error(s) remaining)
{error_list}

## Code Context
{context_window}

## Previous Iterations Summary
{iteration_history}

Use your tools to fix ALL errors listed above. Start now:"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_error_list(errors: list[dict]) -> str:
    return "\n".join(f"  - {e['file_path']}:{e['line_no']} — {e['error_code']}" for e in errors)


def _build_iteration_history(patches_applied: list[dict]) -> str:
    if not patches_applied:
        return "  No fixes applied yet."
    lines = []
    for p in patches_applied:
        itr   = p.get("iteration", "?")
        tools = p.get("tools_called", [])
        lines.append(f"  [Iter {itr}] Tools called: {', '.join(tools) or '(none)'}")
    return "\n".join(lines)


# ── Tool title lookup ──────────────────────────────────────────────────────────
_TOOL_TITLES = {
    "list_project_files": ("Listing Project Files",  "Files Listed",     "File List Failed"),
    "read_file_lines":    ("Reading File Lines",      "File Lines Read",  "File Read Failed"),
    "write_file_lines":   ("Patching File Lines",     "File Patched",     "Patch Failed"),
    "create_new_file":    ("Creating New File",       "File Created",     "File Create Failed"),
}


# ── Node ──────────────────────────────────────────────────────────────────────

def llm_fix_agent_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph node: invoke LLM with four tools, execute all tool calls
    synchronously, return updated state.
    """
    errors          = state["errors"]
    context         = state.get("context_window", "")
    iteration       = state.get("iteration", 1)
    work_dir        = state["work_dir"]
    patches_applied = list(state.get("patches_applied") or [])
    fix_summary     = state.get("fix_summary", "")

    iteration_history = _build_iteration_history(patches_applied)

    human_prompt = HUMAN_PROMPT_TEMPLATE.format(
        iteration=iteration,
        error_count=len(errors),
        error_list=_format_error_list(errors),
        context_window=context,
        iteration_history=iteration_history,
    )

    token_estimate = (len(SYSTEM_PROMPT) + len(human_prompt)) // 4
    logger.info(f"[project_fix/llm_fix] Sending ~{token_estimate} input tokens to LLM")

    dispatch_custom_event(
        "project_fix_trace",
        {
            "id":     f"llm_fix_{iteration}",
            "status": "running",
            "title":  f"AI Fix — Iteration {iteration}",
            "detail": f"Analyzing {len(errors)} error(s) and selecting tool calls…",
        },
        config=config,
    )

    llm            = build_llm_model()
    tools          = build_project_file_tools(work_dir, state)
    llm_with_tools = llm.bind_tools(tools)
    tool_map       = {t.name: t for t in tools}

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ]

        tools_called: list[str] = []

        for step in range(4):
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            usage = getattr(response, "usage_metadata", None)
            in_tokens = 0
            out_tokens = 0
            if usage:
                in_tokens = usage.get("input_tokens", 0)
                out_tokens = usage.get("output_tokens", 0)
            else:
                metadata = getattr(response, "response_metadata", {})
                token_usage_dict = metadata.get("token_usage", metadata.get("usage", {}))
                in_tokens = token_usage_dict.get("prompt_tokens", 0)
                out_tokens = token_usage_dict.get("completion_tokens", 0)
                if in_tokens == 0 and out_tokens == 0:
                    in_tokens = token_usage_dict.get("input_tokens", 0)
                    out_tokens = token_usage_dict.get("output_tokens", 0)
            
            # Fallback for streaming models that strip usage metrics (e.g. genailab)
            if in_tokens == 0 and out_tokens == 0:
                try:
                    import tiktoken
                    enc = tiktoken.get_encoding("cl100k_base")
                    in_tokens = len(enc.encode(str(messages[:-1]), allowed_special="all")) # exclude the response
                    out_tokens = len(enc.encode(str(response.content), allowed_special="all"))
                except Exception as e:
                    import traceback
                    with open("/tmp/tiktoken_error.log", "a") as f:
                        f.write(f"Tiktoken fallback failed: {e}\n{traceback.format_exc()}\n")
            
            if in_tokens >= 0 or out_tokens >= 0:
                token_usage = state.get("token_usage", [])
                token_usage.append({
                    "model_name": getattr(response, "response_metadata", {}).get("model_name", settings.coding_chat_model),
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens
                })
                state["token_usage"] = token_usage

            # ── Execute tool calls ─────────────────────────────────────────────
            tool_results_executed = False

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id   = tool_call["id"]

                run_title, ok_title, err_title = _TOOL_TITLES.get(
                    tool_name, ("Running Tool", "Tool Done", "Tool Failed")
                )

                # Brief parameter description for the UI
                detail_arg = (
                    tool_args.get("relative_path")
                    or tool_args.get("subdir")
                    or ""
                )
                detail = f"{tool_name}({detail_arg!r})" if detail_arg else f"{tool_name}()"

                dispatch_custom_event(
                    "project_fix_trace",
                    {"id": f"tool_{tool_name}_{iteration}_{step}", "status": "running",
                     "title": run_title, "detail": detail},
                    config=config,
                )

                if tool_name in tool_map:
                    result = tool_map[tool_name].invoke(tool_args)
                    tools_called.append(tool_name)
                    ok = not str(result).startswith("ERROR")
                    logger.info(f"[project_fix/llm_fix] {tool_name}: {str(result)[:120]}")

                    dispatch_custom_event(
                        "project_fix_trace",
                        {"id": f"tool_{tool_name}_{iteration}_{step}",
                         "status": "completed" if ok else "error",
                         "title": ok_title if ok else err_title,
                         "detail": str(result)[:200]},
                        config=config,
                    )
                    
                    from langchain_core.messages import ToolMessage
                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_id, name=tool_name))
                    tool_results_executed = True
                else:
                    logger.warning(f"[project_fix/llm_fix] Unknown tool: {tool_name}")
                    from langchain_core.messages import ToolMessage
                    messages.append(ToolMessage(content=f"ERROR: Unknown tool {tool_name}", tool_call_id=tool_id, name=tool_name))
                    tool_results_executed = True
                    
            if not tool_results_executed:
                break

        # ── Update iteration patch record ──────────────────────────────────
        patches_applied.append({
            "iteration":    iteration,
            "tools_called": tools_called,
        })

        # Update rolling fix summary
        if tools_called:
            tools_line = f"[iter {iteration}] {', '.join(tools_called)}"
            updated_summary = (
                (fix_summary + "\n" if fix_summary else "") + tools_line
            )
            if len(updated_summary) > 400:
                updated_summary = "\n".join(updated_summary.splitlines()[-4:])
        else:
            updated_summary = fix_summary

        dispatch_custom_event(
            "project_fix_trace",
            {
                "id":     f"llm_fix_{iteration}",
                "status": "completed",
                "title":  f"AI Fix — Iteration {iteration}",
                "detail": f"{len(tools_called)} tool call(s) executed.",
            },
            config=config,
        )

        return {
            **state,
            "patches_applied": patches_applied,
            "fix_summary":     updated_summary,
            "token_usage":     state.get("token_usage", []),
            "full_diff":       state.get("full_diff", ""),
        }

    except Exception as e:
        logger.error(f"[project_fix/llm_fix] LLM call failed: {e}")
        dispatch_custom_event(
            "project_fix_trace",
            {"id": f"llm_fix_{iteration}", "status": "error",
             "title": "AI Fix Failed", "detail": str(e)},
            config=config,
        )
        return {**state}

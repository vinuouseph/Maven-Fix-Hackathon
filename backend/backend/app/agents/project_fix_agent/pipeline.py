import json, asyncio

node_messages = {
                "guardrails": "Verifying enterprise security guardrails...",
                "intent_classifier": "Classifying query intent...",
                "query_rewriter": "Rewriting the query...",
                "out_of_scope_responder": "Handling out of scope request...",
                "conversational_responder": "Generating conversational response...",
                "app_logic_router": "Extracting application configuration logic...",
                "deep_thinking": "Thinking deeply...",
                "main_ai_worker": "Processing ConfigForge Desk request...",
                "smart_router": "Smart routing...",
                "analysis": "Analyzing document structure...",
                "hitl_metadata_interrupt": "Waiting for metadata...",
                "hitl_grid_interrupt": "Waiting for grid confirmation...",
                "correction": "Applying metadata corrections...",
                "format": "Formatting final configuration payload...",
                "hitl_sql_interrupt": "Waiting for SQL preferences...",
                "sql_generator": "Generating Database Configuration SQL...",
                "hitl_postprocessor_interrupt": "Waiting for postprocessor decision...",
                "postprocessor_router": "Routing postprocessor request...",
                "java_generator": "Generating Java ProcessorHook code...",
                "sql_postprocessor": "Generating SQL postprocessor query...",
                "hitl_postprocessor_review": "Waiting for code review...",
                "java_verify": "Verifying Java code API and schema...",
                "sql_verify": "Verifying SQL code schema...",
                "java_compile": "Compiling Java and packaging JAR...",
                "sql_save": "Saving SQL script to disk...",
                "hitl_package_interrupt": "Waiting for package confirmation...",
                "package_generator": "Generating downloadable package...",
                # JSON Converter workflow
                "jc_parse": "Parsing and validating JSON input...",
                "jc_format_interrupt": "Waiting for format selection...",
                "jc_convert": "Converting JSON to target format...",
                # Compile Fix
                "upload_zip": "Preparing project workspace...",
                "vuln_scan": "Scanning pom.xml for vulnerabilities and outdated dependencies...",
                "compile": "Running compiler...",
                "parse_errors": "Parsing compiler output...",
                "build_context": "Building context window for AI...",
                "llm_fix_agent": "Generating code fixes...",
                "apply_patch": "Applying patches to source code...",
                "success": "Compilation successful!",
                "abort": "Max iterations reached without success.",
                "escalate": "Agent stuck, escalating to user.",
                # Compile Fix 2
                "pom_updation_node": "Scanning and patching pom.xml for vulnerabilities and outdated dependencies...",
                "compile_node": "Running compiler...",
                "parse_errors_node": "Parsing compiler output...",
                "extract_context_node": "Extracting context window for AI...",
                "analyze_and_fix_node": "Generating code fixes...",
                "apply_fix_node": "Applying patches to source code...",
                "success_node": "Compilation successful!",
                "escalate_node": "Agent stuck, escalating to user.",
                # Project Fix
                "pom_update":    "Scanning and patching pom.xml for vulnerabilities...",
                "compile":       "Running compiler...",
                "parse_errors":  "Parsing compiler output...",
                "build_context": "Building context window for AI...",
                "llm_fix_agent": "AI using tools to inspect and patch files...",
                "success":       "Compilation successful!",
                "abort":         "Max iterations reached without success.",
                "escalate":      "Agent stuck, escalating to user.",
            }

node_names = {
    "guardrails": "Guardrails",
    "smart_router": "Routing & Rewriting",
    "query_rewriter": "Query Rewriter",
    "intent_classifier": "Intent Classifier",
    "out_of_scope_responder": "Out Of Scope",
    "conversational_responder": "Conversational Responder",
    "app_logic_router": "Application Logic Router",
    "deep_thinking": "Deep Thinking",
    "main_ai_worker": "ConfigForge Desk Processing",
    "analysis": "Analysing File Structure",
    "hitl_metadata_interrupt": "Awaiting Your Input",
    "hitl_grid_interrupt": "Awaiting Grid Confirmation",
    "correction": "Applying Corrections",
    "format": "Generating Configuration",
    "hitl_sql_interrupt": "Awaiting SQL Details",
    "sql_generator": "Generating Database Config SQL",
    "hitl_postprocessor_interrupt": "Awaiting PostProcessor Decision",
    "postprocessor_router": "Routing PostProcessor",
    "java_generator": "Generating Java ProcessorHook",
    "sql_postprocessor": "Generating SQL Query",
    "hitl_postprocessor_review": "Awaiting Code Review",
    "java_verify": "Verifying Java Code",
    "sql_verify": "Verifying SQL Code",
    "java_compile": "Compiling & Packaging JAR",
    "sql_save": "Saving SQL Script",
    "hitl_package_interrupt": "Awaiting Package Confirmation",
    "package_generator": "Generating Download Package",
    # JSON Converter workflow
    "jc_parse": "JSON Parser",
    "jc_format_interrupt": "Awaiting Format Selection",
    "jc_convert": "Converting JSON",

    # Compile Fix Agent
    "upload_zip": "Project Workspace Initialization",
    "compile": "Running Build Compiler",
    "parse_errors": "Parsing Compiler Errors",
    "build_context": "Building Fix Context",
    "llm_fix_agent": "Generating Code Patches",
    "apply_patch": "Applying AI Patches",
    "success": "Build Verification Passed",
    "abort": "Max Iterations Reached",
    "escalate": "Escalating to User",
    # New nodes
    "pre_compile_check": "Pre-scan Compile Check",
    "pre_compile_escalate": "Pre-existing Errors Detected",
    "vuln_scan": "Vulnerability Scan",
    # Compile Fix 2 Agent
    "pom_updation_node": "POM Dependency Update",
    "compile_node": "Running Build Compiler",
    "parse_errors_node": "Parsing Compiler Errors",
    "extract_context_node": "Extracting Context",
    "analyze_and_fix_node": "Generating Code Patches",
    "apply_fix_node": "Applying AI Patches",
    "success_node": "Build Verification Passed",
    "escalate_node": "Escalating to User",
}

def get_initial_state(project_path : str, build_args: str = None) -> dict:

    initial_state = {
        "work_dir": project_path,
        "build_tool": "",
        "build_args": build_args,
        "iteration": 0,
        "max_iterations": 20,
        "compiler_stdout": "",
        "compiler_stderr": "",
        "compiler_success": False,
        "errors": [],
        "context_window": "",
        "context_token_estimate": 0,
        "patches_applied": [],
        "fix_summary": "",
        "seen_fingerprints": [],
        "fingerprint_counts": {},
        "status": "running",
        "final_message": "",
        "vuln_summary": "",
        "vuln_updates": []
    }

    return initial_state

def sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

async def run_the_pipeline(initial_state:dict, final_state:dict):
    from app.agents.project_fix_agent.graph import graph as project_fix_graph
    graph = project_fix_graph
    # 20 iterations × ~4 steps per iteration = 80; 150 gives safe headroom
    config = {"recursion_limit": 150}
    streamed_content = ""

    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event["event"]
        name = event["name"]
        tags = event.get("tags", [])

        # Catch Node Startup (Dynamic Progress Indicator)
        if kind == "on_chain_start" and name in node_messages:
            trace_msg = node_messages.get(name, f"Running {name}...")
            yield sse_event({
                "type": "trace",
                "id": f"node_{name}",
                "status": "running",
                "title": node_names.get(name, name),
                "detail": trace_msg,
            })
            await asyncio.sleep(0)

        # Catch Node Updates (Graph Logic)
        elif kind == "on_chain_end":
            # Update final_state for any node that returns a dict
            output = event["data"].get("output")
            if isinstance(output, dict):
                final_state.update(output)

            # Only emit trace events for known static nodes
            if name in node_messages:
                trace_msg = node_messages.get(name, f"Processed {name}")
                yield sse_event({
                    "type": "trace",
                    "id": f"node_{name}",
                    "status": "completed",
                    "title": node_names.get(name, name),
                    "detail": trace_msg,
                })
                await asyncio.sleep(0)
        elif kind == "on_custom_event":
            print(
                f"🔥 [FASTAPI STREAM] Caught custom event! Name: {name} | Data: {event.get('data')}")
            custom_data = event.get("data", {})

            # If this custom event represents a trace step, also stream a trace update
            if "status" in custom_data:
                yield sse_event({
                    "type": "trace",
                    "id": custom_data.get("id", name),
                    "status": custom_data.get("status", "running"),
                    "title": custom_data.get("title", name),
                    "detail": custom_data.get("detail", ""),
                })
                await asyncio.sleep(0.02)  # Short delay for visual pacing

            if "log_msg" in custom_data:
                yield sse_event({
                    "type": "delta",
                    "content": custom_data.get("log_msg", "") + "\n"
                })
                await asyncio.sleep(0.02)

            yield sse_event({
                "type": "custom_node_event",
                "event_name": name,
                "data": custom_data
            })
            await asyncio.sleep(0)
        # Catch Internal Thinking & LLM Generation (Model Streams)
        elif kind == "on_chat_model_stream":
            # Only stream output coming from our responder nodes
            if any(t.startswith("langgraph_node:main_ai_worker") for t in tags) or any(
                    t.startswith("langgraph_node:conversational_responder") for t in tags):
                chunk = event["data"].get("chunk")
                if not chunk:
                    continue

                # Extract Provider-Native Reasoning (e.g., DeepSeek API reasoning_content)
                reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                content = chunk.content

                if reasoning:
                    yield sse_event({"type": "thinking_delta", "content": reasoning})
                    await asyncio.sleep(0)

                if content and isinstance(content, str):
                    # Extract Text-Based Thinking (e.g., Open Source <think> tags)
                    if "<think>" in content:
                        is_thinking = True
                        content = content.replace("<think>", "")

                    if "</think>" in content:
                        is_thinking = False
                        parts = content.split("</think>")
                        if parts[0]:
                            yield sse_event({"type": "thinking_delta", "content": parts[0]})
                        if len(parts) > 1 and parts[1]:
                            streamed_content += parts[1]
                            yield sse_event({"type": "delta", "content": parts[1]})
                        continue

                    # Standard vs Thinking Streaming Path
                    if is_thinking:
                        yield sse_event({"type": "thinking_delta", "content": content})
                    else:
                        streamed_content += content
                        yield sse_event({"type": "delta", "content": content})
                    await asyncio.sleep(0)
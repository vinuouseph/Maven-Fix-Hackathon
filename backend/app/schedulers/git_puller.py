import os.path
import logging
from sqlalchemy.orm import Session

from app.agents.project_fix_agent.pipeline import get_initial_state, run_the_pipeline
from app.db_configs.models import GitRepos
from app.process.git_utils import extract_project_name, pull_via_git
from app.services.admin.git_repo_services import get_url_location
from app.workers.models import SpringFixResult

logger = logging.getLogger(__name__)

cwd_dict = {}

async def pull_from_git():
    new_cwd_dict = cwd_dict.copy()
    try:
        if new_cwd_dict is not None:
            for wd, build_args in new_cwd_dict.items():
                if os.path.exists(wd):
                    project_name = extract_project_name(wd)
                    logger.info(f"pulling from git for project {project_name}....")
                    if wd is not None:
                        pull_result = pull_via_git(wd=wd)

                        if 'already up to date' in pull_result.lower():
                            logger.info(f"{project_name} is already upto date")
                        else:
                            logger.info(f"""some changes are there for {project_name}
                                                changes are : {pull_result}
                                            """)
                            initial_state : dict = get_initial_state(project_path=wd, build_args=build_args)
                            final_state = initial_state.copy()
                            async for stream_chunk in run_the_pipeline(initial_state=initial_state,
                                                                       final_state=final_state):
                                pass

                            print(final_state)

                else:
                    logger.info(f"Directory {wd} not found...")
                    cwd_dict.pop(wd, None)

    except Exception as e:
        logger.error(e)

def fetch_git_project_on_startup(db : Session):
    try:
        list_of_git_repos: list[GitRepos] = db.query(GitRepos).all()
        for git_repo in list_of_git_repos:
            cwd_dict[git_repo.git_directory_location] = git_repo.build_args
    finally:
        db.close()

async def update_cwd_list_run_pipeline(full_directory_location: str, temp_directory_location: str, build_args: str = None, project_id: int = 0):
    initial_state: dict = get_initial_state(project_path=temp_directory_location, build_args=build_args)
    final_state = initial_state.copy()

    import json
    log_file_path = os.path.join(temp_directory_location, "pipeline_stream.log")
    
    # Initialize / clear the log file
    with open(log_file_path, "w") as f:
        pass

    async for stream_chunk in run_the_pipeline(initial_state=initial_state, final_state=final_state):
        with open(log_file_path, "a") as f:
            f.write(stream_chunk)

    iteration_count : int = final_state['iteration']
    vuln_count : int = 0
    compiler_success : bool = final_state['compiler_success']

    compile_status = final_state.get("status", "unknown")
    compile_msg = final_state.get("final_message", "")
    vuln_summary = final_state.get("vuln_summary", "")

    if compile_status == "success":
        status_line = "✅ Compilation succeeded — all errors resolved!"
    elif compile_status == "abort":
        status_line = "⚠️ Max iterations reached — partial fixes applied."
    elif compile_status == "escalate":
        status_line = "⚠️ Agent escalating — repeating errors need manual review."
    else:
        status_line = f"Status: {compile_status}"

    final_event = json.dumps({"type": "trace", "id": compile_status, "status": "completed", "title": "Pipeline Finished", "detail": status_line})
    with open(log_file_path, "a") as f:
        f.write(f"data: {final_event}\n\n")

    reply_parts = [status_line]
    if vuln_summary:
        reply_parts.append(f"\n{vuln_summary}")
    if compile_msg:
        reply_parts.append(f"\n{compile_msg}")
    full_diff = final_state.get("full_diff", "").strip()
    attachments = ''
    if full_diff:
        reply_parts.append("\n**Code Changes Applied:**\n```diff\n" + full_diff + "\n```")
        summary_list = extract_diff_summary(full_diff)
        if summary_list:
            import json
            reply_parts.append("\n**Files Changed Summary:**\n```diffsummary\n" + json.dumps(summary_list) + "\n```")

        try:
            from app.process.code_compiler_tools import create_pdf_for_changes, update_metadata_excel, generate_reason_for_changes_async, create_reason_pdf
            pdf_generation = create_pdf_for_changes(full_diff) # file_name

            attachments = f'exports/{pdf_generation}'
            
            reason_md = await generate_reason_for_changes_async(full_diff)
            reason_pdf = create_reason_pdf(reason_md)
            attachments = attachments + f",exports/{reason_pdf}"

            vuln_updates = final_state.get("vuln_updates", [])
            vuln_count = len(vuln_updates)
            excel_link = update_metadata_excel(vuln_updates)
            if excel_link:
                attachments = attachments + f",exports/{excel_link}"

        except Exception as e:
            print(e)

    url = get_url_location(location=temp_directory_location)

    normalized_path = os.path.normpath(full_directory_location)

    folder_name = os.path.basename(normalized_path)

    spring_fix_result = SpringFixResult(code_repo_location=url, project_name=folder_name,
                                        attachments=attachments, iteration_count=iteration_count, vuln_count=vuln_count,
                                        compile_status=compile_status, project_id=project_id)

    from app.workers.kafka_consumers import send_email
    await send_email(event=spring_fix_result)

    # Save Token Analysis and Execution History
    token_usage = final_state.get("token_usage", [])
    logger.info(f"DEBUG OUTSIDE: final_state token_usage is {token_usage}")
    
    from app.db_configs.db_configuration import SessionLocal
    from app.db_configs.models import TokenAnalysis, GitRepos, ExecutionHistory
    from datetime import datetime

    db = SessionLocal()
    try:
        git_repo = db.query(GitRepos).filter(GitRepos.git_directory_location == full_directory_location).first()
        if git_repo:
            now = datetime.utcnow()
            
            # Save Execution History
            exec_hist = ExecutionHistory(
                project_id=git_repo.id,
                project_name=git_repo.project_name,
                executed_datetime=now,
                result=compile_status
            )
            db.add(exec_hist)
            
            # Save Tokens
            if token_usage:
                for usage in token_usage:
                    ta = TokenAnalysis(
                        project_id=git_repo.id,
                        input_tokens=usage["input_tokens"],
                        output_tokens=usage["output_tokens"],
                        model_name=usage["model_name"],
                        created_at=now
                    )
                    db.add(ta)
            
            db.commit()
    except Exception as e:
        logger.error(f"Failed to save to db: {e}")
        db.rollback()
    finally:
        db.close()
        
    cwd_dict[full_directory_location] = build_args
    return compile_status

def extract_diff_summary(full_diff: str) -> list:
    summary = []
    current_file = None
    added = 0
    removed = 0
    for line in full_diff.splitlines():
        if line.startswith("+++ b/") or line.startswith("+++ "):
            if current_file:
                summary.append({"file": current_file, "added": added, "removed": removed})
            current_file = line[4:].lstrip("b/") if line.startswith("+++ b/") else line[4:]
            if current_file == "/dev/null":
                current_file = None
            added = 0
            removed = 0
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    if current_file:
        summary.append({"file": current_file, "added": added, "removed": removed})
    return summary
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import os
from sqlalchemy.orm import Session

from app.dtos.request_dtos import GitRepoDTO
from app.dtos.response_dtos import ResponseDTO
from app.main import get_db
from app.repository.git_repo_repository import GitRepoRepository
from app.services.admin.git_repo_services import archival_and_download_file
from app.services.admin.spring_fix_services import SpringFix
from app.process.git_utils import extract_project_name

router = APIRouter(prefix="/git",tags=["git"])

def get_spring_fix_service(db : Session = Depends(get_db)) -> SpringFix:
    repo = GitRepoRepository(db=db)
    return SpringFix(repo=repo)

@router.post("/add-project", response_model=ResponseDTO, response_model_exclude_none=True)
async def add_git_projects(repo_details:GitRepoDTO,spring_fix : SpringFix = Depends(get_spring_fix_service)):
    return await spring_fix.add_new_repo(repo_dto=repo_details)

@router.get("/get-project", response_model=ResponseDTO)
async def get_git_project(project_id : int, spring_fix : SpringFix = Depends(get_spring_fix_service)):
    return await spring_fix.get_project_details(project_id=project_id)

@router.get("/get-all-projects", response_model=ResponseDTO)
async def get_all_projects(spring_fix : SpringFix = Depends(get_spring_fix_service)):
    return await spring_fix.get_all_projects()

@router.get("/get-all-schedules")
async def get_all_schedules(spring_fix : SpringFix = Depends(get_spring_fix_service)):
    return await spring_fix.get_all_schedules()

@router.delete("/delete-project/{project_id}", response_model=ResponseDTO)
async def delete_project(project_id: int, spring_fix: SpringFix = Depends(get_spring_fix_service)):
    return await spring_fix.delete_project(project_id=project_id)

@router.get("/download-project/{folder_location:path}")
async def download_project(folder_location: str):
    return await archival_and_download_file(location=folder_location)

@router.post("/refresh-schedule/{project_id}")
async def refresh_schedule(project_id: int, db: Session = Depends(get_db)):
    from app.db_configs.models import ProjectSchedules
    from app.schedulers.project_scheduler import add_job_to_scheduler
    schedule = db.query(ProjectSchedules).filter(ProjectSchedules.project_id == project_id).first()
    if schedule:
        add_job_to_scheduler(schedule)
    return {"status": "ok"}

@router.get("/stream/{project_id}")
async def stream_project_pipeline(project_id: int, db: Session = Depends(get_db)):
    repo = GitRepoRepository(db=db)
    git_repo = await repo.find_by_id(project_id)
    if not git_repo:
        raise HTTPException(status_code=404, detail="Project not found")


    project_dir = os.path.dirname(git_repo.git_directory_location)
    extracted_project_name = extract_project_name(git_repo.git_directory_location)
    temp_directory_location = project_dir+f"/{extracted_project_name}"+"_work_folder"
    log_file_path = os.path.join(temp_directory_location, "pipeline_stream.log")

    async def event_generator():
        last_pos = 0
        while True:
            if not os.path.exists(log_file_path):
                await asyncio.sleep(0.5)
                continue
            
            with open(log_file_path, "r") as f:
                f.seek(last_pos)
                lines = f.readlines()
                last_pos = f.tell()

            for line in lines:
                yield line
                if "success" in line or "abort" in line or "escalate" in line:
                    if '\"type\": \"trace\"' in line and ('\"id\": \"success\"' in line or '\"id\": \"abort\"' in line or '\"id\": \"escalate\"' in line):
                        return
            
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

from sqlalchemy import func
from app.db_configs.models import TokenAnalysis

@router.get("/token-analysis/total")
async def get_total_token_analysis(db: Session = Depends(get_db)):
    results = db.query(
        TokenAnalysis.model_name,
        func.sum(TokenAnalysis.input_tokens).label("input_tokens"),
        func.sum(TokenAnalysis.output_tokens).label("output_tokens")
    ).group_by(TokenAnalysis.model_name).all()

    data = []
    for r in results:
        data.append({
            "model_name": r.model_name,
            "input_tokens": r.input_tokens or 0,
            "output_tokens": r.output_tokens or 0,
            "total_tokens": (r.input_tokens or 0) + (r.output_tokens or 0)
        })
    return {"data": data}

@router.get("/token-analysis/{project_id}")
async def get_project_token_analysis(project_id: int, db: Session = Depends(get_db)):
    results = db.query(
        TokenAnalysis.model_name,
        func.sum(TokenAnalysis.input_tokens).label("input_tokens"),
        func.sum(TokenAnalysis.output_tokens).label("output_tokens")
    ).filter(TokenAnalysis.project_id == project_id).group_by(TokenAnalysis.model_name).all()

    data = []
    for r in results:
        data.append({
            "model_name": r.model_name,
            "input_tokens": r.input_tokens or 0,
            "output_tokens": r.output_tokens or 0,
            "total_tokens": (r.input_tokens or 0) + (r.output_tokens or 0)
        })
    return {"data": data}

from fastapi.responses import HTMLResponse

html_template = """
<html>
<head>
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #020617; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: rgba(15,23,42,0.8); padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.4); }}
        .success {{ color: #10b981; font-size: 48px; margin-bottom: 16px; }}
        .error {{ color: #ef4444; font-size: 48px; margin-bottom: 16px; }}
        h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
        p {{ color: #94a3b8; margin: 0 0 24px 0; font-size: 16px; }}
        button {{ background: rgba(255,255,255,0.1); border: none; color: white; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: background 0.2s; }}
        button:hover {{ background: rgba(255,255,255,0.2); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="{icon_class}">&#10003;</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <button onclick="window.close()">Close Window</button>
    </div>
</body>
</html>
"""

@router.get("/approve/{request_id}")
async def approve_fix_request(request_id: int, spring_fix: SpringFix = Depends(get_spring_fix_service)):
    res = await spring_fix.approve_fix(request_id)
    if res.status_code == 200:
        content = html_template.format(icon_class="success", title="Successfully Approved", message="The fix has been merged and pushed to Git.")
    else:
        content = html_template.format(icon_class="error", title="Action Failed", message=res.message)
    return HTMLResponse(content=content)

@router.get("/reject/{request_id}")
async def reject_fix_request(request_id: int, spring_fix: SpringFix = Depends(get_spring_fix_service)):
    res = await spring_fix.reject_fix(request_id)
    if res.status_code == 200:
        content = html_template.format(icon_class="success", title="Successfully Rejected", message="The fix has been rejected and temporary files cleaned up.")
    else:
        content = html_template.format(icon_class="error", title="Action Failed", message=res.message)
    return HTMLResponse(content=content)

@router.get("/fix-requests")
async def get_all_fix_requests(spring_fix: SpringFix = Depends(get_spring_fix_service)):
    return await spring_fix.get_all_fix_requests()
@router.get("/get-execution-history")
async def get_execution_history(db: Session = Depends(get_db)):
    from app.db_configs.models import ExecutionHistory
    records = db.query(ExecutionHistory).order_by(ExecutionHistory.executed_datetime.desc()).all()
    return {"data": records}

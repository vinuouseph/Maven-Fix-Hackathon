import logging
import os
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db_configs.db_configuration import SessionLocal
from app.db_configs.models import GitRepos, ProjectSchedules
from app.process.git_utils import extract_project_name, pull_via_git
from app.schedulers.git_puller import update_cwd_list_run_pipeline
import asyncio
import uuid
import shutil
from datetime import datetime
from app.core.config import settings
from app.workers.models import SpringFixKafka
from app.workers.kafka_producers import produce_spring_fix_event

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def run_scheduled_job(project_id: int):
    """
    Triggered by APScheduler. Pulls from git and runs the pipeline if there are changes.
    """
    db = SessionLocal()
    try:
        git_repo = db.query(GitRepos).filter(GitRepos.id == project_id).first()
        if not git_repo:
            logger.error(f"Project {project_id} not found. Removing job.")
            scheduler.remove_job(str(project_id))
            return
            
        wd = git_repo.git_directory_location
        
        if not os.path.exists(wd):
            logger.error(f"Directory {wd} not found for project {project_id}.")
            return
            
        project_name = extract_project_name(wd)
        logger.info(f"Cron triggered: pulling from git for project {project_name}....")
        
        pull_result = pull_via_git(wd=wd)
        
        if 'already up to date' in pull_result.lower():
            logger.info(f"{project_name} is already upto date")
            
            # Log execution history
            from app.db_configs.models import ExecutionHistory
            from datetime import datetime
            now = datetime.utcnow()
            exec_hist = ExecutionHistory(
                project_id=git_repo.id,
                project_name=git_repo.project_name,
                executed_datetime=now,
                result="NO_CHANGES"
            )
            db.add(exec_hist)
            db.commit()
            
            # Send email
            from app.workers.models import SpringFixKafka
            from app.workers.kafka_producers import produce_spring_fix_event
            
            # We send a special kafka event that bypasses the pipeline and just sends an email
            spring_fix_kafka = SpringFixKafka(
                full_directory_location=wd,
                temp_directory_location=wd,
                build_args=git_repo.build_args,
                is_initial_run=False,
                project_id=git_repo.id,
                schedule_type="up_to_date", # Use this as a flag to bypass pipeline
            )
            await produce_spring_fix_event(spring_fix_kafka=spring_fix_kafka)
            
            return
        else:
            logger.info(f"Changes found for {project_name}: {pull_result}")
            
            # Since there are changes, we need to create a new temp folder and run the pipeline
            git_repo_directory = settings.git_repo_directory
            extracted_project_name = git_repo.git_repo_url.split("/")[-1].split(".")[0]
            project_dir = (
                f"{git_repo_directory}/"
                f"{datetime.now().strftime('%Y%m%d')}_"
                f"{extracted_project_name}_"
                f"{uuid.uuid4().hex}"
            )
            os.makedirs(project_dir, exist_ok=True)
            
            # We copy the already updated `wd` into the new temp folder. Wait, or we can just clone again.
            # Copying `wd` is faster.
            full_directory_location = project_dir + f"/{extracted_project_name}"
            temp_directory_location = project_dir + f"/{extracted_project_name}_work_folder"
            
            shutil.copytree(wd, full_directory_location)
            shutil.copytree(full_directory_location, temp_directory_location)
            
            # Send the kafka event just like we do when adding a project, so it processes asynchronously
            spring_fix_kafka = SpringFixKafka(
                full_directory_location=full_directory_location, 
                temp_directory_location=temp_directory_location, 
                build_args=git_repo.build_args
            )
            await produce_spring_fix_event(spring_fix_kafka=spring_fix_kafka)
            
    except Exception as e:
        logger.exception(f"Error in scheduled job for project {project_id}: {e}")
    finally:
        db.close()


def load_schedules_on_startup():
    db = SessionLocal()
    try:
        schedules = db.query(ProjectSchedules).all()
        for schedule in schedules:
            add_job_to_scheduler(schedule)
    finally:
        db.close()

def add_job_to_scheduler(schedule: ProjectSchedules):
    job_id = str(schedule.project_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    try:
        kwargs = json.loads(schedule.schedule_config)
    except Exception:
        kwargs = {}
        
    scheduler.add_job(
        run_scheduled_job,
        trigger=schedule.schedule_type,
        args=[schedule.project_id],
        id=job_id,
        **kwargs
    )
    logger.info(f"Added APScheduler job {job_id} with type {schedule.schedule_type} and config {kwargs}")

def remove_job_from_scheduler(project_id: int):
    job_id = str(project_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed APScheduler job {job_id}")

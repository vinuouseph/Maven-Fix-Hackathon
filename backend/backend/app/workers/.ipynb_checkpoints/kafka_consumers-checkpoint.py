import logging
from pathlib import Path

# Removed BackgroundTasks, Form
from fastapi import File, UploadFile
from fastapi_mail import ConnectionConfig, MessageSchema, MessageType, FastMail
from app.db_configs.db_configuration import SessionLocal
from app.db_configs.models import GitRepos, FixRequests
from typing import List, Optional
from faststream import FastStream, AckPolicy
from faststream.kafka import KafkaBroker, KafkaMessage
from pydantic.v1 import EmailStr

from app.core.config import settings
from app.schedulers.git_puller import update_cwd_list_run_pipeline
from app.services.admin.git_repo_services import archival_and_download_file
from app.workers.models import SpringFixKafka, SpringFixResult
from app.db_configs.db_configuration import SessionLocal
from app.repository.git_repo_repository import GitRepoRepository

broker = KafkaBroker(settings.kafka_bootstrap_servers)
app = FastStream(broker)

@broker.subscriber(
    "spring_fix",
    group_id="analytics_service_group",
    ack_policy=AckPolicy.MANUAL,
)
async def process_user_event(
    msg: KafkaMessage,
) -> None:
    try:
        raw = msg.body.decode("utf-8")
        event = SpringFixKafka.model_validate_json(raw)
        
        if event.schedule_type == "up_to_date":
            # Bypass pipeline entirely
            compile_status = "up_to_date"
            from app.workers.models import SpringFixResult
            import os
            from app.process.git_utils import extract_project_name
            project_name = extract_project_name(event.full_directory_location)
            # Use get_url_location for the relative URL if needed
            from app.services.admin.git_repo_services import get_url_location
            url = get_url_location(event.full_directory_location)
            dummy_result = SpringFixResult(
                code_repo_location=url,
                project_name=project_name,
                attachments="",
                iteration_count=0,
                vuln_count=0,
                compile_status="up_to_date",
                project_id=event.project_id
            )
            await send_email(dummy_result)
        else:
            compile_status = await update_cwd_list_run_pipeline(full_directory_location=event.full_directory_location, temp_directory_location=event.temp_directory_location, build_args=event.build_args, project_id=event.project_id)

        if event.is_initial_run and event.project_id:
            db = SessionLocal()
            try:
                git_repo = db.query(GitRepos).filter(GitRepos.id == event.project_id).first()
                if git_repo:
                    if compile_status == "pre_compile_failed":
                        git_repo.status = 3
                        logging.info(f"Pre-compile failed during initial run. Status set to 3 for project {git_repo.project_name}")
                    else:
                        git_repo.status = 1
                        logging.info(f"Pipeline finished during initial run. Status set to 1 for project {git_repo.project_name}")
                    
                    db.commit()

                    if event.schedule_type and event.schedule_config:
                        from app.db_configs.models import ProjectSchedules
                        project_schedule = ProjectSchedules(
                            project_id=git_repo.id,
                            schedule_type=event.schedule_type,
                            schedule_config=event.schedule_config
                        )
                        db.add(project_schedule)
                        db.commit()
                        db.refresh(project_schedule)
                        
                        # Notify the Uvicorn backend to update its APScheduler memory
                        import httpx
                        try:
                            async with httpx.AsyncClient() as client:
                                await client.post(f"http://localhost:8000/git/refresh-schedule/{git_repo.id}")
                            logging.info(f"Notified Uvicorn to schedule job for project {git_repo.project_name}")
                        except Exception as ex:
                            logging.error(f"Failed to notify Uvicorn to schedule job: {ex}")
            finally:
                db.close()

        await msg.ack()

    except Exception as e:
        logging.error(f"Failed to process: {e}", exc_info=True)
        await msg.ack()


@broker.subscriber(
    "spring_fix_result",
    group_id="analytics_service_group",
    ack_policy=AckPolicy.MANUAL,
)
async def process_user_event(
    msg: KafkaMessage,
) -> None:
    try:
        raw = msg.body.decode("utf-8")
        event = SpringFixResult.model_validate_json(raw)

        template_data = {
            "number": '1',
            "project_name": 'project_1',
            "number_of_loops": '2',
            "download_link":f'http://localhost:8000/git/download-projet/{event.code_repo_location}',
        }

        await send_advanced_email(
            email_to="legionsmpower@gmail.com",
            subject="Action Required: Baseline Compile Failure",
            recipient_name="Admin",
            custom_message="This is a simulated execution.",
            template_data=template_data
        )
    except Exception as e:
        logging.error(f"Failed to process: {e}", exc_info=True)
        await msg.ack()


TEMPLATE_FOLDER = settings.template_folder

conf = ConnectionConfig(
    MAIL_USERNAME="naseedrahman@gmail.com",
    MAIL_PASSWORD="yniuuahwarhbduuf",
    MAIL_FROM="naseedrahman@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)

async def file_to_uploadfile(file_path: str) -> UploadFile:
    path = Path(file_path)
    return UploadFile(filename=path.name, file=open(path, "rb"))

async def send_email(event: SpringFixResult) -> None:
    # event.code_repo_location already ends with '_work_folder' (e.g. 'parent/project_work_folder')
    # So temp_dir is exactly that, and git_dir is without '_work_folder'
    temp_dir = f'{settings.git_repo_directory}/{event.code_repo_location}'
    if event.code_repo_location.endswith('_work_folder'):
        main_repo_loc = event.code_repo_location[:-len('_work_folder')]
    else:
        main_repo_loc = event.code_repo_location
    git_dir = f'{settings.git_repo_directory}/{main_repo_loc}'

    db = SessionLocal()
    try:
        project_id = event.project_id
        project_name = event.project_name
        
        # Fallback for older events without project_id
        if not project_id:
            repo = db.query(GitRepos).filter(GitRepos.git_directory_location == git_dir).first()
            project_id = repo.id if repo else 0
            project_name = repo.project_name if repo else (event.project_name or "Unknown")

        fix_req = FixRequests(
            project_id=project_id,
            project_name=project_name,
            status="PENDING",
            git_directory_location=git_dir,
            temp_directory_location=temp_dir
        )
        db.add(fix_req)
        db.commit()
        db.refresh(fix_req)
        request_id = fix_req.id
    except Exception as e:
        logging.error(f"Failed to create FixRequest: {e}")
        db.rollback()
        request_id = 0
    finally:
        db.close()

    base_url = f"http://{settings.app_host}:{settings.app_port}"
    approval_url = f"{base_url}/git/approve/{request_id}"
    rejection_url = f"{base_url}/git/reject/{request_id}"
    download_url = f"{base_url}/git/download-project/{event.code_repo_location}"

    template_data = {
        "number": event.vuln_count,
        "project_name": event.project_name,
        "number_of_loops": event.iteration_count,
        "approval_url": approval_url,
        "rejection_url": rejection_url,
        "download_url": download_url,
    }

    # Determine template and subject based on compile_status
    status = event.compile_status
    vuln_count = event.vuln_count or 0

    attachments = []
    if vuln_count > 0:
        attachments.append(f'{temp_dir}/pom.xml')

    if event.attachments:
        additional_files = [f.strip() for f in event.attachments.split(",") if f.strip()]
        attachments.extend(additional_files)

    if status == "pre_compile_failed":
        template_name = "initial_compile_error.html"
        subject = f"Action Required: Pre-existing Compile Error in {event.project_name}"
    elif status == "up_to_date":
        template_name = "clean_pom.html"
        subject = f"Scan Complete: Project already up to date for {event.project_name}"
    elif status == "success" and vuln_count == 0:
        template_name = "clean_pom.html"
        subject = f"Scan Complete: No Vulnerabilities Found in {event.project_name}"
    elif status == "success" and vuln_count > 0:
        template_name = "remediation_success.html"
        subject = f"Remediation Successful: Please review {event.project_name}"
    elif status == "abort":
        template_name = "max_iterations_reached.html"
        subject = f"Action Required: Max Iterations Reached for {event.project_name}"
    elif status == "escalate":
        template_name = "agent_escalation.html"
        subject = f"Action Required: Agent Escalation for {event.project_name}"
    else:
        template_name = "max_iterations_reached.html"
        subject = f"Action Required: Pipeline Finished for {event.project_name}"

    await send_advanced_email(
        email_to=settings.email_to,
        subject=subject,
        template_data=template_data,
        attachments=attachments,
        template_name=template_name
    )


async def send_advanced_email(
        email_to: EmailStr,
        subject: str,
        template_data:dict,
        attachments: Optional[list[str]] = None,
        template_name: str = "remediation_success.html"
):
    upload_files = []
    if attachments:
        for path in attachments:
            upload_files.append(await file_to_uploadfile(path))

    message_args = {
        "subject": subject,
        "recipients": [email_to],
        "template_body": template_data,
        "subtype": MessageType.html,
    }
    
    if upload_files:
        message_args["attachments"] = upload_files

    message = MessageSchema(**message_args)

    fm = FastMail(conf)

    try:
        await fm.send_message(message, template_name=template_name)
        print("Mail actually sent to SMTP server successfully")
    except Exception as e:
        # Better error logging to catch SMTP issues
        logging.error(f"Failed to send email: {e}")

    return {
        "message": "Email processed."
    }
import shutil
from datetime import datetime
import uuid
from app.core.config import settings
from app.db_configs.models import GitRepos, FixRequests, ProjectSchedules
import logging
import os
import subprocess
from app.dtos.request_dtos import GitRepoDTO
from app.dtos.response_dtos import ResponseDTO, ProjectDetailsDTO
from app.exception.spring_fix_exceptions import SpringFixException
from app.process.git_utils import is_valid_git_repo, clone_project_from_git
from app.repository.git_repo_repository import GitRepoRepository
from app.schedulers.git_puller import cwd_dict, update_cwd_list_run_pipeline
from app.schedulers.project_scheduler import add_job_to_scheduler, remove_job_from_scheduler
from app.workers.kafka_producers import produce_spring_fix_event
from app.workers.models import SpringFixKafka
from app.process.code_compiler_tools import compile_spring_boot

logger = logging.getLogger(__name__)

class SpringFix:

    def __init__(self, repo:GitRepoRepository):
        self.repo = repo

    async def add_new_repo(self, repo_dto:GitRepoDTO):

        """
            Adds a new Git repository to the database.

            Args:
                repo_dto (GitRepoDTO): DTO containing repository details.

            Returns:
                ResponseDTO: Result of the operation.

            Raises:
                SpringFixException: If there is an internal server error.

            """

        # git_repos = GitRepos(**repo_dto.model_dump()) 
        # wait, repo_dto has schedule_config which is not in GitRepos table directly.
        git_repos = GitRepos(
            project_name=repo_dto.project_name,
            project_description=repo_dto.project_description,
            project_type=repo_dto.project_type,
            git_repo_url=repo_dto.git_repo_url,
            build_args=repo_dto.build_args,
            status=0
        )
        try:
            if not await is_valid_git_repo(git_repos.git_repo_url):
                raise SpringFixException(f"Invalid Git Url : {git_repos.git_repo_url}")

            if await self.repo.is_git_repo_already_exist(git_repos.git_repo_url):
                raise SpringFixException(f"Project with git url {git_repos.git_repo_url} already exists", status_code=400)

            git_repo_directory = settings.git_repo_directory

            extracted_project_name = git_repos.git_repo_url.split("/")[-1].split(".")[0]
            project_dir = (
                f"{git_repo_directory}/"
                f"{datetime.now().strftime('%Y%m%d')}_"
                f"{extracted_project_name}_"
                f"{uuid.uuid4().hex}"
            )

            os.makedirs(project_dir, exist_ok=True)

            await clone_project_from_git(repo_url=git_repos.git_repo_url, cwd=project_dir)

            full_directory_location = project_dir+f"/{extracted_project_name}"
            
            git_repos.git_directory_location = full_directory_location

            git_repos.status = 0
            git_repos = await self.repo.create_git_repo(git_repo=git_repos)
            logger.info(f"Added the project with id {git_repos.id} to db with status PENDING")

            temp_directory_location = project_dir+f"/{extracted_project_name}_work_folder"
            shutil.copytree(full_directory_location, temp_directory_location)

            from app.workers.models import SpringFixKafka
            from app.workers.kafka_producers import produce_spring_fix_event
            
            spring_fix_kafka = SpringFixKafka(
                full_directory_location=full_directory_location,
                temp_directory_location=temp_directory_location,
                build_args=git_repos.build_args,
                is_initial_run=True,
                project_id=git_repos.id,
                schedule_type=repo_dto.schedule_type,
                schedule_config=repo_dto.schedule_config
            )
            await produce_spring_fix_event(spring_fix_kafka=spring_fix_kafka)

            return ResponseDTO(message="Project added and pipeline started asynchronously", status_code=201)

        except SpringFixException:
            raise

        except Exception as e:
            logger.exception(f"Internal Server Error : {e}")
            raise SpringFixException(message="Internal server error, contact admin", status_code=500)


    async def get_project_details(self, project_id : int):
        """
            Gets Project details from the database

            Args:
                project_id (int)

            Returns:
                ResponseDTO: Result of the operation.

            Raises:
                SpringFixException: If there is an internal server error.

            """

        if project_id is None or project_id<=0:
            raise SpringFixException(message="Invalid Project ID", status_code=400)

        try:
            git_repo: GitRepos = await self.repo.find_by_id(project_id=project_id)

            if git_repo is not None:
                project_details: ProjectDetailsDTO = ProjectDetailsDTO(project_id=git_repo.id,
                                                                       project_name=git_repo.project_name,
                                                                       project_description=git_repo.project_description,
                                                                       project_type=git_repo.project_type,
                                                                       git_repo_url=git_repo.git_repo_url,
                                                                       status=git_repo.status)

                logger.info(f"Projects fetched successfully for project id : {project_id}")
                return ResponseDTO(message="Projects fetched successfully...", status_code=200, project_details=project_details)
            else:
                logger.error(f"Projects not found for id : {project_id}")
                raise SpringFixException(message=f"Projects not found for id : {project_id}",status_code=404)

        except SpringFixException:
            raise

        except Exception as e:
            logger.exception(f"Internal Server Error : {e}")
            raise SpringFixException(message=f"Internal Server Error : {e}", status_code=500)


    async def get_all_projects(self):
        """
        Returns all projects stored in the database.

        Returns:
            ResponseDTO: A response containing the list of all projects.

        Raises:
            SpringFixException: If there is an internal server error.
        """
        try:
            git_repos: list = await self.repo.find_all()
            projects = [
                ProjectDetailsDTO(
                    project_id=repo.id,
                    project_name=repo.project_name,
                    project_description=repo.project_description,
                    project_type=repo.project_type,
                    git_repo_url=repo.git_repo_url,
                    status=repo.status,
                )
                for repo in git_repos
            ]
            logger.info(f"Fetched all {len(projects)} projects")
            return ResponseDTO(message="Projects fetched successfully", status_code=200, projects=projects)

        except Exception as e:
            logger.exception(f"Internal Server Error : {e}")
            raise SpringFixException(message="Internal server error, contact admin", status_code=500)


    async def get_all_schedules(self):
        """
        Returns all project schedules stored in the database.
        """
        try:
            schedules = self.repo.db.query(ProjectSchedules).all()
            result = []
            for s in schedules:
                project = await self.repo.find_by_id(s.project_id)
                result.append({
                    "id": s.id,
                    "project_id": s.project_id,
                    "project_name": project.project_name if project else "Unknown",
                    "schedule_type": s.schedule_type,
                    "schedule_config": s.schedule_config
                })
            return {"schedules": result}
        except Exception as e:
            logger.exception(f"Internal Server Error : {e}")
            raise SpringFixException(message="Internal server error, contact admin", status_code=500)

    async def delete_project(self, project_id: int):
        """
        Deletes a project from the database and removes its directory.

        Args:
            project_id (int): The ID of the project to delete.

        Returns:
            ResponseDTO: Result of the operation.

        Raises:
            SpringFixException: If there is an internal server error or project not found.
        """
        if project_id is None or project_id <= 0:
            raise SpringFixException(message="Invalid Project ID", status_code=400)

        try:
            git_repo: GitRepos = await self.repo.find_by_id(project_id=project_id)

            if git_repo is None:
                raise SpringFixException(message=f"Project not found with id : {project_id}", status_code=404)

            # Attempt to delete the directory from the file system
            if git_repo.git_directory_location and os.path.exists(git_repo.git_directory_location):
                parent_dir = os.path.dirname(git_repo.git_directory_location)
                try:
                    shutil.rmtree(parent_dir)
                    logger.info(f"Deleted directory: {parent_dir}")
                except Exception as e:
                    logger.warning(f"Failed to delete directory {parent_dir}: {e}")
            else:
                logger.warning(f"Directory not found for deletion: {git_repo.git_directory_location}")

            # Delete the repo from the database
            await self.repo.delete_by_id(project_id=project_id)
            
            # Remove scheduled job
            remove_job_from_scheduler(project_id)
            
            # Also remove the project schedules record if needed
            db = self.repo.db
            schedules = db.query(ProjectSchedules).filter(ProjectSchedules.project_id == project_id).all()
            for sched in schedules:
                db.delete(sched)
            db.commit()

            logger.info(f"Project deleted successfully for id : {project_id}")
            return ResponseDTO(message="Project deleted successfully", status_code=200)

        except SpringFixException:
            raise

        except Exception as e:
            logger.exception(f"Internal Server Error during deletion : {e}")
            raise SpringFixException(message=f"Internal Server Error : {e}", status_code=500)

    async def approve_fix(self, request_id: int):
        fix_req: FixRequests = self.repo.db.query(FixRequests).filter(FixRequests.id == request_id).first()
        if not fix_req:
            raise SpringFixException(message="Fix request not found", status_code=404)
        
        if fix_req.status != "PENDING":
            return ResponseDTO(message=f"Request is already processed ({fix_req.status})", status_code=400)

        # Copy temp folder src and pom to git_directory_location
        # Then push to git
        try:
            main_dir = fix_req.git_directory_location
            temp_dir = fix_req.temp_directory_location

            for item in ["src", "pom.xml", "build.gradle", "build.gradle.kts"]:
                src_item = os.path.join(temp_dir, item)
                dest_item = os.path.join(main_dir, item)
                if os.path.exists(src_item):
                    if os.path.isdir(src_item):
                        if os.path.exists(dest_item):
                            shutil.rmtree(dest_item)
                        shutil.copytree(src_item, dest_item)
                    else:
                        shutil.copy2(src_item, dest_item)

            # Git commands
            subprocess.run(["git", "add", "."], cwd=main_dir, check=True)
            subprocess.run(["git", "commit", "-m", "AI Auto-Fix: Dependency and compilation fixes"], cwd=main_dir, check=False)
            subprocess.run(["git", "push"], cwd=main_dir, check=False)

            fix_req.status = "APPROVED"
            self.repo.db.commit()
            
            # Clean up temp dir
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info(f"Approved fix request {request_id}")
            return ResponseDTO(message="Fix approved and pushed successfully.", status_code=200)

        except Exception as e:
            logger.exception(f"Error approving fix: {e}")
            raise SpringFixException(message=f"Error approving fix: {e}", status_code=500)

    async def reject_fix(self, request_id: int):
        fix_req: FixRequests = self.repo.db.query(FixRequests).filter(FixRequests.id == request_id).first()
        if not fix_req:
            raise SpringFixException(message="Fix request not found", status_code=404)
        
        if fix_req.status != "PENDING":
            return ResponseDTO(message=f"Request is already processed ({fix_req.status})", status_code=400)

        try:
            fix_req.status = "REJECTED"
            self.repo.db.commit()

            temp_dir = fix_req.temp_directory_location
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info(f"Rejected fix request {request_id}")
            return ResponseDTO(message="Fix rejected and temp files cleaned up.", status_code=200)

        except Exception as e:
            logger.exception(f"Error rejecting fix: {e}")
            raise SpringFixException(message=f"Error rejecting fix: {e}", status_code=500)

    async def get_all_fix_requests(self):
        try:
            requests = self.repo.db.query(FixRequests).order_by(FixRequests.created_at.desc()).all()
            result = []
            for r in requests:
                result.append({
                    "id": r.id,
                    "project_id": r.project_id,
                    "project_name": r.project_name,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })
            return {"data": result}
        except Exception as e:
            logger.exception(f"Error getting fix requests: {e}")
            raise SpringFixException(message=f"Error getting fix requests: {e}", status_code=500)

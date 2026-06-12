import subprocess
import logging

from app.exception.spring_fix_exceptions import SpringFixException

logger = logging.getLogger(__name__)

async def is_valid_git_repo(repo_url):
    try:
        result = subprocess.run(
            ["git", "ls-remote", repo_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

def extract_project_name(dir : str):
    extracted_name = dir.split("/")[-1].split("\\")[-1]
    return extracted_name

async def clone_project_from_git(repo_url:str, cwd:str):
    try:
        subprocess.run(
            ["git", "clone", repo_url],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        logger.info("Project Cloned Successfully!...")
    except Exception as e:
        logger.error(f"Error occurred while cloning the repo {repo_url} : {e}")
        raise SpringFixException(f"Error occurred while cloning the repo {repo_url} : {e}", status_code=500)

def pull_via_git(wd:str) -> str:
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=wd,
            capture_output=True,
            text=True,
            check=True
        )
        pull_result = str(result.stdout)
        return pull_result

    except Exception as e:
        logger.error(f"Error occurred while pulling the repo from : {wd}")
        return None
from typing import Optional

from pydantic import BaseModel, Field
from enum import Enum

class ProjectType(str, Enum):
    MAVEN = "maven"
    GRADLE = "gradle"


class GitRepoDTO(BaseModel):
    project_name : str = Field(..., min_length=1, max_length=20 , description="Name of the project")
    project_description : Optional[str] = Field(None, max_length=100, description="Description for the project")
    project_type : ProjectType = Field(..., min_length=1, max_length=50, description="Type of the project ( Maven, Gradle, ...)")
    git_repo_url : str = Field(..., min_length=1, max_length=200, description="Git repository URL" )
    build_args : Optional[str] = Field(None, max_length=500, description="Extra build arguments")
    schedule_type: Optional[str] = Field(None, description="Type of schedule (e.g. cron, interval)")
    schedule_config: Optional[str] = Field(None, description="JSON string of schedule kwargs")
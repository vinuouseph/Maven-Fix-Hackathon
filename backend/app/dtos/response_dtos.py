from typing import Optional

from pydantic import BaseModel

class ProjectDetailsDTO(BaseModel):
    project_id : int
    project_name : str
    project_description : Optional[str]
    project_type : str
    git_repo_url : str
    status : Optional[int] = None

class ResponseDTO(BaseModel):
    message : Optional[str] = None
    status_code : Optional[int] = None
    project_details : Optional[ProjectDetailsDTO] = None
    projects : Optional[list[ProjectDetailsDTO]] = None

from typing import Optional

from pydantic import BaseModel


class SpringFixKafka(BaseModel):
    full_directory_location : str
    temp_directory_location : str
    build_args : Optional[str] = None
    is_initial_run : bool = False
    project_id : Optional[int] = None
    schedule_type : Optional[str] = None
    schedule_config : Optional[str] = None

class SpringFixResult(BaseModel):
    project_name : Optional[str] = None
    is_pom_fixed : Optional[bool] = None
    is_spring_fixed : Optional[bool] = None
    pom_fixes : Optional[str] = None
    spring_fixes : Optional[str] = None
    pom_file : Optional[str] = None
    dependency_report_file : Optional[str] = None
    code_change_report : Optional[str] = None
    code_repo_location : Optional[str] = None
    attachments : Optional[str] = None
    iteration_count : Optional[int] = None
    vuln_count : Optional[int] = None
    compile_status : Optional[str] = None
    project_id : Optional[int] = None

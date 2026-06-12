from sqlalchemy import Column, String, Integer

from app.db_configs.db_configuration import Base

class GitRepos(Base):
    __tablename__ = "git_repos"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(20), nullable=False)
    project_description = Column(String(100), nullable=True)
    project_type = Column(String(50), nullable=False)
    git_repo_url = Column(String(200), nullable=False)
    git_directory_location = Column(String(200), nullable=False)
    status = Column(Integer, nullable=False)
    build_args = Column(String(500), nullable=True)

class ProjectSchedules(Base):
    __tablename__ = "project_schedules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False) # Maps to GitRepos id
    schedule_type = Column(String(50), nullable=False) # e.g. "cron", "interval", "daily"
    schedule_config = Column(String(500), nullable=False) # JSON string with schedule kwargs


from sqlalchemy import DateTime
from sqlalchemy.sql import func

class TokenAnalysis(Base):
    __tablename__ = "token_analysis"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    model_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)

class FixRequests(Base):
    __tablename__ = "fix_requests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    project_name = Column(String(200), nullable=False)
    status = Column(String(20), default="PENDING")
    git_directory_location = Column(String(500), nullable=False)
    temp_directory_location = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

class ExecutionHistory(Base):
    __tablename__ = "execution_history"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    project_name = Column(String(200), nullable=False)
    executed_datetime = Column(DateTime, nullable=False, default=func.now())
    result = Column(String(50), nullable=False)
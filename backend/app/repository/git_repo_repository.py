from sqlalchemy.orm import Session

from app.db_configs.models import GitRepos


class GitRepoRepository:
    def __init__(self, db:Session):
        self.db = db

    async def create_git_repo(self, git_repo:GitRepos) -> GitRepos:
        self.db.add(git_repo)
        self.db.commit()
        self.db.refresh(git_repo)

        return git_repo

    async def find_by_id(self, project_id:int):
        return self.db.query(GitRepos).filter(GitRepos.id == project_id).first()

    async def find_by_directory_location(self, directory_location: str):
        return self.db.query(GitRepos).filter(GitRepos.git_directory_location == directory_location).first()

    async def find_all(self) -> list[GitRepos]:
        return self.db.query(GitRepos).order_by(GitRepos.id).all()

    async def delete_by_id(self, project_id: int) -> bool:
        git_repo = await self.find_by_id(project_id)
        if git_repo:
            self.db.delete(git_repo)
            self.db.commit()
            return True
        return False

    async def is_git_repo_already_exist(self, git_repo_url) -> bool:
        git_repo : GitRepos = self.db.query(GitRepos).filter(GitRepos.git_repo_url==git_repo_url).first()

        if git_repo is None:
            return False
        return True
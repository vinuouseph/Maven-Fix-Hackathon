import shutil
import os
from fastapi.responses import FileResponse

from app.core.config import settings


async def archival_and_download_file(location: str):

    repo_dir: str = settings.git_repo_directory
    location = os.path.join(repo_dir, location)

    # 1. Verify the path actually exists before trying to zip it
    if not os.path.isdir(location):
        print(f"Error: The directory '{location}' does not exist.")
        return None

    normalized_path = os.path.normpath(location)

    # 2. Safely extract the folder name
    folder_name = os.path.basename(normalized_path)

    # 3. Define EXACTLY where the zip file should go
    parent_dir = os.path.dirname(normalized_path)

    # This creates the full path: /home/.../parent_dir/2734512-legacy-library-app
    zip_output_path = os.path.join(parent_dir, folder_name)

    # 4. Create the archive
    shutil.make_archive(zip_output_path, "zip", location)
    return FileResponse(
        path=f"{zip_output_path}.zip",
        filename=f"{folder_name}.zip",
        media_type="application/zip"
    )

def get_url_location(location:str):
    normalized_path = os.path.normpath(location)

    # 2. Safely extract the folder name
    folder_name = os.path.basename(normalized_path)

    # 3. Define EXACTLY where the zip file should go
    parent_dir = os.path.dirname(os.path.normpath(location))

    parent_name = os.path.basename(parent_dir)

    return f"{parent_name}/{folder_name}"
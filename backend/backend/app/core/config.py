import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    db_host : str = os.getenv("MYSQL_HOST", "")
    db_user : str = os.getenv("MYSQL_USER", "")
    db_password : str = os.getenv("MYSQL_PASSWORD", "")
    db_port : int = os.getenv("MYSQL_PORT", "")
    db_name : str = os.getenv("MYSQL_DB", "")

    # password hashing
    hash_salt : str = os.getenv("HASH_SALT", "SPRING_FIX_SALT")
    git_repo_directory : str = os.getenv("GIT_REPO_DIRECTORY", "../../Git Repositories")

    llm_provider : str = os.getenv("LLM_PROVIDER","openai")
    coding_chat_model : str = os.getenv("CODING_CHAT_MODEL", "gpt-5.4")
    llm_api_key : str = os.getenv("LLM_API_KEY", "")
    llm_base_url : str = os.getenv("LLM_BASE_URL", "")
    llm_temperature : int = os.getenv("LLM_TEMPERATURE", -10)

    kafka_bootstrap_servers : str = os.getenv("KAFKA_URL", "localhost:9092")
    template_folder : str = os.getenv("TEMPLATE_FOLDER", "")

    email_to : str = os.getenv("EMAIL_RECEIVER", "")

    app_host : str = os.getenv("APP_HOST", "localhost")
    app_port : str = os.getenv("APP_PORT", "8000")

settings = Settings()
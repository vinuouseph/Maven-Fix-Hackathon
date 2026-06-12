from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus

# loading the variable from .env file
load_dotenv()

from app.core.config import settings

db_host = settings.db_host
db_user = settings.db_user
db_password = quote_plus(settings.db_password)
db_port = settings.db_port
db_name = settings.db_name

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

Base = declarative_base()

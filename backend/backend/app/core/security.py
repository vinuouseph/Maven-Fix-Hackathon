import bcrypt
from dotenv import load_dotenv
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

load_dotenv()

SALT = settings.hash_salt

def hash_password(password: str) -> bytes:
    logger.info(f"Password Salt is: {SALT}")
    hashed = bcrypt.hashpw(password.encode('utf-8'), SALT.encode('utf-8'))
    return hashed

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)
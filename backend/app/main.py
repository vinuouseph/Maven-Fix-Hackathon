from aiokafka import AIOKafkaProducer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging, json
from app.core.config import settings
from app.db_configs import models
from app.db_configs.db_configuration import SessionLocal, engine
from app.exception.global_exception_handler import spring_fix_exception_handler
from app.exception.spring_fix_exceptions import SpringFixException
from app.logging.logging_config import setup_logging
from app.logging.logging_config import setup_logging
from app.schedulers.project_scheduler import scheduler, load_schedules_on_startup
from sqlalchemy.orm import Session

from app.workers.kafka_manager import kafka_manager

logger = logging.getLogger(__name__)

# loading the variable from .env file
load_dotenv()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Instantiate the session directly since we are outside a route dependency
    db: Session = SessionLocal()
    load_schedules_on_startup()

    # initializing background schedulers
    scheduler.start()

    # initialize kafka producer
    kafka_manager.producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        acks="all",
        enable_idempotence=True,
    )

    await kafka_manager.producer.start()

    yield

    # shutting down the schedulers when app is going to stop
    scheduler.shutdown()

    # shutting down the kafka producer
    await kafka_manager.producer.stop()


models.Base.metadata.create_all(bind=engine)

# fast api application initialization
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# initialize all the routers
from app.controller.admin.project_management_controller import router as admin_router
app.include_router(admin_router)

# registering all custom exceptions and handlers
app.add_exception_handler(SpringFixException, spring_fix_exception_handler)

setup_logging()


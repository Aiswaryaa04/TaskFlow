import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://taskflow_user:devpassword123@localhost/taskflow"
)
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=1, decode_responses=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
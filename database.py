from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis

DATABASE_URL = "postgresql://taskflow_user:devpassword123@localhost/taskflow"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

redis_client = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)
# Using db=1 here (separate from AuthVault's db=0) so the two projects' Redis data don't collide

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
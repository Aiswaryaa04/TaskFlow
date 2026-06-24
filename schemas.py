from pydantic import BaseModel
from datetime import datetime

class JobCreate(BaseModel):
    job_type: str
    payload: str

class JobOut(BaseModel):
    id: int
    job_type: str
    payload: str
    status: str
    attempts: int
    result: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
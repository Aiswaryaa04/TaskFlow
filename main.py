from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database import engine, Base, get_db, redis_client, SessionLocal
from models import Job
from schemas import JobCreate, JobOut

import asyncio

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskFlow")

QUEUE_KEY = "taskflow:queue"
DEAD_LETTER_KEY = "taskflow:dead_letter"


@app.post("/jobs", response_model=JobOut)
def submit_job(job: JobCreate, db: Session = Depends(get_db)):
    # Write to Postgres FIRST — this is the durable record.
    # Even if the Redis push below fails, the job's existence is already recorded.
    new_job = Job(job_type=job.job_type, payload=job.payload, status="pending")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Push just the job ID onto the Redis queue — workers will look up details from Postgres.
    redis_client.lpush(QUEUE_KEY, new_job.id)

    return new_job


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    return jobs


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    queue_depth = redis_client.llen(QUEUE_KEY)
    dead_letter_count = redis_client.llen(DEAD_LETTER_KEY)
    total_jobs = db.query(Job).count()
    completed = db.query(Job).filter(Job.status == "completed").count()
    failed = db.query(Job).filter(Job.status == "dead").count()

    return {
        "queue_depth": queue_depth,
        "dead_letter_count": dead_letter_count,
        "total_jobs": total_jobs,
        "completed": completed,
        "failed": failed,
    }

@app.websocket("/ws/stats")
async def stats_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            queue_depth = redis_client.llen(QUEUE_KEY)
            dead_letter_count = redis_client.llen(DEAD_LETTER_KEY)
            total_jobs = db.query(Job).count()
            completed = db.query(Job).filter(Job.status == "completed").count()
            failed = db.query(Job).filter(Job.status == "dead").count()
            db.close()

            await websocket.send_json({
                "queue_depth": queue_depth,
                "dead_letter_count": dead_letter_count,
                "total_jobs": total_jobs,
                "completed": completed,
                "failed": failed,
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
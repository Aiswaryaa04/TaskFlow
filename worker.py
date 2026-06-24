import time
import random
import sys
from redis.exceptions import TimeoutError as RedisTimeoutError

from database import SessionLocal, redis_client
from models import Job

QUEUE_KEY = "taskflow:queue"
DEAD_LETTER_KEY = "taskflow:dead_letter"
MAX_ATTEMPTS = 5


def process_job(job: Job) -> bool:
    """
    Simulates doing real work. Returns True on success, False on failure.
    We randomly fail ~30% of the time to actually exercise the retry logic.
    """
    print(f"[worker] Processing job {job.id} ({job.job_type})...")
    time.sleep(1)  
    success = random.random() > 0.3
    return success


def run_worker(worker_name: str = "worker-1"):
    print(f"[{worker_name}] Started. Waiting for jobs...")
    while True:
        try:
            result = redis_client.brpop(QUEUE_KEY, timeout=5)
        except RedisTimeoutError:
            continue  # no job arrived within the timeout window, just loop again

        if result is None:
            continue

        _, job_id = result
        job_id = int(job_id)

        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            db.close()
            continue

        job.status = "processing"
        db.commit()

        success = process_job(job)

        if success:
            job.status = "completed"
            job.result = "Job completed successfully"
            db.commit()
            print(f"[{worker_name}] Job {job.id} completed.")
        else:
            job.attempts += 1
            if job.attempts >= MAX_ATTEMPTS:
                job.status = "dead"
                job.result = f"Failed after {job.attempts} attempts"
                db.commit()
                redis_client.lpush(DEAD_LETTER_KEY, job.id)
                print(f"[{worker_name}] Job {job.id} moved to dead letter queue.")
            else:
                job.status = "pending"
                db.commit()
                backoff_seconds = 2 ** job.attempts
                print(f"[{worker_name}] Job {job.id} failed (attempt {job.attempts}). Retrying in {backoff_seconds}s...")
                time.sleep(backoff_seconds)
                redis_client.lpush(QUEUE_KEY, job.id)

        db.close()


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "worker-1"
    run_worker(name)
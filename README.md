# TaskFlow

TaskFlow is a distributed job processing system I built to understand how background task queues actually work under the hood — the same pattern that Celery, BullMQ, and AWS SQS exist to solve, just implemented from scratch so I could see every moving part.

The core idea: some work shouldn't happen while a user waits on an HTTP response. TaskFlow lets an API accept a job instantly, hands it off to a queue, and lets independent worker processes pick it up, retry it if it fails, and give up gracefully (rather than forever) if it keeps failing.

## The problem this solves

Imagine an endpoint that sends a welcome email, resizes an uploaded image, or generates a report. If you do that work directly inside the request handler, the caller sits there waiting — and if the email provider is slow or temporarily down, the whole request fails with it. TaskFlow decouples "accepting the work" from "doing the work," so the API responds immediately and the actual processing happens in the background, with automatic retries if something goes wrong.

## How it actually works

**Submitting a job:** `POST /jobs` writes a row to PostgreSQL first — `status: pending` — before anything else happens. This is deliberate: Postgres is the durable record of every job's existence and current state. Only after that write succeeds does the job's ID get pushed onto a Redis list, which acts as the actual queue.

**Picking up work:** Worker processes call Redis's `BRPOP`, a *blocking* pop — instead of constantly polling "is there a job yet?", the worker just waits efficiently until one appears. The moment a job ID shows up, Redis hands it to exactly one waiting worker, even if several workers are listening on the same queue. That's the real mechanism behind distributing work across workers — Redis handles the coordination, not the application code.

**Why two systems instead of one:** Redis is fast but disposable; if it restarted and lost the queue, only the *pointers* would be gone, not the jobs themselves, since Postgres still has every job's record. Postgres isn't built for high-frequency push/pop the way Redis is, so the split plays to each system's strength — Redis for fast dispatch, Postgres for durable state.

**Retry logic:** If a worker fails a job, it doesn't retry immediately. It waits `2^attempts` seconds — 2s, then 4s, then 8s, then 16s — before trying again, so a struggling downstream system isn't hammered repeatedly. After 5 failed attempts, the job is marked `dead` and moved to a separate dead-letter list instead of being retried forever or silently dropped.

**Scaling:** Running a second (or third, or fifth) worker process requires no code changes — they all pull from the same Redis queue, and Redis guarantees no two workers grab the same job. I proved this by running multiple workers simultaneously and watching jobs get split between them in the logs and in the database.

**Live stats:** A WebSocket endpoint (`/ws/stats`) pushes a fresh snapshot of queue depth, total jobs, completions, and dead-lettered jobs once a second. A small React dashboard subscribes to it and updates in real time, plus has a form to submit jobs directly.

**Containerization:** The whole system — API, worker(s), Postgres, and Redis — runs via a single `docker-compose up`. Getting this working took a couple of real fixes worth mentioning: Postgres needs a proper health check (not just "container started") before the API tries to connect, and Python needs `PYTHONUNBUFFERED=1` set inside containers or `print()` output gets buffered and never shows up in `docker logs`.

## Project layout

```
taskflow/
├── main.py                    FastAPI app: submit/list/get jobs, stats, WebSocket
├── worker.py                  Worker process: pulls jobs, retries, dead-letters
├── models.py                  SQLAlchemy Job model
├── schemas.py                 Pydantic request/response schemas
├── database.py                DB engine/session, Redis client
├── load_test.py               Measures API submission throughput
├── load_test_processing.py    Measures end-to-end processing throughput
├── Dockerfile
├── docker-compose.yml
└── frontend/                  React (Vite) live dashboard
```

## Running it locally (without Docker)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

createdb taskflow
psql taskflow -c "GRANT ALL ON SCHEMA public TO your_db_user;"

brew install redis && brew services start redis

uvicorn main:app --reload --port 8001
```

In separate terminals, run one or more workers:
```bash
python3 worker.py worker-1
python3 worker.py worker-2
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Running it with Docker Compose

```bash
docker-compose up --build
```

This starts Postgres, Redis, the API, and two worker replicas together. The API is available at `http://127.0.0.1:8001`.

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/jobs` | Submit a new job |
| GET | `/jobs/{id}` | Get a specific job's status |
| GET | `/jobs` | List recent jobs |
| GET | `/stats` | One-time snapshot of queue/job stats |
| WS | `/ws/stats` | Live stats stream, updated every second |

## Throughput

I ran two separate load tests since "throughput" can mean different things depending on what's being measured:

- **Submission throughput** (how fast the API accepts a job and queues it): roughly **47,000 jobs/minute** with concurrent requests.
- **Processing throughput** (how fast jobs are actually completed end-to-end): roughly **150 jobs/minute** with 5 workers running and a 30% artificial failure rate injected for testing. This number is sensitive to the backoff sleeps on failure, since a worker is unavailable to pick up new jobs while waiting to retry one — a lower failure rate or lighter per-job work would push this number up significantly.
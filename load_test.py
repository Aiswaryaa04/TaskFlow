import requests
import time
import concurrent.futures

API_URL = "http://127.0.0.1:8001/jobs"
NUM_JOBS = 500

def submit_job(i):
    response = requests.post(API_URL, json={
        "job_type": "load_test",
        "payload": f"job-{i}"
    })
    return response.status_code

def main():
    start = time.time()

    # Submit jobs concurrently using a thread pool, simulating many requests at once
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(submit_job, range(NUM_JOBS)))

    elapsed = time.time() - start
    success_count = sum(1 for r in results if r == 200)

    print(f"Submitted {NUM_JOBS} jobs in {elapsed:.2f} seconds")
    print(f"Successful: {success_count}/{NUM_JOBS}")
    print(f"Submission rate: {NUM_JOBS / elapsed:.1f} jobs/second ({(NUM_JOBS / elapsed) * 60:.0f} jobs/minute)")

if __name__ == "__main__":
    main()
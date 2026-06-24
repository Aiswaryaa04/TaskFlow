import requests
import time

API_URL = "http://127.0.0.1:8001"
NUM_JOBS = 1000

def main():
    start = time.time()
    job_ids = []
    for i in range(NUM_JOBS):
        res = requests.post(f"{API_URL}/jobs", json={"job_type": "load_test", "payload": f"job-{i}"})
        job_ids.append(res.json()["id"])
    submit_time = time.time() - start
    print(f"Submitted {NUM_JOBS} jobs in {submit_time:.2f}s")

    # Poll stats until queue is empty
    while True:
        stats = requests.get(f"{API_URL}/stats").json()
        if stats["queue_depth"] == 0:
            break
        time.sleep(0.5)

    total_time = time.time() - start
    rate_per_minute = (NUM_JOBS / total_time) * 60
    print(f"All jobs processed in {total_time:.2f}s total")
    print(f"Processing rate: {rate_per_minute:.0f} jobs/minute")

if __name__ == "__main__":
    main()
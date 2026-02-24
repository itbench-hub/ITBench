import logging
import os
import sys
import time

from kubernetes import client, config

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger(__name__)

def main():
    try:
        rps = int(os.environ.get("RPS"))
        duration = int(os.environ.get("DURATION"))
    except ValueError:
        sys.exit("error: RPS and DURATION environment variable are not set or not ints")

    if rps <= 0 or duration <= 0:
        sys.exit("error: RPS and DURATION environment variable must be positive")

    try:
        config.load_incluster_config()
    except Exception as e:
        logger.exception("configuration loading failed: {0}".format(sys.exception()))
        sys.exit(1)

    print("=== API Request Surge Load Generator ===")
    print("Target: Kubernetes API Server")
    print("Requests per second: {0}".format(rps))
    print("Duration: {0} seconds".format(duration))
    print("==========================================")

    v1 = client.CoreV1Api()

    count = 0
    sleep_interval = 1.0 / rps
    start_time = time.time()
    total_requests = rps * duration

    while count < total_requests:
        elapsed = int(time.time() - start_time)

        if elapsed >= duration:
            break

        try:
            v1.list_pod_for_all_namespaces(watch=False)
        except Exception:
            logger.exception("request failed: {0}".format(sys.exception()))

        count += 1

        if count % (rps * 10) == 0:
            print("[{0}s] Sent {1} requests. {2}s remaining...".format(elapsed, count, duration - elapsed))

        time.sleep(sleep_interval)

    actual_duration = int(time.time() - start_time)

    print("Load generation complete!")
    print("Total requests sent: {0}".format(count))
    print("Actual duration: {0}s".format(actual_duration))

if __name__ == "__main__":
    main()

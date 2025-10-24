import datetime
import json
import logging
import os
import sys
import time

from datetime import datetime, timedelta, timezone

import requests

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger(__name__)

def get_services(session, endpoint, headers):
    response = session.get(
        "{0}/api/v3/services".format(endpoint),
        headers=headers,
        verify=True
    )

    if response.status_code != 200:
        logger.warning("unable to query jaeger for services")
        return []

    content = response.json()
    return content.get("services", [])

def get_operations(session, endpoint, headers, service):
    response = session.get(
        "{0}/api/v3/operations".format(endpoint),
        headers=headers,
        params={
            "service": service,
        },
        verify=True
    )

    if response.status_code != 200:
        logger.warning("unable to query jaeger for operations related to {0}".format(service))
        return []

    content = response.json()
    return content.get("operations", [])

def get_traces(session, endpoint, headers, service, operation, time_window):
    name = operation.get("name")
    if name is None:
        logger.warning("unable to discover name of operation: {0}".format(operation))
        return []

    response = session.get(
        "{0}/api/v3/traces".format(endpoint),
        headers=headers,
        params={
            "query.service_name": service,
            "query.operation_name": name,
            "query.start_time_min": time_window[0],
            "query.start_time_max": time_window[1],
            "query.num_traces": "1"
        },
        verify=True
    )

    if response.status_code != 200:
        logger.warning("unable to query jaeger for traces related to operation ({0})".format(name))
        return []

    content = response.json()
    return content.get("result", {}).get("resourceSpans", [])

def main():
    endpoint = os.environ.get("JAEGER_ENDPOINT")
    if endpoint is None:
        sys.exit("error: JAEGER_ENDPOINT environment variable is not set")

    headers = { "Content-Type": "application/json" }

    retries = Retry(total=3, backoff_factor=0.3)
    adapter = HTTPAdapter(max_retries=retries)

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    while True:
        current_datetime = datetime.now()
        last_datetime = current_datetime - timedelta(seconds=300)
        next_datetime = current_datetime + timedelta(seconds=300)

        traces = []

        time_window = (
            "{0}000Z".format(last_datetime.isoformat(timespec='microseconds')),
            "{0}000Z".format(current_datetime.isoformat(timespec='microseconds'))
        )

        services = get_services(session, endpoint, headers)
        logger.info("retrieved {0} services from jaeger".format(len(services)))

        for service in services:
            operations = get_operations(session, endpoint, headers, service)
            logger.info("retrieved {0} operations from jaeger".format(len(operations)))

            for operation in operations:
                t = get_traces(session, endpoint, headers, service, operation, time_window)
                logger.info("retrieved {0} traces from jaeger".format(len(t)))

                traces.extend(t)

        if len(traces) > 0:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')
            file_path = os.path.join(os.path.expanduser("~"), "records", "traces_at_{0}.json".format(timestamp))

            with open(file_path, "w") as f:
                json.dump(traces, f, indent=4)

        sleep_interval = (next_datetime - datetime.now()).total_seconds()
        if sleep_interval > 0:
            logger.debug("sleep for {0} seconds".format(sleep_interval))
            time.sleep(sleep_interval)

if __name__ == "__main__":
    main()

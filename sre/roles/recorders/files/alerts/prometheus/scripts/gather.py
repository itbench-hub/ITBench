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


def main():
    endpoint = os.environ.get("PROMETHEUS_ENDPOINT")
    if endpoint is None:
        sys.exit("error: PROMETHEUS_ENDPOINT environment variable is not set")

    headers = { "Content-Type": "application/json" }

    token = os.environ.get("PROMETHEUS_TOKEN")
    if token is not None:
        headers["Authorization"] = token

    retries = Retry(total=3, backoff_factor=0.1)
    adapter = HTTPAdapter(max_retries=retries)

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    while True:
        next_datetime = datetime.now() + timedelta(seconds=60)

        response = session.get("{0}/api/v1/alerts".format(endpoint), headers=headers, verify=True)

        if response.status_code != 200:
            logger.warning("unable to query prometheus server")
        else:
            content = response.json()

            alerts = content.get("data", {}).get("alerts", [])
            firing_alerts = list(filter(lambda a: a.get("state", "") == "firing", alerts))

            logger.info("retrieved {0} alerts from prometheus server".format(len(alerts)))
            logger.info("retrieved {0} alerts are in firing state".format(len(firing_alerts)))

            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')
            file_path = os.path.join(os.path.expanduser("~"), "records", "alerts_at_{0}.json".format(timestamp))

            with open(file_path, "w") as f:
                json.dump(firing_alerts, f, indent=4)

        sleep_interval = (next_datetime - datetime.now()).total_seconds()
        if sleep_interval > 0:
            logger.debug("sleep for {0} seconds".format(sleep_interval))
            time.sleep(sleep_interval)

if __name__ == "__main__":
    main()

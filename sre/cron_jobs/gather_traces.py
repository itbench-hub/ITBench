#!/usr/bin/env python3
# Source: https://github.ibm.com/Saurabh-Jha/NTAM/blob/main/gather_traces.py
import argparse
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 120  

def create_session() -> requests.Session:
    """
    Create a requests.Session with a retry strategy.
    """
    session = requests.Session()
    retries = Retry(
        total=3,               # number of total retries
        backoff_factor=0.3,    # factor for time between retries
        status_forcelist=[500, 502, 503, 504] 
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_services(
    session: requests.Session, 
    jaeger_url: str,
    token: str, 
) -> Dict[str, Any]:
    """
    Fetch the list of services from Jaeger.
    """
    url = f"{jaeger_url}/api/services"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()  # e.g., { "total": int, "data": [service1, service2, ...] }
    except Exception as e:
        logger.error(f"Error fetching services: {e}")
        return {}

def get_operations(
    session: requests.Session, 
    jaeger_url: str,
    token: str, 
    service: str
) -> Dict[str, Any]:
    """
    Fetch the list of operations for a given service from Jaeger.
    """
    url = f"{jaeger_url}/api/operations"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"service": service}

    try:
        resp = session.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()  # e.g., { "total": int, "data": [ { "name": ...}, ...] }
    except Exception as e:
        logger.error(f"Error fetching operations for service '{service}': {e}")
        return {}

def get_traces(
    session: requests.Session,
    jaeger_url: str,
    token: str,
    service: str,
    operation: Optional[str],
    start_time: int,
    end_time: int,
    limit: int = 1
) -> Dict[str, Any]:
    """
    Query Jaeger traces for a given service & operation over a time window.
    """
    url = f"{jaeger_url}/api/traces"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "service": service,
        "operation": operation,
        "start": start_time,
        "end": end_time,
        "limit": limit
    }

    try:
        resp = session.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()  # typically { "data": [ ... ] }
    except Exception as e:
        logger.error(f"Error fetching traces for service '{service}', operation '{operation}': {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Collect one trace per service/operation from Jaeger.")
    parser.add_argument(
        "--jaeger_url",
        required=True,
        help="Jaeger base URL (e.g., https://jaeger-domain)"
    )
    parser.add_argument(
        "--jaeger_token",
        required=True,
        help="Jaeger service account token."
    )
    parser.add_argument(
        "--time_window",
        type=int,
        default=300,
        help="Time window in seconds for the last traces. Default is 300 (5 minutes)."
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="traces.json",
        help="File path to store collected traces as JSON. Default is 'traces.json'."
    )
    args = parser.parse_args()

    # Prepare the time range in microseconds
    end_time = int(time.time_ns() // 1000)
    start_time = end_time - (args.time_window * 1_000_000)  # from now - time_window in microseconds

    session = create_session()

    # Retrieve services
    services_data = get_services(session, args.jaeger_url, args.jaeger_token)
    if not services_data or "data" not in services_data:
        logger.info("No services found or unable to fetch services.")
        return

    all_traces = {"data": []}

    # Iterate over services & operations, collect up to one trace each
    for service in services_data["data"]:
        operations_data = get_operations(session, args.jaeger_url, args.jaeger_token, service)
        if not operations_data or "data" not in operations_data:
            logger.info(f"No operations found or unable to fetch operations for service: {service}")
            continue

        for op in operations_data["data"]:
            operation_name = op.get("name", "")
            logger.info(f"Fetching trace for service '{service}' and operation '{operation_name}'")
            trace_json = get_traces(
                session,
                args.jaeger_url,
                args.jaeger_token,
                service,
                operation_name,
                start_time,
                end_time,
                limit=1
            )
            # Merge new data
            if "data" in trace_json:
                all_traces["data"].extend(trace_json["data"])

    # Write to output if we have traces
    if all_traces["data"]:
        with open(args.output_file, "w") as f:
            json.dump(all_traces, f, indent=2)
        logger.info(f"Traces successfully written to {args.output_file}")
    else:
        logger.info("No traces retrieved within the specified time window.")

if __name__ == "__main__":
    main()

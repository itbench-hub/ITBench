"""Check localhost CPU and memory against recommended minimums for a given cluster target."""
import logging
from typing import Any

import psutil

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)

RECOMMENDED_RESOURCES: dict[str, dict[str, int]] = {
    "argo-stack": {"cpu": 12, "memory": 16},
    "environment-cluster": {"cpu": 8, "memory": 16},
}


def get_cpu_count() -> int:
    return psutil.cpu_count(logical=False) or 0


def get_memory_gb() -> int:
    return psutil.virtual_memory().total // (1024 ** 3)


def check_resources(target: str) -> bool:
    """Check if host resources meet recommended minimums. Returns True if met, False otherwise."""
    recommended = RECOMMENDED_RESOURCES[target]
    cpu = get_cpu_count()
    memory_gb = get_memory_gb()

    ok = True
    if cpu < recommended["cpu"]:
        logger.warning(
            "This machine does not have the recommended amount of CPU (%d+). "
            "You may experience degraded or inconsistent performance on this machine.",
            recommended["cpu"],
        )
        ok = False

    if memory_gb < recommended["memory"]:
        logger.warning(
            "This machine does not have the recommended amount of memory (%dGB+). "
            "You may experience degraded or inconsistent performance on this machine.",
            recommended["memory"],
        )
        ok = False

    return ok

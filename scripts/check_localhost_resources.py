"""
Check localhost CPU and memory against recommended minimums for a given cluster target.

Makefile invocation:
  uv run python ../../scripts/check_localhost_resources.py --target <target>
"""
import argparse
import logging

import psutil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

RECOMMENDED_RESOURCES: dict[str, dict[str, int]] = {
    "argo-stack":          {"cpu": 12, "memory": 16},
    "environment-cluster": {"cpu": 8,  "memory": 16},
}


def get_cpu_count() -> int:
    return psutil.cpu_count(logical=False) or 0


def get_memory_gb() -> int:
    return psutil.virtual_memory().total // (1024 ** 3)


def check_resources(target: str) -> None:
    recommended = RECOMMENDED_RESOURCES[target]
    cpu = get_cpu_count()
    memory_gb = get_memory_gb()

    if cpu < recommended["cpu"]:
        logger.warning(
            "This machine does not have the recommended amount of CPU (%d+). "
            "You may experience degraded or inconsistent performance on this machine.",
            recommended["cpu"],
        )

    if memory_gb < recommended["memory"]:
        logger.warning(
            "This machine does not have the recommended amount of memory (%dGB+). "
            "You may experience degraded or inconsistent performance on this machine.",
            recommended["memory"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check localhost resources against recommended minimums.")
    parser.add_argument(
        "--target",
        required=True,
        choices=list(RECOMMENDED_RESOURCES.keys()),
        help="Cluster target to check resources for.",
    )
    args = parser.parse_args()
    check_resources(args.target)


if __name__ == "__main__":
    main()

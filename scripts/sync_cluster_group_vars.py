"""
Write the cluster kubeconfig path into the scenarios group variables.

Makefile invocation:
  uv run python ../../scripts/sync_cluster_group_vars.py
    --kubeconfig <path>
    --cluster-group-variable <path>
"""
import argparse
import logging
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def sync_cluster_group_vars(kubeconfig: Path, cluster_group_variable: Path) -> None:
    content = {"cluster": {"kubeconfig": str(kubeconfig)}}
    cluster_group_variable.parent.mkdir(parents=True, exist_ok=True)
    cluster_group_variable.write_text(
        yaml.dump(content, default_flow_style=False, explicit_start=True),
        encoding="utf-8",
    )
    logger.info("wrote cluster group vars to %s", cluster_group_variable)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write cluster kubeconfig path into scenarios group variables."
    )
    parser.add_argument(
        "--kubeconfig",
        required=True,
        type=Path,
        help="Path to the cluster kubeconfig file.",
    )
    parser.add_argument(
        "--cluster-group-variable",
        required=True,
        type=Path,
        help="Path to the cluster group variable to write.",
    )
    args = parser.parse_args()
    sync_cluster_group_vars(args.kubeconfig, args.cluster_group_variable)


if __name__ == "__main__":
    main()

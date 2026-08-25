"""
Write the Argo stack kubeconfig paths into the scenarios group variables.

Makefile invocation:
  uv run python ../../scripts/sync_stack_group_vars.py
    --orchestrator-kubeconfig <path>
    --runner-kubeconfigs <path> [<path> ...]
    --output <path>
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


def sync_stack_group_vars(
    orchestrator_kubeconfig: Path,
    runner_kubeconfigs: list[Path],
    stack_group_variable: Path,
) -> None:
    content = {
        "stack": {
            "argo": {
                "kubeconfig": str(orchestrator_kubeconfig),
            },
            "runners": {
                "kubeconfigs": [str(p) for p in runner_kubeconfigs],
            },
        }
    }
    stack_group_variable.parent.mkdir(parents=True, exist_ok=True)
    stack_group_variable.write_text(
        yaml.dump(content, default_flow_style=False, explicit_start=True),
        encoding="utf-8",
    )
    logger.info("wrote stack group vars to %s", stack_group_variable)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write Argo stack kubeconfig paths into scenarios group variables."
    )
    parser.add_argument(
        "--orchestrator-kubeconfig",
        required=True,
        type=Path,
        help="Path to the Argo orchestrator kubeconfig file.",
    )
    parser.add_argument(
        "--runner-kubeconfigs",
        required=True,
        nargs="+",
        type=Path,
        help="Paths to the runner kubeconfig files.",
    )
    parser.add_argument(
        "--stack-group-variable",
        required=True,
        type=Path,
        help="Path to the stack group variable to write.",
    )
    args = parser.parse_args()
    sync_stack_group_vars(args.orchestrator_kubeconfig, args.runner_kubeconfigs, args.stack_group_variable)


if __name__ == "__main__":
    main()

import argparse
import logging
import sys
import time

from pathlib import Path
from typing import Any, Dict, List

import ansible_runner
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_scenario_spec(private_project_directory: Path, scenario_id: int) -> Dict[str, Any]:
    file_path = (
        private_project_directory
        / "project"
        / "roles"
        / "scenarios"
        / "files"
        / f"scenario_{scenario_id}"
        / "scenario.yaml"
    )

    logger.info(f"Loading scenario spec from: {file_path}")

    try:
        with open(file_path) as f:
            spec = yaml.safe_load(f)
        logger.debug(f"Loaded scenario spec with {len(spec["spec"]["faults"])} fault groups")
        return spec
    except FileNotFoundError:
        logger.error(f"Scenario spec file not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse scenario spec YAML: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error loading scenario spec: {e}")
        sys.exit(1)

def inject_fault_group(
    private_project_directory: Path,
    scenario_id: int,
    faults_index: int
) -> Any:
    logger.info(f"Starting fault injection for group {faults_index + 1}")

    _, runner = ansible_runner.interface.run_async(
        private_data_dir=str(private_project_directory),
        playbook="manage_faults.yaml",
        ident=f"scenario-{scenario_id}-fault-{faults_index}",
        cmdline=f"--tags inject_faults --extra-vars scenario_id={scenario_id} --extra-vars faults_index={faults_index}"
    )

    return runner

def wait_for_runners(runners: List[Any]) -> None:
    logger.info(f"waiting for {len(runners)} fault injection tasks to complete")

    for idx, runner in enumerate(runners, 1):
        logger.debug(f"waiting for runner {idx}/{len(runners)} to complete")

        while runner.status not in ["canceled", "successful", "timeout", "failed"]:
            time.sleep(1)

        logger.info(f"runner {idx}/{len(runners)} completed with status: {runner.status}")

def main() -> None:
    parser = argparse.ArgumentParser(description="CLI for asynchronous fault injection for live ITBench SRE and FinOps scenarios")

    parser.add_argument("--private_project_directory", type=Path, required=True,)
    parser.add_argument("--scenario_id", type=int, required=True)

    args = parser.parse_args()

    spec = load_scenario_spec(args.private_project_directory, args.scenario_id)

    runners = []
    for faults_index in range(len(spec["spec"]["faults"])):
        runner = inject_fault_group(
            args.private_project_directory,
            args.scenario_id,
            faults_index
        )
        runners.append(runner)

    wait_for_runners(runners)

if __name__ == "__main__":
    main()

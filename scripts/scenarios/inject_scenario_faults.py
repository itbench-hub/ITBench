import argparse
import logging
import sys
import time

from pathlib import Path

import ansible_runner
import yaml

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)

_TERMINAL_STATUSES: frozenset[str] = frozenset({"canceled", "successful", "timeout", "failed"})


def load_scenario_spec(scenario_specs_directory: Path) -> dict:
    file_path = scenario_specs_directory / "scenario.yaml"

    logger.info("loading scenario spec from: %s", file_path)

    try:
        spec = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        logger.debug("loaded scenario spec with %d fault group(s)", len(spec["spec"]["faults"]))
        return spec
    except FileNotFoundError:
        logger.error("scenario spec file not found: %s", file_path)
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error("failed to parse scenario spec YAML: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("unexpected error loading scenario spec: %s", e)
        sys.exit(1)

def inject_fault_group(
    private_project_directory: Path,
    scenario_specs_directory: Path,
    faults_index: int
) -> object:
    logger.info("starting fault injection for group %d", faults_index + 1)

    _, runner = ansible_runner.interface.run_async(
        private_data_dir=str(private_project_directory),
        playbook="manage_faults.yaml",
        ident=f"scenario-{scenario_specs_directory.name}-fault-{faults_index}",
        cmdline=f"--tags inject_faults --extra-vars scenario_specs_directory={scenario_specs_directory} --extra-vars faults_index={faults_index}"
    )

    return runner

def wait_for_runners(runners: list) -> None:
    logger.info("waiting for %d fault injection task(s) to complete", len(runners))

    for idx, runner in enumerate(runners, 1):
        logger.debug("waiting for runner %d/%d to complete", idx, len(runners))

        while runner.status not in _TERMINAL_STATUSES:
            time.sleep(1)

        logger.info("runner %d/%d completed with status: %s", idx, len(runners), runner.status)

def main() -> None:
    parser = argparse.ArgumentParser(description="CLI for asynchronous fault injection for live ITBench SRE and FinOps scenarios")

    parser.add_argument("--private_project_directory", type=Path, required=True,)
    parser.add_argument("--scenario_specs_directory", type=Path, required=True)

    args = parser.parse_args()

    spec = load_scenario_spec(args.scenario_specs_directory)

    runners = [
        inject_fault_group(
            args.private_project_directory,
            args.scenario_specs_directory,
            faults_index,
        )
        for faults_index, _ in enumerate(spec["spec"]["faults"])
    ]

    wait_for_runners(runners)

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.logging import configure_logging
    configure_logging()
    main()

"""Scenario fault injection operations using ansible-runner."""
import logging
import sys
import time
from pathlib import Path
from typing import Any

import ansible_runner
import yaml

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)

_TERMINAL_STATUSES: frozenset[str] = frozenset({"canceled", "successful", "timeout", "failed"})


def load_scenario_spec(scenario_specs_directory: Path) -> dict[str, Any]:
    file_path = scenario_specs_directory / "scenario.yaml"
    logger.info("loading scenario spec from: %s", file_path)

    try:
        spec = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        logger.debug("loaded scenario spec with %d fault group(s)", len(spec.get("spec", {}).get("faults", [])))
        return spec
    except FileNotFoundError:
        logger.error("scenario spec file not found: %s", file_path)
        raise
    except yaml.YAMLError as e:
        logger.error("failed to parse scenario spec YAML: %s", e)
        raise


def inject_fault_group(
    private_project_directory: Path,
    scenario_specs_directory: Path,
    faults_index: int,
) -> Any:
    logger.info("starting fault injection for group %d", faults_index + 1)
    _, runner = ansible_runner.interface.run_async(
        private_data_dir=str(private_project_directory),
        playbook="manage_faults.yaml",
        ident=f"scenario-{scenario_specs_directory.name}-fault-{faults_index}",
        cmdline=f"--tags inject_faults --extra-vars scenario_specs_directory={scenario_specs_directory} --extra-vars faults_index={faults_index}",
    )
    return runner


def wait_for_runners(runners: list[Any]) -> None:
    logger.info("waiting for %d fault injection task(s) to complete", len(runners))
    failed_runners = []
    for idx, runner in enumerate(runners, 1):
        logger.debug("waiting for runner %d/%d to complete", idx, len(runners))
        while runner.status not in _TERMINAL_STATUSES:
            time.sleep(1)
        logger.info("runner %d/%d completed with status: %s", idx, len(runners), runner.status)
        if runner.status != "successful":
            failed_runners.append((idx, runner.status))

    if failed_runners:
        details = ", ".join(f"task {idx} ({status})" for idx, status in failed_runners)
        raise RuntimeError(f"Fault injection failed for: {details}")


def inject_faults(private_project_directory: Path, scenario_specs_directory: Path) -> None:
    """Inject all faults defined in a scenario spec."""
    spec = load_scenario_spec(scenario_specs_directory)
    fault_groups = spec.get("spec", {}).get("faults", [])
    runners = [
        inject_fault_group(
            private_project_directory,
            scenario_specs_directory,
            faults_index,
        )
        for faults_index in range(len(fault_groups))
    ]
    wait_for_runners(runners)

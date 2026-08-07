import argparse
import json
import logging
import time

from pathlib import Path
from typing import Any, Dict, List, Optional

import ansible_runner
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_evaluation_defaults(private_project_directory: Path) -> Dict[str, Any]:
    defaults_path = (
        private_project_directory
        / "project"
        / "roles"
        / "evaluation"
        / "vars"
        / "main"
        / "defaults.yaml"
    )
    with open(defaults_path) as f:
        return yaml.safe_load(f).get("evaluation_defaults", {})


def load_evaluation_overrides(private_project_directory: Path) -> Dict[str, Any]:
    overrides_path = (
        private_project_directory
        / "inventory"
        / "group_vars"
        / "environment"
        / "evaluation.yaml"
    )
    if not overrides_path.exists():
        return {}
    with open(overrides_path) as f:
        return yaml.safe_load(f).get("evaluation_overrides", {})


def resolve_timing(private_project_directory: Path) -> Dict[str, Any]:
    defaults = load_evaluation_defaults(private_project_directory)
    overrides = load_evaluation_overrides(private_project_directory)
    return {**defaults, **overrides}


def run_evaluation_pass(
    private_project_directory: Path,
    scenario_id: int,
    poll_index: int
) -> Any:
    logger.info(f"Running evaluation pass {poll_index}")
    _, runner = ansible_runner.interface.run_async(
        private_data_dir=str(private_project_directory),
        playbook="evaluate_scenario.yaml",
        ident=f"scenario-{scenario_id}-eval-{poll_index}",
        cmdline=f"--extra-vars scenario_id={scenario_id}"
    )
    return runner


def wait_for_runners(runners: List[Any]) -> List[str]:
    statuses = []
    for idx, runner in enumerate(runners, 1):
        while runner.status not in ["canceled", "successful", "timeout", "failed"]:
            time.sleep(1)
        logger.info(f"Check runner {idx}/{len(runners)} completed: {runner.status}")
        statuses.append(runner.status)
    return statuses


def read_check_results(private_project_directory: Path, scenario_id: int) -> Optional[Dict[str, Any]]:
    result_path = private_project_directory / "storage" / f"scenario_{scenario_id}" / "evaluation_result.json"
    if not result_path.exists():
        return None
    with open(result_path) as f:
        return json.load(f)


def write_final_result(
    private_project_directory: Path,
    scenario_id: int,
    passed: bool,
    checks: List[Dict[str, Any]]
) -> None:
    result_path = private_project_directory / "storage" / f"scenario_{scenario_id}" / "evaluation.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pass": passed, "checks": checks}
    with open(result_path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Final evaluation result written to {result_path}: pass={passed}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Continuous evaluation watcher for ITBench scenarios"
    )
    parser.add_argument("--private_project_directory", type=Path, required=True)
    parser.add_argument("--scenario_id", type=int, required=True)
    args = parser.parse_args()

    timing = resolve_timing(args.private_project_directory)

    window = timing.get("window", 300)
    interval = timing.get("interval", 30)
    pass_mark = timing.get("pass_mark", 2)

    consecutive_passes = 0
    deadline = time.time() + window
    poll_index = 0

    logger.info(
        f"Evaluation watcher started: scenario={args.scenario_id} "
        f"window={window}s interval={interval}s pass_mark={pass_mark}"
    )

    last_checks: List[Dict[str, Any]] = []

    while time.time() < deadline:
        runner = run_evaluation_pass(args.private_project_directory, args.scenario_id, poll_index)
        wait_for_runners([runner])
        poll_index += 1

        result = read_check_results(args.private_project_directory, args.scenario_id)
        if result:
            last_checks = result.get("checks", [])
            all_passed = all(c.get("pass", False) for c in last_checks)

            if all_passed:
                consecutive_passes += 1
                logger.info(f"All checks passing — consecutive passes: {consecutive_passes}/{pass_mark}")
                if consecutive_passes >= pass_mark:
                    logger.info("Pass mark reached — declaring success")
                    write_final_result(args.private_project_directory, args.scenario_id, True, last_checks)
                    return
            else:
                consecutive_passes = 0
                failed = [c for c in last_checks if not c.get("pass", False)]
                logger.info(f"Checks not yet passing: {[c.get('message') for c in failed]}")

        remaining = deadline - time.time()
        if remaining <= 0:
            break

        sleep_time = min(interval, remaining)
        logger.info(f"Next poll in {sleep_time:.0f}s ({remaining:.0f}s remaining in window)")
        time.sleep(sleep_time)

    logger.info("Evaluation window expired — declaring failure")
    write_final_result(args.private_project_directory, args.scenario_id, False, last_checks)


if __name__ == "__main__":
    main()

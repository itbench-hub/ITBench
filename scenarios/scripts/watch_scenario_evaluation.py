#!/usr/bin/env python3
"""
Continuous scenario evaluation watcher.

Polls evaluate_scenario.py on a configurable interval until all checks pass
consecutively (pass_mark) or the window expires.
"""

import argparse
import json
import logging
import subprocess
import sys
import time

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_cluster_config(private_project_directory: Path) -> Dict[str, Any]:
    """Load cluster configuration from inventory."""
    cluster_config_path = (
        private_project_directory
        / "inventory"
        / "group_vars"
        / "environment"
        / "cluster.yaml"
    )
    if not cluster_config_path.exists():
        logger.warning(f"Cluster config not found: {cluster_config_path}")
        return {}

    try:
        with open(cluster_config_path) as f:
            data = yaml.safe_load(f)
            return data.get("cluster", {}) if data else {}
    except Exception as e:
        logger.error(f"Failed to load cluster config: {e}")
        return {}


def load_evaluation_defaults() -> Dict[str, Any]:
    """Load evaluation timing defaults."""
    return {
        "window": 300,
        "interval": 30,
        "pass_mark": 2
    }


def load_evaluation_overrides(private_project_directory: Path) -> Dict[str, Any]:
    """Load evaluation timing overrides from inventory."""
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
        data = yaml.safe_load(f)
        return data.get("evaluation_overrides", {}) if data else {}


def resolve_timing(private_project_directory: Path) -> Dict[str, Any]:
    """Merge defaults with overrides."""
    defaults = load_evaluation_defaults()
    overrides = load_evaluation_overrides(private_project_directory)
    return {**defaults, **overrides}


def run_evaluation_pass(
    groundtruth_path: Path,
    kubeconfig: str,
    prometheus_url: str,
    agent_output: Optional[str] = None,
    vm_inventory: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Run evaluation via evaluate_scenario.py subprocess."""
    logger.info("Running evaluation pass via evaluate_scenario.py")

    cmd = [
        "python",
        str(Path(__file__).parent / "evaluate_scenario.py"),
        "--groundtruth", str(groundtruth_path),
        "--kubeconfig", kubeconfig,
        "--prometheus-url", prometheus_url,
    ]

    if agent_output:
        cmd.extend(["--agent-output", agent_output])

    if vm_inventory:
        cmd.extend(["--vm-inventory", vm_inventory])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Evaluation failed: {result.stderr}")
            return None

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
            return output
        except json.JSONDecodeError:
            logger.error(f"Failed to parse evaluation output: {result.stdout}")
            return None

    except subprocess.TimeoutExpired:
        logger.error("Evaluation subprocess timed out")
        return None
    except Exception as e:
        logger.error(f"Evaluation subprocess error: {e}")
        return None


def aggregate_results(
    alerts: List[Dict],
    kubernetes: List[Dict],
    opa: List[Dict]
) -> List[Dict[str, Any]]:
    """Aggregate results from all three evaluators into a single checks list."""
    checks = []

    for alert in alerts:
        checks.append({"type": "alert", **alert})

    for resource in kubernetes:
        checks.append({"type": "kubernetes", **resource})

    for check in opa:
        checks.append({"type": "opa", **check})

    return checks


def write_final_result(
    private_project_directory: Path,
    scenario_id: int,
    passed: bool,
    evaluation_output: Dict[str, Any]
) -> None:
    """Write final evaluation result to storage."""
    result_path = private_project_directory / "storage" / f"scenario_{scenario_id}" / "evaluation.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)

    # Aggregate checks from all evaluators
    checks = aggregate_results(
        evaluation_output.get("alerts", []),
        evaluation_output.get("kubernetes", []),
        evaluation_output.get("opa", [])
    )

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
    parser.add_argument("--agent_output", type=str, default=None)
    parser.add_argument("--vm_inventory", type=str, default=None)
    args = parser.parse_args()

    timing = resolve_timing(args.private_project_directory)

    window = timing.get("window", 300)
    interval = timing.get("interval", 30)
    pass_mark = timing.get("pass_mark", 2)

    # Load kubeconfig from inventory
    cluster_config = load_cluster_config(args.private_project_directory)
    kubeconfig = cluster_config.get("kubeconfig")
    if not kubeconfig:
        logger.error("kubeconfig not found in cluster.yaml")
        sys.exit(1)

    # Prometheus URL: use default, will be set via tools role at runtime
    prometheus_url = "http://prometheus:9090"

    # Resolve groundtruth path
    groundtruth_path = (
        args.private_project_directory
        / "project"
        / "roles"
        / "scenarios"
        / "files"
        / f"scenario_{args.scenario_id}"
        / "groundtruth.yaml"
    )

    if not groundtruth_path.exists():
        logger.error(f"GroundTruth file not found: {groundtruth_path}")
        return

    consecutive_passes = 0
    deadline = time.time() + window
    poll_index = 0

    logger.info(
        f"Evaluation watcher started: scenario={args.scenario_id} "
        f"window={window}s interval={interval}s pass_mark={pass_mark}"
    )

    last_evaluation: Optional[Dict[str, Any]] = None

    while time.time() < deadline:
        poll_index += 1
        logger.info(f"Poll {poll_index}: evaluating scenario {args.scenario_id}")

        evaluation_result = run_evaluation_pass(
            groundtruth_path,
            kubeconfig,
            prometheus_url,
            agent_output=args.agent_output,
            vm_inventory=args.vm_inventory
        )

        if evaluation_result:
            last_evaluation = evaluation_result

            # Extract pass/fail status
            all_checks = (
                evaluation_result.get("alerts", []) +
                evaluation_result.get("kubernetes", []) +
                evaluation_result.get("opa", [])
            )

            if not all_checks:
                # No checks to evaluate
                logger.info("No checks defined for this scenario")
                write_final_result(args.private_project_directory, args.scenario_id, True, evaluation_result)
                return

            all_passed = all(c.get("pass", False) for c in all_checks)

            if all_passed:
                consecutive_passes += 1
                logger.info(f"All checks passing — consecutive passes: {consecutive_passes}/{pass_mark}")
                if consecutive_passes >= pass_mark:
                    logger.info("Pass mark reached — declaring success")
                    write_final_result(args.private_project_directory, args.scenario_id, True, evaluation_result)
                    return
            else:
                consecutive_passes = 0
                failed = [c for c in all_checks if not c.get("pass", False)]
                logger.info(f"Checks not yet passing: {len(failed)}/{len(all_checks)} — {[c.get('message') for c in failed]}")
        else:
            logger.warning(f"Poll {poll_index}: evaluation failed, will retry")
            consecutive_passes = 0

        remaining = deadline - time.time()
        if remaining <= 0:
            break

        sleep_time = min(interval, remaining)
        logger.info(f"Next poll in {sleep_time:.0f}s ({remaining:.0f}s remaining in window)")
        time.sleep(sleep_time)

    logger.info("Evaluation window expired — declaring failure")
    if last_evaluation:
        write_final_result(args.private_project_directory, args.scenario_id, False, last_evaluation)
    else:
        # No successful evaluation, write empty result
        write_final_result(args.private_project_directory, args.scenario_id, False, {"alerts": [], "kubernetes": [], "opa": []})


if __name__ == "__main__":
    main()

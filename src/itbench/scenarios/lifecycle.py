"""Scenario orchestrator: running playbooks and managing scenario lifecycles."""
import logging
from pathlib import Path
from typing import Any

import ansible_runner

from itbench.scenarios.faults import inject_faults

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def run_playbook(
    project_dir: Path,
    playbook: str,
    tags: str | None = None,
    extra_vars: dict[str, Any] | None = None,
) -> Any:
    """Run an Ansible playbook via ansible_runner."""
    cmdline_args = []
    if tags:
        cmdline_args.append(f"--tags {tags}")
    if extra_vars:
        for k, v in extra_vars.items():
            cmdline_args.append(f"--extra-vars {k}={v}")

    cmdline = " ".join(cmdline_args)
    logger.info("Running playbook %s in %s (tags=%s)", playbook, project_dir, tags)
    res = ansible_runner.interface.run(
        private_data_dir=str(project_dir),
        playbook=playbook,
        cmdline=cmdline if cmdline else None,
    )
    if res.status != "successful":
        logger.error("Playbook %s failed with status %s", playbook, res.status)
        raise RuntimeError(f"Playbook {playbook} failed: {res.status}")
    return res


def deploy_tools(project_dir: Path, scenario_specs_directory: Path | None = None) -> None:
    extra_vars = {}
    if scenario_specs_directory:
        extra_vars["scenario_specs_directory"] = str(scenario_specs_directory)
    run_playbook(project_dir, "manage_tools.yaml", tags="install_tools", extra_vars=extra_vars or None)


def undeploy_tools(project_dir: Path, scenario_specs_directory: Path | None = None) -> None:
    extra_vars = {}
    if scenario_specs_directory:
        extra_vars["scenario_specs_directory"] = str(scenario_specs_directory)
    run_playbook(project_dir, "manage_tools.yaml", tags="uninstall_tools", extra_vars=extra_vars or None)


def deploy_applications(project_dir: Path, scenario_specs_directory: Path | None = None) -> None:
    extra_vars = {}
    if scenario_specs_directory:
        extra_vars["scenario_specs_directory"] = str(scenario_specs_directory)
    run_playbook(project_dir, "manage_applications.yaml", tags="install_applications", extra_vars=extra_vars or None)


def undeploy_applications(project_dir: Path, scenario_specs_directory: Path | None = None) -> None:
    extra_vars = {}
    if scenario_specs_directory:
        extra_vars["scenario_specs_directory"] = str(scenario_specs_directory)
    run_playbook(project_dir, "manage_applications.yaml", tags="uninstall_applications", extra_vars=extra_vars or None)


def deploy_recorders(project_dir: Path, scenario_specs_directory: Path | None = None) -> None:
    extra_vars = {}
    if scenario_specs_directory:
        extra_vars["scenario_specs_directory"] = str(scenario_specs_directory)
    run_playbook(project_dir, "manage_recorders.yaml", tags="install_recorders", extra_vars=extra_vars or None)


def undeploy_recorders(project_dir: Path) -> None:
    run_playbook(project_dir, "manage_recorders.yaml", tags="uninstall_recorders")


def remove_fault_resources(project_dir: Path) -> None:
    run_playbook(project_dir, "manage_faults.yaml", tags="remove_faults")


def start_scenario(
    project_dir: Path,
    scenario_specs_directory: Path,
) -> None:
    """Complete start-scenario lifecycle: deploy tools, apps, recorders, and inject faults."""
    logger.info("Starting scenario with specs from %s", scenario_specs_directory)
    deploy_tools(project_dir, scenario_specs_directory)
    deploy_applications(project_dir, scenario_specs_directory)
    deploy_recorders(project_dir, scenario_specs_directory)
    inject_faults(project_dir, scenario_specs_directory)
    logger.info("Scenario started successfully.")


def stop_scenario(
    project_dir: Path,
    scenario_specs_directory: Path | None = None,
) -> None:
    """Complete stop-scenario lifecycle: undeploy recorders, remove faults, undeploy apps & tools."""
    logger.info("Stopping scenario")
    undeploy_recorders(project_dir)
    remove_fault_resources(project_dir)
    undeploy_applications(project_dir, scenario_specs_directory)
    undeploy_tools(project_dir, scenario_specs_directory)
    logger.info("Scenario stopped successfully.")

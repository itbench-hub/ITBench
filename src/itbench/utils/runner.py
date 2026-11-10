"""Ansible runner utilities for ITBench CLI commands."""

import json
import os
import sys
import uuid

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import ansible_runner

from ansible_runner.exceptions import AnsibleRunnerException

from itbench.paths import repository


class PlaybookError(RuntimeError):
    """A playbook exited with a non-zero return code.

    *output* holds the captured Ansible output. It is empty when the output was already streamed
    to the terminal (verbose mode).
    """

    def __init__(self, playbook: str, rc: int, artifact_dir: Path, output: str = "") -> None:
        super().__init__(f"Playbook '{playbook}' failed with return code {rc}. See artifacts in {artifact_dir}")
        self.playbook = playbook
        self.rc = rc
        self.artifact_dir = artifact_dir
        self.output = output


def run_directory(run_id: str) -> Path:
    """Directory that holds the artifacts of the run identified by *run_id*."""
    return Path.cwd() / ".itbench" / "runs" / run_id


def create_run(extra_vars: Mapping[str, Any]) -> tuple[str, Path]:
    """Create a run directory and record *extra_vars* in it as ``extra_vars.json``.

    Returns the new run id and the path of the written file.
    """
    run_id = str(uuid.uuid4())
    artifact_dir = run_directory(run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    extra_vars_file = artifact_dir / "extra_vars.json"
    extra_vars_file.write_text(json.dumps(extra_vars, indent=2), encoding="utf-8")
    return run_id, extra_vars_file


def _captured_output(runner: ansible_runner.Runner) -> str:
    """Read the Ansible output that was written to the run artifacts, or ``""`` when unavailable."""
    try:
        handle = runner.stdout
    except AnsibleRunnerException:
        return ""
    try:
        return handle.read()
    finally:
        handle.close()


def run_playbook(
    playbook: str,
    extra_vars: dict | None = None,
    tags: list[str] | None = None,
    run_id: str | None = None,
    verbose: bool = False,
    kubeconfig: str | None = None,
) -> ansible_runner.Runner:
    """Invoke an Ansible playbook via ansible-runner.

    Args:
        playbook: Playbook filename relative to the SRE project directory
                  (e.g. ``"manage_environment.yaml"``).
        extra_vars: Optional dictionary of extra variables passed to the playbook.
        tags: Optional list of Ansible tags to limit task execution.
        run_id: Optional run identifier; a UUID is generated when omitted.
        verbose: Stream the Ansible output to the terminal. When false the output is
                 captured and only attached to the error if the playbook fails.
        kubeconfig: Optional absolute path to a kubeconfig file.

    Returns:
        The :class:`ansible_runner.Runner` instance after the run completes.

    Raises:
        PlaybookError: If the playbook exits with a non-zero return code.
    """
    run_id = run_id or str(uuid.uuid4())
    artifact_dir = run_directory(run_id)

    cmdline_args: list[str] = []
    if tags:
        cmdline_args += ["--tags", ",".join(tags)]

    envvars = dict(os.environ)
    if kubeconfig:
        envvars["K8S_AUTH_KUBECONFIG"] = str(kubeconfig)

    extravars = {
        "ansible_python_interpreter": sys.executable,
        **(extra_vars or {}),
    }

    runner = ansible_runner.run(
        private_data_dir=str(repository.ansible_project),
        inventory=str(repository.inventory),
        playbook=playbook,
        extravars=extravars,
        cmdline=" ".join(cmdline_args) if cmdline_args else None,
        artifact_dir=str(artifact_dir),
        quiet=not verbose,
        envvars=envvars,
    )

    if runner.rc != 0:
        raise PlaybookError(playbook, runner.rc, artifact_dir, "" if verbose else _captured_output(runner))

    return runner

"""Ansible runner utilities for ITBench CLI commands."""

import uuid
from pathlib import Path

import ansible_runner

_PROJECT_DIR = Path(__file__).parents[3] / "scenarios" / "sre" / "project"


def run_playbook(
    playbook: str,
    extra_vars: dict | None = None,
    tags: list[str] | None = None,
    run_id: str | None = None,
) -> ansible_runner.Runner:
    """Invoke an Ansible playbook via ansible-runner.

    Args:
        playbook: Playbook filename relative to the SRE project directory
                  (e.g. ``"manage_applications.yaml"``).
        extra_vars: Optional dictionary of extra variables passed to the playbook.
        tags: Optional list of Ansible tags to limit task execution.
        run_id: Optional run identifier; a UUID is generated when omitted.

    Returns:
        The :class:`ansible_runner.Runner` instance after the run completes.

    Raises:
        RuntimeError: If the playbook exits with a non-zero return code.
    """
    run_id = run_id or str(uuid.uuid4())
    artifact_dir = Path.cwd() / ".itbench" / "runs" / run_id

    cmdline_args: list[str] = []
    if tags:
        cmdline_args += ["--tags", ",".join(tags)]

    runner = ansible_runner.run(
        private_data_dir=str(_PROJECT_DIR),
        playbook=playbook,
        extravars=extra_vars or {},
        cmdline=" ".join(cmdline_args) if cmdline_args else None,
        artifact_dir=str(artifact_dir),
        quiet=False,
    )

    if runner.rc != 0:
        raise RuntimeError(
            f"Playbook '{playbook}' failed with return code {runner.rc}. "
            f"See artifacts in {artifact_dir}"
        )

    return runner

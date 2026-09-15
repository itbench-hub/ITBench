"""Generate Ansible role files (task stubs) from library indexes."""
import json
import logging

from pathlib import Path
from typing import Any

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def generate_faults_files(faults: list[dict[str, Any]], roles_directory: Path) -> None:
    logger.info("generating faults role files (%d fault(s))", len(faults))
    tasks_dir = roles_directory / "faults" / "tasks"
    for fault in faults:
        task_file = tasks_dir / f"inject_{fault['id'].replace('-', '_')}.yaml"
        if not task_file.exists():
            task_file.write_text(
                f"---\n"
                f"- name: Include fault argument validation tasks\n"
                f"  ansible.builtin.include_tasks:\n"
                f"    file: validate_fault_arguments.yaml\n"
                f"\n"
                f"- name: Print message\n"
                f"  ansible.builtin.debug:\n"
                f"    msg: This fault injection ({fault['id']}) is unimplemented.\n",
                encoding="utf-8",
            )
            logger.info("created unimplemented task stub: %s", task_file.name)


def generate_waiters_files(waiters: list[dict[str, Any]], roles_directory: Path) -> None:
    logger.info("generating waiters role files (%d waiter(s))", len(waiters))
    tasks_dir = roles_directory / "waiters" / "tasks"
    for waiter in waiters:
        task_file = tasks_dir / f"wait_{waiter['id'].replace('-', '_')}.yaml"
        if not task_file.exists():
            task_file.write_text(
                f"---\n"
                f"- name: Include waiter argument validation tasks\n"
                f"  ansible.builtin.include_tasks:\n"
                f"    file: validate_waiter_arguments.yaml\n"
                f"\n"
                f"- name: Print message\n"
                f"  ansible.builtin.debug:\n"
                f"    msg: This waiter ({waiter['id']}) is unimplemented.\n",
                encoding="utf-8",
            )
            logger.info("created unimplemented task stub: %s", task_file.name)


def load_library_index(library_index_directory: Path, library_type: str) -> list[dict[str, Any]]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in (library_index_directory / library_type).glob("*.json")
    ]


def generate_role_files(library_index_directory: Path, playbooks_directory: Path) -> None:
    """Generate faults and waiters role files from library indexes."""
    roles_directory = playbooks_directory / "roles"
    faults = load_library_index(library_index_directory, "faults")
    waiters = load_library_index(library_index_directory, "waiters")

    generate_faults_files(faults, roles_directory)
    generate_waiters_files(waiters, roles_directory)

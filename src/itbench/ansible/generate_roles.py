"""Generate Ansible role files (argument specs, task stubs, vars) from library indexes."""
import json
import logging

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def _make_env(templates_directory: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_directory)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _render_to_file(env: Environment, template_name: str, dest: Path, **context: Any) -> None:
    content = env.get_template(template_name).render(**context)
    dest.write_text(content, encoding="utf-8")
    logger.debug("wrote: %s", dest)


def generate_faults_files(faults: list[dict[str, Any]], roles_directory: Path) -> None:
    logger.info("generating faults role files (%d fault(s))", len(faults))
    role_dir = roles_directory / "faults"
    env = _make_env(role_dir / "templates")

    _render_to_file(env, "meta/argument_specs.yaml.j2", role_dir / "meta" / "argument_specs.yaml", faults=faults)
    _render_to_file(env, "vars/task_files.yaml.j2", role_dir / "vars" / "main" / "task_files.yaml", faults=faults)

    tasks_dir = role_dir / "tasks"
    for fault in faults:
        task_file = tasks_dir / f"inject_{fault['id'].replace('-', '_')}.yaml"
        if not task_file.exists():
            _render_to_file(env, "tasks/inject_unimplemented.j2", task_file, fault=fault)
            logger.info("created unimplemented task stub: %s", task_file.name)


def generate_waiters_files(waiters: list[dict[str, Any]], roles_directory: Path) -> None:
    logger.info("generating waiters role files (%d waiter(s))", len(waiters))
    role_dir = roles_directory / "waiters"
    env = _make_env(role_dir / "templates")

    _render_to_file(env, "meta/argument_specs.yaml.j2", role_dir / "meta" / "argument_specs.yaml", waiters=waiters)
    _render_to_file(env, "vars/task_files.yaml.j2", role_dir / "vars" / "main" / "task_files.yaml", waiters=waiters)

    tasks_dir = role_dir / "tasks"
    for waiter in waiters:
        task_file = tasks_dir / f"wait_{waiter['id'].replace('-', '_')}.yaml"
        if not task_file.exists():
            _render_to_file(env, "tasks/unimplemeneted_wait.j2", task_file, waiter=waiter)
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

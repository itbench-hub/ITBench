"""Generate Ansible role files (argument specs, task stubs, vars) from library indexes.

Makefile invocation:
  scripts/ansible/generate_role_files.py
    --library_index_directory=<path>
    --playbooks_directory=<path>
"""
import argparse
import json
import logging
import sys

from pathlib import Path

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


def _render_to_file(env: Environment, template_name: str, dest: Path, **context) -> None:
    content = env.get_template(template_name).render(**context)
    dest.write_text(content, encoding="utf-8")
    logger.debug("wrote: %s", dest)


def generate_faults_files(faults: list[dict], roles_directory: Path) -> None:
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


def generate_waiters_files(waiters: list[dict], roles_directory: Path) -> None:
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


def load_library_index(library_index_directory: Path, library_type: str) -> list[dict]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in (library_index_directory / library_type).glob("*.json")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Ansible role files from library indexes"
    )
    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--playbooks_directory", type=Path, required=True)
    args = parser.parse_args()

    roles_directory = args.playbooks_directory / "roles"

    faults = load_library_index(args.library_index_directory, "faults")
    waiters = load_library_index(args.library_index_directory, "waiters")

    generate_faults_files(faults, roles_directory)
    generate_waiters_files(waiters, roles_directory)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.logging import configure_logging
    configure_logging()
    sys.exit(main())

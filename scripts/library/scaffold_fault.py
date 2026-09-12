"""Scaffold a new fault index stub from user prompts.

Makefile invocation:
  scripts/library/scaffold_fault.py
    --templates_directory=<path>
"""
import argparse
import logging
import sys

from pathlib import Path

# Ensure `scripts/` is on sys.path for utils imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from utils.yaml import IndentedSafeDumper

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def next_index(faults_templates_directory: Path) -> int:
    existing = [
        int(f.name.split(".", 1)[0])
        for f in faults_templates_directory.glob("*.yaml.j2")
    ]
    return max(existing) + 1 if existing else 1


def create_fault_stub(
    name: str,
    description: str,
    expectation: str,
    index: int,
    faults_templates_directory: Path,
) -> Path:
    fault = {
        "alerts": {},
        "arguments": {"jsonSchema": {}},
        "name": name,
        "description": description,
        "expectation": expectation,
        "platform": "",
        "resources": [],
        "solutions": {"templates": []},
        "tags": [],
    }

    schema_comment = "# yaml-language-server: $schema=../../../../../../schemas/json/library/index/fault.json\n"
    content = schema_comment + yaml.dump(
        fault,
        Dumper=IndentedSafeDumper,
        explicit_start=True,
        indent=2,
        default_flow_style=False,
        allow_unicode=True,
    )

    dest = faults_templates_directory / f"{index}.yaml.j2"
    dest.write_text(content, encoding="utf-8")
    logger.debug("wrote fault stub: %s", dest)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new fault index stub")
    parser.add_argument("--templates_directory", type=Path, required=True)
    args = parser.parse_args()

    faults_dir = args.templates_directory / "faults"

    name = input("Please enter a name for the new fault: ").strip()
    description = input("Please enter a description for the new fault: ").strip()
    expectation = input("Please enter the expectation for when the new fault is injected: ").strip()

    index = next_index(faults_dir)
    dest = create_fault_stub(name, description, expectation, index, faults_dir)

    logger.info("The new fault (%s) has been generated.", name)
    logger.info("Please edit the file to complete the fault:")
    logger.info("  %s", dest.resolve())
    logger.info("")
    logger.info("Once done, run `make generate-library` and `make validate-library`.")
    logger.info("Once verified, run `make generate-resource-files` to create implementation file(s).")


if __name__ == "__main__":
    from utils.logging import configure_logging
    configure_logging()
    sys.exit(main())
